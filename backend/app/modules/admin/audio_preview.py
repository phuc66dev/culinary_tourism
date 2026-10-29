"""Authenticated admin audio preview/download from current POI localizations.

Only trusted Edge-TTS cache files inside app/static/audio are exposed. Avoid
using raw paths from MongoDB as file paths: a corrupt/malicious audio_url must
never allow a local file download outside the audio directory.
"""
from datetime import datetime
from pathlib import Path
import re

from bson import ObjectId
from fastapi import HTTPException

from app.core.database import get_db
from app.core.path_security import resolve_safe_path
from app.modules.audio.service import DEFAULT_NEURAL_VOICES, AUDIO_DIR

LANGUAGE_NAMES = {
    "vi": "Tiếng Việt", "en": "English", "zh": "中文", "ja": "日本語", "ko": "한국어"
}
_MD5_MP3 = re.compile(r"[0-9a-f]{32}\.mp3\Z")
_AUDIO_PREFIX = "/static/audio/"


def _safe_audio_file(localization: dict | None) -> Path | None:
    """Resolve an MP3 only when its record says completed and it exists on disk."""
    if not localization or localization.get("audio_status") != "completed":
        return None
    url = localization.get("audio_url")
    if not isinstance(url, str) or not url.startswith(_AUDIO_PREFIX):
        return None
    filename = url[len(_AUDIO_PREFIX):]
    if not _MD5_MP3.fullmatch(filename):
        return None
    try:
        path = resolve_safe_path(AUDIO_DIR, filename)
        if path.is_file() and path.stat().st_size > 0:
            return path
    except (HTTPException, OSError):
        return None
    return None


async def _poi_id_or_404(poi_id: str) -> tuple[ObjectId, dict]:
    if not ObjectId.is_valid(poi_id):
        raise HTTPException(400, "POI ID không hợp lệ")
    oid = ObjectId(poi_id)
    poi = await get_db()["poi"].find_one({"_id": oid}, {"name": 1})
    if not poi:
        raise HTTPException(404, "Không tìm thấy quán")
    return oid, poi


async def list_poi_audio_files(poi_id: str) -> dict:
    oid, poi = await _poi_id_or_404(poi_id)
    localizations = {
        loc["lang"]: loc
        async for loc in get_db()["poi_localizations"].find(
            {"poi_id": oid, "lang": {"$in": list(DEFAULT_NEURAL_VOICES)}},
            {"lang": 1, "audio_url": 1, "audio_status": 1, "updated_at": 1},
        )
        if loc.get("lang") in DEFAULT_NEURAL_VOICES
    }
    items = []
    for lang, voice in DEFAULT_NEURAL_VOICES.items():
        localization = localizations.get(lang) or {}
        file = _safe_audio_file(localization)
        updated_at = localization.get("updated_at")
        items.append({
            "lang": lang,
            "name": LANGUAGE_NAMES[lang],
            "voice": voice,
            "ready": file is not None,
            "audio_url": f"{_AUDIO_PREFIX}{file.name}" if file else None,
            "size_bytes": file.stat().st_size if file else None,
            "audio_status": localization.get("audio_status") or "missing",
            "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
        })
    return {"poi_id": poi_id, "poi_name": poi.get("name") or "Quán ăn", "items": items}


async def get_poi_audio_file(poi_id: str, lang: str) -> Path:
    if lang not in DEFAULT_NEURAL_VOICES:
        raise HTTPException(422, "Ngôn ngữ không được hỗ trợ")
    oid, _ = await _poi_id_or_404(poi_id)
    doc = await get_db()["poi_localizations"].find_one(
        {"poi_id": oid, "lang": lang}, {"audio_url": 1, "audio_status": 1}
    )
    path = _safe_audio_file(doc)
    if path is None:
        raise HTTPException(404, "Chưa có tệp âm thanh hoàn chỉnh cho ngôn ngữ này")
    return path
