import httpx
import pytest

from app.core.config import settings
from app.modules.audio import service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statuses, provider_message, expected_error",
    [
        ([500, 200], "", None),
        ([429], "", service.TranslationRateLimited),
        ([403], "User Rate Limit Exceeded", service.TranslationRateLimited),
        ([403], "Daily Limit Exceeded", RuntimeError),
        ([403], "Invalid API key: test-key", RuntimeError),
    ],
)
async def test_cloud_translation_classifies_provider_failures(monkeypatch, statuses, provider_message, expected_error):
    monkeypatch.setattr(settings, "GOOGLE_TRANSLATION_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(service, "RETRY_BASE_DELAY", 0)
    requests = []

    def respond(request):
        requests.append(request)
        status = statuses[len(requests) - 1]
        payload = {"data": {"translations": [{"translatedText": "Fresh noodles"}]}} if status == 200 else {
            "error": {"message": provider_message},
        }
        return httpx.Response(status, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    if expected_error:
        with pytest.raises(expected_error) as error:
            await service.TTSService().translate("Bún tươi", "en")
        assert type(error.value) is expected_error
        assert "test-key" not in str(error.value)
    else:
        assert await service.TTSService().translate("Bún tươi", "en") == "Fresh noodles"
    assert len(requests) == len(statuses)
    assert requests[0].url.host == "translation.googleapis.com"
    assert requests[0].headers["x-goog-api-key"] == "test-key"
    assert "test-key" not in str(requests[0].url)
