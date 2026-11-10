import asyncio
import hashlib
import logging
from datetime import datetime, timezone
import re
from uuid import uuid4
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakValueDictionary

from app.core import database
from app.core.config import settings
from app.core.ssl_support import ensure_ssl_certificates

logger = logging.getLogger("quan4.tts")

DEFAULT_NEURAL_VOICES = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}

BACKUP_NEURAL_VOICES = {
    "vi": ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"],
    "en": ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural"],
    "zh": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
    "ja": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
    "ko": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"],
}

AUDIO_DIR = Path(__file__).resolve().parents[2] / "static" / "audio"

# Mã ngôn ngữ của Google Translate khác mã nội bộ ở tiếng Trung.
TRANSLATE_CODES = {"zh": "zh-CN"}
MAX_TEXT_LENGTH = 10000
TRANSLATE_CHUNK_SIZE = 4500  # Google Translate giới hạn 5000 ký tự / lần
NETWORK_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # giây; test đặt về 0
TTS_ATTEMPT_TIMEOUT_SECONDS = 120
# Chậm hơn giới hạn được công bố; Redis chia sẻ nhịp giữa nhiều Uvicorn workers.
TRANSLATION_MIN_INTERVAL = 1.5
TRANSLATION_COOLDOWN_SECONDS = 90
_TRANSLATE_PACE_KEY = "translation:google:next_request"
_TRANSLATE_COOLDOWN_KEY = "translation:google:cooldown"


ENABLE_TTS_FALLBACK = False


def clean_text_for_tts(text: str) -> str:
    """Loại bỏ thẻ HTML, markdown, link web, ký tự điều khiển để Edge-TTS không bị lỗi SSML."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"[*_~`#]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


class TranslationRateLimited(RuntimeError):
    """Google Translate temporarily rejected requests (quota / rate limit)."""


class SpeechTemporarilyUnavailable(RuntimeError):
    """The speech provider failed in a way that can recover on a later attempt."""


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
                        raise TranslationRateLimited("Google Translate đang trong thời gian chờ sau khi bị giới hạn.")
                    reserved = await redis.set(_TRANSLATE_PACE_KEY, '1', nx=True,
                                               px=max(1, int(interval * 1000)))
                    if reserved:
                        return
                    ttl = await redis.pttl(_TRANSLATE_PACE_KEY)
                    await asyncio.sleep(max(0.1, ttl / 1000 if ttl > 0 else 0.1))
            except TranslationRateLimited:
                raise
            except (OSError, ConnectionError, TimeoutError):
                logger.warning("Redis translation pacing unavailable; using local throttle")
            except Exception:
                logger.warning("Redis translation pacing failed; using local throttle", exc_info=True)
        async with self._lock:
            loop = asyncio.get_running_loop()
            delay = max(0.0, self._next - loop.time())
            if delay:
                await asyncio.sleep(delay)
            if self._cooldown_until > loop.time():
                raise TranslationRateLimited("Google Translate đang trong thời gian chờ sau khi bị giới hạn.")
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
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
        self._translation_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
        ensure_ssl_certificates()

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
        api_key = settings.GOOGLE_TRANSLATION_API_KEY.strip()
        key = _translation_key(chunk, lang)
        if api_key:
            key = f"cloud-v2:{key}"
        cached = await _cached_translation(key)
        if cached:
            return cached
        lock = self._translation_locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = await _cached_translation(key)
            if cached:
                return cached
            target = TRANSLATE_CODES.get(lang, lang)

            if api_key:
                translated = await self._translate_cloud(chunk, target, api_key)
            else:
                translated = await self._translate_free_with_fallbacks(chunk, target, lang)
            await _save_translation(key, translated)
            return translated

    async def _translate_cloud(self, chunk: str, target: str, api_key: str) -> str:
        import httpx
        url = "https://translation.googleapis.com/language/translate/v2"
        headers = {"x-goog-api-key": api_key}
        payload = {"q": chunk, "source": "vi", "target": target, "format": "text"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(1, NETWORK_RETRIES + 1):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                except httpx.RequestError:
                    message = "Không kết nối được với Google Cloud Translation."
                else:
                    status = response.status_code
                    if status == 200:
                        try:
                            translated = response.json()["data"]["translations"][0]["translatedText"]
                        except (ValueError, KeyError, IndexError, TypeError):
                            translated = None
                        if isinstance(translated, str) and translated.strip():
                            return translated.strip()
                        message = "Google Cloud Translation trả về bản dịch không hợp lệ."
                    elif status == 429 or (
                        status == 403 and "user rate limit exceeded" in response.text.lower()
                    ):
                        raise TranslationRateLimited("Google Cloud Translation đang giới hạn yêu cầu theo phút.")
                    elif status == 403 and "daily limit exceeded" in response.text.lower():
                        raise RuntimeError("Google Cloud Translation đã hết hạn mức dịch trong ngày.")
                    elif status in (401, 403):
                        raise RuntimeError(
                            f"Google Cloud Translation từ chối yêu cầu ({status}). "
                            "Kiểm tra API key, quyền sử dụng API, thanh toán và hạn mức của dự án."
                        )
                    elif status == 400:
                        raise RuntimeError(
                            "Google Cloud Translation báo yêu cầu không hợp lệ (400). "
                            "Kiểm tra API key và nội dung cần dịch."
                        )
                    elif 500 <= status < 600:
                        message = f"Google Cloud Translation tạm thời không khả dụng ({status})."
                    else:
                        raise RuntimeError(f"Google Cloud Translation trả về HTTP {status}.")
                if attempt < NETWORK_RETRIES:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
        raise RuntimeError(message)

    async def _translate_free_with_fallbacks(self, chunk: str, target: str, lang: str) -> str:
        from deep_translator import GoogleTranslator
        from deep_translator.exceptions import TooManyRequests

        last_error: Exception | None = None

        for attempt in range(1, NETWORK_RETRIES + 1):
            try:
                await _translation_pacer.wait()
                translated = await asyncio.to_thread(
                    GoogleTranslator(source="vi", target=target).translate, chunk
                )
                if translated and translated.strip():
                    return translated.strip()
                raise RuntimeError("Empty translation")
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, (TranslationRateLimited, TooManyRequests)) or any(token in str(exc).lower() for token in
                    ("too many requests", "429", "rate limit", "quota exceeded")):
                    if not isinstance(exc, TranslationRateLimited):
                        await _translation_pacer.cooldown()
                    fallback = await self._translate_gemini(chunk, target)
                    if fallback:
                        return fallback
                    raise TranslationRateLimited(
                        "Google Translate đang giới hạn yêu cầu; tác vụ sẽ tự thử lại sau."
                    ) from exc
                last_error = exc
                logger.warning("Dịch %s lỗi (%d/%d): %s", lang, attempt, NETWORK_RETRIES, type(exc).__name__)
                if attempt < NETWORK_RETRIES:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))

        # Kênh dự phòng 1: Gemini AI (nếu có GEMINI_API_KEY)
        gemini_result = await self._translate_gemini(chunk, target)
        if gemini_result:
            return gemini_result

        # Kênh dự phòng 2: MyMemoryTranslator
        mymemory_result = await self._translate_mymemory(chunk, target)
        if mymemory_result:
            return mymemory_result

        raise RuntimeError(f"Dịch sang '{lang}' thất bại: {type(last_error).__name__}") from last_error

    async def _translate_gemini(self, chunk: str, target: str) -> str | None:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return None
        try:
            import httpx
            target_names = {
                "en": "English", "zh": "Simplified Chinese", "zh-CN": "Simplified Chinese",
                "ja": "Japanese", "ko": "Korean",
            }
            lang_name = target_names.get(target, target)
            prompt = (
                f"Translate the following Vietnamese culinary/restaurant text into natural {lang_name}. "
                f"Keep Vietnamese food names recognizable if standard or add brief culinary clarity. "
                f"Output ONLY the translated text, no quotes, no markdown formatting, no explanation:\n\n{chunk}"
            )
            model = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"x-goog-api-key": api_key}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and candidates[0].get("finishReason") == "STOP":
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text and text.strip():
                            logger.info("Dịch thành công qua Gemini AI fallback (%s)", target)
                            return text.strip()
        except Exception as exc:
            logger.warning("Gemini translation fallback error: %s", exc)
        return None

    async def _translate_mymemory(self, chunk: str, target: str) -> str | None:
        try:
            from deep_translator import MyMemoryTranslator
            mm_target = "zh-CN" if target.startswith("zh") else f"{target}-US" if target == "en" else f"{target}-{target.upper()}"
            def do_mm():
                try:
                    return MyMemoryTranslator(source="vi-VN", target=mm_target).translate(chunk)
                except Exception:
                    return MyMemoryTranslator(source="vi", target=target).translate(chunk)
            result = await asyncio.to_thread(do_mm)
            if result and result.strip() and "MYMEMORY WARNING" not in result:
                logger.info("Dịch thành công qua MyMemory fallback (%s)", target)
                return result.strip()
        except Exception as exc:
            logger.warning("MyMemory translation fallback error: %s", exc)
        return None

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

        lock = self._locks.setdefault(digest, asyncio.Lock())
        async with lock:
            if file.is_file() and file.stat().st_size > 0:
                logger.info("TTS cache HIT %s (%s) — zero cost", file.name, lang)
                return SynthResult(url, True)
            await self._generate(text, lang, file)
            logger.info("TTS cache MISS → đã tạo %s (%s)", file.name, lang)
            return SynthResult(url, False)

    async def synthesize_speech(self, text: str, lang: str = "vi") -> str:
        """Tương thích ngược (router /audio/tts): chỉ trả về URL."""
        return (await self.synthesize(text, lang)).url

    async def _generate(self, text: str, lang: str, file: Path) -> None:
        import edge_tts
        from aiohttp import ClientConnectionError, ClientResponseError
        from edge_tts.exceptions import NoAudioReceived

        ensure_ssl_certificates()

        clean_text = clean_text_for_tts(text)
        if not clean_text:
            clean_text = text

        temp = file.with_name(f".{file.stem}.{uuid4().hex}.tmp")
        last_error: Exception | None = None
        voices = BACKUP_NEURAL_VOICES.get(lang, [DEFAULT_NEURAL_VOICES[lang]])

        try:
            for attempt in range(1, NETWORK_RETRIES + 1):
                voice = voices[(attempt - 1) % len(voices)]
                try:
                    temp.unlink(missing_ok=True)
                    await asyncio.wait_for(
                        edge_tts.Communicate(clean_text, voice).save(str(temp)),
                        timeout=TTS_ATTEMPT_TIMEOUT_SECONDS,
                    )
                    if not temp.is_file() or temp.stat().st_size == 0:
                        raise NoAudioReceived("TTS returned empty audio")
                    temp.replace(file)
                    return
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning("Edge-TTS %s (voice %s) lỗi (lần %d/%d): %s", lang, voice, attempt, NETWORK_RETRIES, last_error)
                    if attempt < NETWORK_RETRIES:
                        await asyncio.sleep(RETRY_BASE_DELAY * attempt)

            # Fallback cấp 2: Google Translate TTS nếu Edge-TTS không trả về audio (NoAudioReceived) hoặc lỗi dịch vụ
            if isinstance(last_error, NoAudioReceived) or (ENABLE_TTS_FALLBACK and not isinstance(last_error, ConnectionError)):
                try:
                    logger.info("Thử phương án TTS dự phòng (Google TTS) cho %s...", lang)
                    if await self._generate_gtts_fallback(clean_text, lang, temp):
                        if temp.is_file() and temp.stat().st_size > 0:
                            temp.replace(file)
                            logger.info("Tạo audio thành công bằng TTS dự phòng cho %s", lang)
                            return
                except Exception as exc:
                    logger.warning("Phương án TTS dự phòng thất bại: %s", exc)

            if isinstance(last_error, (NoAudioReceived, ClientConnectionError)) or (
                isinstance(last_error, ClientResponseError)
                and (last_error.status == 429 or last_error.status >= 500)
            ) or isinstance(last_error, TimeoutError):
                raise SpeechTemporarilyUnavailable(
                    f"Dịch vụ tạo MP3 tạm thời không khả dụng cho ngôn ngữ {lang}."
                ) from last_error
            raise RuntimeError(f"Edge-TTS '{lang}' thất bại: {last_error}") from last_error
        finally:
            temp.unlink(missing_ok=True)

    async def _generate_gtts_fallback(self, text: str, lang: str, temp: Path) -> bool:
        """Fallback TTS qua endpoint Google Translate TTS khi Edge-TTS bất khả dụng."""
        import httpx
        try:
            target_lang = "zh-CN" if lang == "zh" else lang
            chunks = split_text(text, limit=180)
            audio_bytes = bytearray()
            url = "https://translate.google.com/translate_tts"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with httpx.AsyncClient(timeout=15.0) as client:
                for c in chunks:
                    if not c.strip():
                        continue
                    params = {"ie": "UTF-8", "q": c, "tl": target_lang, "client": "tw-ob"}
                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code == 200 and resp.content and resp.headers.get("content-type", "").startswith("audio/"):
                        audio_bytes.extend(resp.content)
                    else:
                        return False
            if len(audio_bytes) > 0:
                temp.write_bytes(bytes(audio_bytes))
                return True
        except Exception as exc:
            logger.warning("Google TTS fallback failed: %s", exc)
        return False


tts_service = TTSService()
