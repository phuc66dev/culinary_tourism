/**
 * NarrationEngine — Trình phát thuyết minh tự động đa tầng (4-Tier Hybrid Audio).
 * Phụ trách: Bảo (Task 1.7)
 *
 * Thứ tự Fallback:
 * - Tier 1: Pre-generated MP3 (`audio_url` có sẵn, CacheFirst qua Service Worker)
 * - Tier 1.5: On-demand Translate + TTS (`POST /api/v1/localizations/on-demand` khi `is_fallback = true`)
 * - Tier 2: Cloud TTS Stream (`POST /api/v1/audio/tts` trực tiếp từ Edge-TTS)
 * - Tier 3: Local Browser SpeechSynthesis (`window.speechSynthesis` — hoạt động 100% offline)
 */
class NarrationEngine {
  async playWithFallback(poi, lang = 'vi') {
    /**
     * TODO (Bảo - Task 1.7):
     * Cài đặt chuỗi thử phát âm thanh từ Tier 1 -> Tier 1.5 -> Tier 2 -> Tier 3.
     */
    console.log(`[NarrationEngine Skeleton] Đang chuẩn bị thuyết minh cho: ${poi?.name} (${lang})`);
  }

  stop() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }
}

export const narrationEngine = new NarrationEngine();
