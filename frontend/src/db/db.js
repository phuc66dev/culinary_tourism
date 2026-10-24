/**
 * IndexedDB Wrapper — `Quan4DB` (v2).
 * Phụ trách: Bảo (Task 1.8)
 *
 * Object Stores:
 * - `pois_by_lang`: Lưu danh sách POI đã hydrate theo từng ngôn ngữ + `dataset_version`
 * - `ui_bundles`: Lưu gói ngôn ngữ giao diện (`Dual-Lane i18n`)
 * - `offline_packs`: Metadata các gói bản đồ/âm thanh ngoại tuyến đã tải
 */
import { openDB } from 'idb';

export const DB_NAME = 'Quan4DB';
export const DB_VERSION = 2;

export async function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('pois_by_lang')) {
        db.createObjectStore('pois_by_lang', { keyPath: 'lang' });
      }
      if (!db.objectStoreNames.contains('ui_bundles')) {
        db.createObjectStore('ui_bundles', { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains('offline_packs')) {
        db.createObjectStore('offline_packs', { keyPath: 'id' });
      }
    },
  });
}

export async function getOfflinePOIs(lang = 'vi') {
  // TODO (Bảo - Task 1.8): Đọc snapshot POI từ IndexedDB để hiển thị tức thì
  const db = await getDB();
  return db.get('pois_by_lang', lang);
}

export async function saveOfflinePOIs(lang, data) {
  // TODO (Bảo - Task 1.8): Lưu/cập nhật POI sau khi full sync hoặc delta sync
  const db = await getDB();
  return db.put('pois_by_lang', { lang, ...data, updatedAt: new Date().toISOString() });
}
