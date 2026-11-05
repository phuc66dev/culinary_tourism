/**
 * Chuyển đường dẫn tĩnh của backend (vd `/static/images/poi/a.webp`) thành URL tuyệt đối.
 * Chỉ cho phép http(s) và data:image — mọi scheme khác (javascript:, file:...) bị coi là đường dẫn tương đối.
 */
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const API_ORIGIN = new URL(apiBase, window.location.origin).origin;

export function assetUrl(path) {
  if (!path || typeof path !== 'string') return null;
  if (/^https?:\/\//i.test(path) || /^data:image\//i.test(path)) return path;
  if (/^[a-z][a-z0-9+.-]*:/i.test(path)) return null; // scheme lạ → từ chối
  return API_ORIGIN + (path.startsWith('/') ? path : `/${path}`);
}

/** Lấy thông điệp lỗi thân thiện từ phản hồi FastAPI (detail có thể là chuỗi hoặc object). */
export function apiErrorMessage(error, fallback = 'Đã có lỗi xảy ra') {
  if (!error?.response) return 'Không kết nối được máy chủ';
  const detail = error.response.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return `${fallback} (${error.response.status})`;
}
