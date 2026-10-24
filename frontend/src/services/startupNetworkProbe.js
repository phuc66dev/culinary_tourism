/**
 * startupNetworkProbe — Kiểm tra kết nối Backend trước khi chuyển sang chế độ Offline.
 * Phụ trách: Bảo
 *
 * Key Constants:
 * - STARTUP_PROBE_WINDOW_MS = 8000 (8 giây)
 * - STARTUP_PROBE_MAX_FAILS = 2
 */
export const STARTUP_PROBE_WINDOW_MS = 8000;
export const STARTUP_PROBE_MAX_FAILS = 2;

export async function probeBackendConnectivity() {
  // TODO (Bảo): Thử gọi `/api/v1/audio/languages` và `/api/v1/maps/offline-options` (timeout 2.5s)
  return { online: true };
}
