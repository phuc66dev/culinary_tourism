import asyncio
import hashlib
import logging
from datetime import datetime, timezone
import re
from uuid import uuid4
from dataclasses import dataclass
from pathlib import Path

from app.core import database

logger = logging.getLogger("quan4.tts")

DEFAULT_NEURAL_VOICES = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}
AUDIO_DIR = Path(__file__).resolve().parents[2] / "static" / "audio"

# Mã ngôn ngữ của Google Translate khác mã nội bộ ở tiếng Trung.
TRANSLATE_CODES = {"zh": "zh-CN"}
MAX_TEXT_LENGTH = 10000
TRANSLATE_CHUNK_SIZE = 4500  # Google Translate giới hạn 5000 ký tự / lần
NETWORK_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # giây; test đặt về 0
# Chậm hơn giới hạn được công bố; Redis chia sẻ nhịp giữa nhiều Uvicorn workers.
TRANSLATION_MIN_INTERVAL = 1.5
TRANSLATION_COOLDOWN_SECONDS = 90
_TRANSLATE_PACE_KEY = "translation:google:next_request"
_TRANSLATE_COOLDOWN_KEY = "translation:google:cooldown"


class TranslationRateLimited(RuntimeError):
    """Google Translate temporarily rejected requests (quota / rate limit)."""


class TranslationPacer:
    """Throttle requests globally through Redis, or locally when Redis is down.

    The Redis SET NX PX gate spaces START times, not only concurrent requests.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._next = 0.0
        self._cooldown_until = 0.0

    async def wait(self):
        interval = TRANSLATION_MIN_INTERVAL
        if interval <= 0:
            return
        redis = database.redis_client
        if redis is not None:
            try:
                while True:
                    remaining = await redis.pttl(_TRANSLATE_COOLDOWN_KEY)
                    if remaining > 0:
                        await asyncio.sleep(max(0.1, remaining / 1000))
                        continue
                    reserved = await redis.set(_TRANSLATE_PACE_KEY, '1', nx=True,
                                               px=max(1, int(interval * 1000)))
                    if reserved:
                        return
                    ttl = await redis.pttl(_TRANSLATE_PACE_KEY)
                    await asyncio.sleep(max(0.1, ttl / 1000 if ttl > 0 else 0.1))
            except (OSError, ConnectionError, TimeoutError):
                logger.warning("Redis translation pacing unavailable; using local throttle")
            except Exception:
                logger.warning("Redis translation pacing failed; using local throttle", exc_info=True)
        async with self._lock:
            loop = asyncio.get_running_loop()
            delay = max(0.0, self._next - loop.time(), self._cooldown_until - loop.time())
            if delay:
                await asyncio.sleep(delay)
            self._next = loop.time() + interval

    async def cooldown(self):
        self._cooldown_until = asyncio.get_running_loop().time() + TRANSLATION_COOLDOWN_SECONDS
        redis = database.redis_client
        if redis is not None:
            try:
                await redis.set(_TRANSLATE_COOLDOWN_KEY, '1', ex=TRANSLATION_COOLDOWN_SECONDS)
            except Exception:
                logger.warning("Unable to set shared translation cooldown", exc_info=True)


_translation_pacer = TranslationPacer()


def _translation_key(text: str, lang: str) -> str:
    return f"vi:{lang}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


async def _cached_translation(key: str) -> str | None:
    try:
        if database.db is None:
            return None
        doc = await database.get_db()["translation_cache"].find_one({"_id": key})
        return str(doc["value"]) if doc and doc.get("value") else None
    except Exception:
        logger.warning("Translation cache read failed", exc_info=True)
        return None


async def _save_translation(key: str, value: str):
    try:
        if database.db is not None:
            await database.get_db()["translation_cache"].update_one(
                {"_id": key},
                {"$set": {"value": value, "updated_at": datetime.now(timezone.utc)}},
                upsert=True,
            )
    except Exception:
        # Cache failure should never prevent returning a successfully translated text.
        logger.warning("Translation cache write failed", exc_info=True)


@dataclass(frozen=True)
class SynthResult:
    url: str
    cache_hit: bool


def split_text(text: str, limit: int = TRANSLATE_CHUNK_SIZE) -> list[str]:
    """Chia văn bản dài thành các đoạn <= limit ký tự, ưu tiên cắt ở ranh giới câu."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    sentences = re.split(r"(?<=[.!?…。！？])\s+|\n+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > limit:  # câu quá dài: cắt cứng
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:limit])
            sentence = sentence[limit:]
        if current and len(current) + 1 + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def cache_key(text: str, lang: str) -> str:
    """MD5(text + lang) — khóa cache ổn định (không dùng cho mục đích bảo mật)."""
    return hashlib.md5((text + lang).encode("utf-8"), usedforsecurity=False).hexdigest()


class TTSService:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._translation_locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def _check_lang(lang: str) -> None:
        if lang not in DEFAULT_NEURAL_VOICES:
            raise ValueError("Unsupported language")

    # ------------------------------------------------------------------
    # Dịch thuật
    # ------------------------------------------------------------------
    async def translate(self, text: str, lang: str) -> str:
        """Dịch mô tả tiếng Việt sang `lang`. `vi` trả về nguyên văn."""
        self._check_lang(lang)
        text = (text or "").strip()
        if not text:
            raise ValueError("Empty text")
        if lang == "vi":
            return text
        parts = [await self._translate_chunk(chunk, lang) for chunk in split_text(text)]
        return " ".join(parts)

    async def _translate_chunk(self, chunk: str, lang: str) -> str:
        from deep_translator import GoogleTranslator
        from deep_translator.exceptions import TooManyRequests

        key = _translation_key(chunk, lang)
        cached = await _cached_translation(key)
        if cached:
            return cached
        lock = self._translation_locks.setdefault(key, asyncio.Lock())
        try:
            async with lock:
                cached = await _cached_translation(key)
                if cached:
                    return cached
                target = TRANSLATE_CODES.get(lang, lang)
                last_error: Exception | None = None
                for attempt in range(1, NETWORK_RETRIES + 1):
                    try:
                        await _translation_pacer.wait()
                        translated = await asyncio.to_thread(
                            GoogleTranslator(source="vi", target=target).translate, chunk
                        )
                        if translated and translated.strip():
                            value = translated.strip()
                            await _save_translation(key, value)
                            return value
                        raise RuntimeError("Empty translation")
                    except Exception as exc:  # noqa: BLE001 — third-party response
                        # Do not retry 429 immediately: release the global audio worker
                        # and let AudioTaskManager resume from the saved checkpoint.
                        if isinstance(exc, TooManyRequests) or any(token in str(exc).lower() for token in
                            ("too many requests", "429", "rate limit", "quota exceeded")):
                            await _translation_pacer.cooldown()
                            raise TranslationRateLimited(
                                "Google Translate đang giới hạn yêu cầu; tác vụ sẽ tự thử lại sau."
                            ) from exc
                        last_error = exc
                        logger.warning("Dịch %s lỗi (%d/%d): %s", lang, attempt, NETWORK_RETRIES, type(exc).__name__)
                        if attempt < NETWORK_RETRIES:
                            await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                raise RuntimeError(f"Dịch sang '{lang}' thất bại: {type(last_error).__name__}") from last_error
        finally:
            if not lock.locked():
                self._translation_locks.pop(key, None)

    # ------------------------------------------------------------------
    # Tổng hợp giọng nói
    # ------------------------------------------------------------------
    async def synthesize(self, text: str, lang: str = "vi") -> SynthResult:
        """Sinh MP3 (hoặc dùng lại tệp đã có). Trả về URL tĩnh + cờ `cache_hit`."""
        self._check_lang(lang)
        if not text or not text.strip() or len(text) > MAX_TEXT_LENGTH:
            raise ValueError("Invalid language/text")
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        digest = cache_key(text, lang)
        file = AUDIO_DIR / f"{digest}.mp3"
        url = f"/static/audio/{file.name}"

        lock = self._locks.get(digest) or asyncio.Lock()
        self._locks[digest] = lock
        try:
            async with lock:
                if file.is_file() and file.stat().st_size > 0:
                    logger.info("TTS cache HIT %s (%s) — zero cost", file.name, lang)
                    return SynthResult(url, True)
                await self._generate(text, lang, file)
                logger.info("TTS cache MISS → đã tạo %s (%s)", file.name, lang)
                return SynthResult(url, False)
        finally:
            # Giải phóng khóa khi không còn ai chờ → dict không phình theo số văn bản.
            if not lock.locked():
                self._locks.pop(digest, None)

    async def synthesize_speech(self, text: str, lang: str = "vi") -> str:
        """Tương thích ngược (router /audio/tts): chỉ trả về URL."""
        return (await self.synthesize(text, lang)).url

    async def _generate(self, text: str, lang: str, file: Path) -> None:
        import edge_tts

        # Unique temp file: concurrent requests from separate processes must not share one .tmp.
        temp = file.with_name(f".{file.stem}.{uuid4().hex}.tmp")
        last_error: Exception | None = None
        try:
            for attempt in range(1, NETWORK_RETRIES + 1):
                try:
                    await edge_tts.Communicate(text, DEFAULT_NEURAL_VOICES[lang]).save(str(temp))
                    if not temp.is_file() or temp.stat().st_size == 0:
                        raise RuntimeError("TTS returned empty audio")
                    temp.replace(file)  # ghi nguyên tử: không bao giờ để lại MP3 dở dang
                    return
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning("Edge-TTS %s lỗi (lần %d/%d): %s", lang, attempt, NETWORK_RETRIES, exc)
                    if attempt < NETWORK_RETRIES:
                        await asyncio.sleep(RETRY_BASE_DELAY * attempt)
            raise RuntimeError(f"Edge-TTS '{lang}' thất bại: {last_error}") from last_error
        finally:
            temp.unlink(missing_ok=True)


tts_service = TTSService()
