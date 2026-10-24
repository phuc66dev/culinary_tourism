/**
 * LanguageHotsetService — Chuẩn bị trước nội dung & âm thanh trong bán kính 1.5km.
 * Phụ trách: Bảo
 *
 * Key Constants:
 * - HOTSET_NEARBY_RADIUS_M = 1500
 * - HOTSET_REQUIRED_CACHE_COUNT = 3
 */
export const HOTSET_NEARBY_RADIUS_M = 1500;
export const HOTSET_REQUIRED_CACHE_COUNT = 3;

export async function prepareLanguageHotset(lat, lng, lang) {
  // TODO (Bảo): Gọi POST /api/v1/localizations/prepare-hotset và warm cache cho 3 POI gần nhất
  return { ready: true, lang };
}
