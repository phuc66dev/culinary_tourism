"""
Router cho phân hệ Audio (`/api/v1/audio/*`).
Phụ trách: Vũ (Backend TTS) & Bảo (Tier 2 Cloud TTS Stream)
"""
from fastapi import APIRouter
from app.modules.audio.service import DEFAULT_NEURAL_VOICES

router = APIRouter()


@router.get("/languages")
async def get_supported_languages():
    """Danh sách ngôn ngữ và giọng đọc hỗ trợ (dùng cho cả Startup Network Probe)."""
    return {
        "languages": list(DEFAULT_NEURAL_VOICES.keys()),
        "voices": DEFAULT_NEURAL_VOICES,
    }


@router.post("/tts")
async def stream_cloud_tts(payload: dict):
    """
    TODO (Vũ / Bảo - Tier 2 Audio Fallback):
    - Nhận `text` và `lang`, gọi Edge-TTS tổng hợp và stream MP3 trực tiếp về client.
    """
    return {"status": "todo", "message": "Implement Cloud TTS stream"}
