"""
TTSService — Nhà máy dịch thuật & tổng hợp giọng nói (Edge-TTS + Deep-Translator).
Phụ trách: Vũ (Task 3.7)
"""

# 5 Giọng đọc Neural chuẩn theo PRD
DEFAULT_NEURAL_VOICES: dict[str, str] = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}


class TTSService:
    async def synthesize_speech(self, text: str, lang: str = "vi") -> str:
        """
        TODO (Vũ - Task 3.7):
        1. Tính mã băm `MD5(text + lang)` -> kiểm tra file MP3 đã tồn tại trong `app/static/audio/` chưa.
        2. Nếu đã có -> trả về đường dẫn ngay (Cache HIT, zero cost).
        3. Nếu chưa -> gọi `edge_tts.Communicate(text, voice)` lưu file MP3 và trả về `audio_url`.
        """
        raise NotImplementedError("TODO: Implement TTSService.synthesize_speech")


tts_service = TTSService()
