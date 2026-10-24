/**
 * Service Worker (`sw.js`) — Workbox injectManifest + 4 Lớp Phòng Ngự Offline.
 * Phụ trách: Bảo (Task 1.9)
 *
 * Chiến lược chính:
 * 1. POI Data (`/api/v1/poi/load-all`): NetworkFirst (timeout 8s, cache `poi-load-all-cache`, TTL 15 phút)
 * 2. Audio (`/static/audio/*`): CacheFirst phân mảnh theo ngôn ngữ (`audio-cache-lang-{lang}`, max 300 entries/lang)
 * 3. Hình ảnh (`/static/images/*`): CacheFirst kèm kiểm soát hạn mức (Quota-aware LRU eviction)
 * 4. SW Message Protocol:
 *    - `SET_ACTIVE_LANGUAGE`
 *    - `APP_BUILD_SYNC`
 *    - `AUDIO_PACK_ACTIVATE` / `AUDIO_PACK_REMOVE_LANG`
 *    - `MAP_PACK_ACTIVATE` / `MAP_PACK_DEACTIVATE`
 */
import { precacheAndRoute } from 'workbox-precaching';

// Precache các asset build của Vite
precacheAndRoute(self.__WB_MANIFEST || []);

let activeLanguage = 'vi';

self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};
  switch (type) {
    case 'SET_ACTIVE_LANGUAGE':
      activeLanguage = payload?.lang || 'vi';
      break;
    case 'APP_BUILD_SYNC':
    case 'AUDIO_PACK_ACTIVATE':
    case 'AUDIO_PACK_REMOVE_LANG':
    case 'MAP_PACK_ACTIVATE':
    case 'MAP_PACK_DEACTIVATE':
      // TODO (Bảo - Task 1.9): Cài đặt xử lý cache shard và offline pack
      break;
    default:
      break;
  }
});
