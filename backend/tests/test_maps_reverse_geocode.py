from io import BytesIO
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config import settings
from app.modules.maps import service


async def test_reverse_geocode_returns_address_and_ward(client, monkeypatch):
    monkeypatch.setattr(settings, "GOONG_API_KEY", "test-key")

    def respond(url, *, timeout):
        params = parse_qs(urlsplit(url).query)
        assert params["latlng"] == ["10.76,106.703"]
        assert params["api_key"] == ["test-key"]
        return BytesIO(json.dumps({"results": [{
            "formatted_address": "1 Vĩnh Khánh, Khánh Hội, Hồ Chí Minh",
            "compound": {"commune": "Khánh Hội"},
        }]}).encode())

    monkeypatch.setattr(service, "urlopen", respond)
    response = await client.get("/api/v1/maps/reverse-geocode", params={"lat": 10.76, "lng": 106.703})
    assert response.status_code == 200, response.text
    assert response.json() == {
        "address": "1 Vĩnh Khánh, Khánh Hội, Hồ Chí Minh",
        "ward": "Khánh Hội",
    }


@pytest.mark.parametrize("properties, expected_address", [
    ({"name": "Quán mẫu", "housenumber": "1", "street": "Vĩnh Khánh"},
     "1 Vĩnh Khánh, Khánh Hội, Thành phố Hồ Chí Minh"),
    ({"name": "Hẻm 243 Hoàng Diệu", "type": "street"},
     "Hẻm 243 Hoàng Diệu, Khánh Hội, Thành phố Hồ Chí Minh"),
])
async def test_reverse_geocode_uses_photon_without_goong_key(client, monkeypatch, properties, expected_address):
    monkeypatch.setattr(settings, "GOONG_API_KEY", "")
    monkeypatch.setattr(settings, "PHOTON_BASE_URL", "https://photon.komoot.io")

    def respond(url, *, timeout):
        target = urlsplit(url)
        params = parse_qs(target.query)
        assert target.hostname == "photon.komoot.io"
        assert target.path == "/reverse"
        assert params["lat"] == ["10.76"]
        assert params["lon"] == ["106.703"]
        assert "api_key" not in params
        return BytesIO(json.dumps({"features": [{"properties": {
            **properties, "district": "Khánh Hội", "city": "Thành phố Hồ Chí Minh",
        }}]}).encode())

    monkeypatch.setattr(service, "urlopen", respond)
    response = await client.get("/api/v1/maps/reverse-geocode", params={"lat": 10.76, "lng": 106.703})
    assert response.status_code == 200, response.text
    assert response.json() == {"address": expected_address, "ward": "Khánh Hội"}


async def test_address_search_returns_first_usable_map_pin(client, monkeypatch):
    def respond(url, *, timeout):
        target = urlsplit(url)
        assert target.path == "/api"
        assert parse_qs(target.query)["q"] == ["Vĩnh Khánh"]
        return BytesIO(json.dumps({"features": [
            {"properties": {"type": "district", "name": "Khánh Hội"}},
            {"properties": {"type": "street", "name": "Đường Vĩnh Khánh", "district": "Khánh Hội"},
             "geometry": {"type": "Point", "coordinates": [106.703, 10.76]}},
        ]}).encode())

    monkeypatch.setattr(service, "urlopen", respond)
    response = await client.get("/api/v1/maps/search-address", params={"q": " Vĩnh Khánh "})
    assert response.status_code == 200, response.text
    assert response.json() == {
        "address": "Đường Vĩnh Khánh, Khánh Hội",
        "ward": "Khánh Hội",
        "coordinates": [106.703, 10.76],
    }
