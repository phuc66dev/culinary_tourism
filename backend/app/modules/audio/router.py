"""Public audio fallback routes, with safe diagnostic logging for upstream failures."""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.modules.audio.service import AUDIO_DIR, DEFAULT_NEURAL_VOICES, tts_service
from app.core.path_security import resolve_safe_path

logger = logging.getLogger(__name__)
router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    lang: str = "vi"


@router.get("/languages")
async def languages():
    return {"languages": list(DEFAULT_NEURAL_VOICES), "voices": DEFAULT_NEURAL_VOICES}


@router.post("/tts")
async def tts(payload: TTSRequest):
    try:
        url = await tts_service.synthesize_speech(payload.text, payload.lang)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Never log the submitted narration text; it could contain private data.
        logger.exception("Edge-TTS synthesis failed (language=%s)", payload.lang)
        raise HTTPException(
            status_code=502,
            detail="Edge-TTS service failed. Check the Uvicorn traceback for the upstream error.",
        ) from exc
    return FileResponse(
        resolve_safe_path(AUDIO_DIR, url.rsplit("/", 1)[-1]), media_type="audio/mpeg",
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'"},
    )
