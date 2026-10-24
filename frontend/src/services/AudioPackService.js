/**
 * AudioPackService — Quản lý tải gói âm thanh ngoại tuyến theo ngôn ngữ.
 * Phụ trách: Bảo
 */
class AudioPackService {
  async downloadLanguageAudioPack(lang) {
    /**
     * TODO (Bảo): Tải gói âm thanh cho ngôn ngữ `lang` và gửi `AUDIO_PACK_ACTIVATE` tới SW.
     */
    console.log(`[AudioPackService Skeleton] Downloading audio pack for: ${lang}`);
  }
}

export const audioPackService = new AudioPackService();
