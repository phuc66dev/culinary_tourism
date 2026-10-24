/**
 * GeofenceEngine — Phát hiện vùng bán kính quán ăn & Quyết định phát thuyết minh.
 * Phụ trách: Bảo (Task 1.6)
 *
 * Key Constants:
 * - DEFAULT_RADIUS_M = 30 (30 mét)
 * - DEBOUNCE_MS = 3000 (3 giây liên tục trong vùng)
 * - COOLDOWN_MS = 300000 (5 phút không lặp lại cùng 1 quán)
 * - SAFETY_RECONCILE_MS = 5000 (5 giây)
 */
export const DEFAULT_RADIUS_M = 30;
export const DEBOUNCE_MS = 3000;
export const COOLDOWN_MS = 5 * 60 * 1000;
export const SAFETY_RECONCILE_MS = 5000;

class GeofenceEngine {
  constructor() {
    this.pendingEntries = new Map(); // poiId -> enteredTimestamp
    this.cooldowns = new Map(); // poiId -> lastTriggeredTimestamp
  }

  checkGeofences(userPosition, pois) {
    /**
     * TODO (Bảo - Task 1.6):
     * 1. Dùng `@turf/distance` tính khoảng cách từ `userPosition` tới từng POI.
     * 2. Nếu khoảng cách <= `trigger_radius` (mặc định 30m) và không trong thời gian cooldown 5 phút:
     *    - Đưa vào `pendingEntries`.
     *    - Sau 3s debounce liên tục -> xác nhận sự kiện ENTER.
     * 3. Sắp xếp theo `audio_priority` giảm dần -> khoảng cách tăng dần -> đẩy vào `NarrationEngine`.
     */
  }
}

export const geofenceEngine = new GeofenceEngine();
