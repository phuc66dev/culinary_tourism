/**
 * MapPackService — Quản lý tải & kích hoạt bản đồ Vector ngoại tuyến (`.pmtiles`).
 * Phụ trách: Bảo (Task 1.10)
 */
class MapPackService {
  async installOfflineMapPack(packId) {
    /**
     * TODO (Bảo - Task 1.10):
     * Tải tệp `.pmtiles` Quận 4 vào Cache Storage và gửi message `MAP_PACK_ACTIVATE` cho Service Worker.
     */
    console.log(`[MapPackService Skeleton] Installing map pack: ${packId}`);
  }
}

export const mapPackService = new MapPackService();
