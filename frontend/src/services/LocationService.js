/**
 * LocationService — Thu thập tọa độ GPS thực địa tối ưu pin.
 * Phụ trách: Bảo (Task 1.5)
 *
 * Key Constants:
 * - GPS_THROTTLE_MS = 5000 (5 giây)
 * - LOCATE_REQUEST_BUDGET_MS = 15000 (15 giây)
 * - LOCATE_MAX_CACHED_AGE_MS = 30000 (30 giây)
 */
export const GPS_THROTTLE_MS = 5000;
export const LOCATE_REQUEST_BUDGET_MS = 15000;
export const LOCATE_MAX_CACHED_AGE_MS = 30000;

class LocationService {
  constructor() {
    this.watchId = null;
    this.lastEmitTime = 0;
  }

  requestBestEffortPosition() {
    /**
     * TODO (Bảo - Task 1.5):
     * Ưu tiên dùng cached GPS fix nếu tuổi cache <= 30s và độ chính xác <= 100m.
     */
  }

  startTracking(onPositionUpdate) {
    /**
     * TODO (Bảo - Task 1.5):
     * Gọi `navigator.geolocation.watchPosition` và throttle 5s trước khi gọi `onPositionUpdate`.
     */
  }

  stopTracking() {
    if (this.watchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
  }
}

export const locationService = new LocationService();
