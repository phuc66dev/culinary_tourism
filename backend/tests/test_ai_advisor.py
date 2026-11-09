import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password
from app.modules.ai_advisor import service


async def make_advisor_shop(client, **fields):
    db = get_db()
    owner = await db["users"].insert_one({
        "email": "advisor-owner@example.com",
        "password_hash": hash_password("TestOwner123!"),
        "role": "poi_owner",
        "is_poi_owner_verified": True,
    })
    poi = await db["poi"].insert_one({"name": "Quán mẫu", "owner_id": owner.inserted_id, **fields})
    login = await client.post("/api/v1/admin/auth/login", json={
        "email": "advisor-owner@example.com", "password": "TestOwner123!",
    })
    assert login.status_code == 200, login.text
    return poi.inserted_id


@pytest.mark.parametrize("fallback_status", [200, 429])
async def test_advisor_handles_unavailable_legacy_model(client, monkeypatch, fallback_status):
    poi_id = await make_advisor_shop(client)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    requests = []
    description = " ".join(["món"] * 225)

    def respond(request, *, timeout):
        model = request.full_url.split("/models/")[1].split(":")[0]
        requests.append(model)
        assert request.get_header("X-goog-api-key") == "test-key"
        assert "quán phục vụ bánh mì" in json.loads(request.data)["contents"][0]["parts"][0]["text"]
        status = 404 if model == "gemini-2.5-flash" else fallback_status
        if status != 200:
            raise HTTPError(request.full_url, status, "Gemini error", {}, BytesIO())
        return BytesIO(json.dumps({"candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [{"text": "private reasoning", "thought": True}, {"text": description}]},
        }]}).encode())

    monkeypatch.setattr(service, "urlopen", respond, raising=False)
    response = await client.post("/api/v1/ai/enhance-description", json={
        "poi_id": str(poi_id),
        "poi_name": "Quán mẫu",
        "keywords": [],
        "raw_notes": "quán phục vụ bánh mì",
    })
    assert requests == ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
    if fallback_status == 200:
        assert response.status_code == 200, response.text
        assert response.json()["enhanced_description"] == description
        assert response.json()["usage"]["used_today"] == 1
    else:
        assert response.status_code == 503, response.text
        usage = await client.get("/api/v1/ai/usage")
        assert usage.json()["used_today"] == 0


async def test_advisor_asks_for_context_without_charging_then_uses_shop_facts(client, monkeypatch):
    poi_id = await make_advisor_shop(
        client, category="street_food", ward="Khánh Hội",
        original_description="Một lời giới thiệu cũ.",
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    prompts = []
    description = " ".join(["món"] * 225)

    def respond(request, *, timeout):
        prompts.append(json.loads(request.data)["contents"][0]["parts"][0]["text"])
        return BytesIO(json.dumps({"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": description}]},
        }]}).encode())

    monkeypatch.setattr(service, "urlopen", respond)
    payload = {"poi_id": str(poi_id), "poi_name": "Quán khác", "raw_notes": "Một lời giới thiệu cũ."}
    response = await client.post("/api/v1/ai/enhance-description", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ai_context_required"
    assert prompts == []
    usage = await client.get("/api/v1/ai/usage")
    assert usage.json()["used_today"] == 0

    await get_db()["menu_items"].insert_many([
        {"poi_id": str(poi_id), "name": "Bánh mì chảo", "tags": ["ăn sáng"], "price_vnd": 35123},
        {"poi_id": "unrelated-poi", "name": "Món của quán khác"},
    ])
    response = await client.post("/api/v1/ai/enhance-description", json={
        **payload, "owner_highlight": "Muốn giới thiệu bánh mì chảo",
    })
    assert response.status_code == 200, response.text
    prompt, = prompts
    for fact in ("Quán mẫu", "street_food", "Khánh Hội", "Bánh mì chảo", "ăn sáng",
                 "Muốn giới thiệu bánh mì chảo", "Một lời giới thiệu cũ."):
        assert fact in prompt
    assert "Quán khác" not in prompt
    assert "Món của quán khác" not in prompt
    assert "35123" not in prompt
    assert response.json()["usage"]["used_today"] == 1
