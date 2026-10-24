/**
 * Hook kết nối LocationService + GeofenceEngine + Background Prefetch (Top 3 POI / batch, gate >= 30s).
 * Phụ trách: Bảo
 */
import { useEffect } from 'react';

export function useGeofence(pois, activeLang) {
  useEffect(() => {
    /**
     * TODO (Bảo):
     * 1. Bắt đầu theo dõi vị trí qua `locationService.startTracking`.
     * 2. Đưa tọa độ vào `geofenceEngine.checkGeofences`.
     * 3. Chạy `_prefetchNearbyLocalizations(pos)` cho tối đa 3 POI `is_fallback = true` trong bán kính 500m.
     */
  }, [pois, activeLang]);
}
