import { useEffect } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';

/**
 * Khôi phục phiên đăng nhập từ httpOnly Cookie khi tải trang (`GET /admin/auth/me`),
 * và tự gọi `/auth/refresh` đúng 1 lần khi access_token (30 phút) hết hạn giữa chừng.
 */
export function useAdminSession() {
  const user = useAuthStore((s) => s.user);
  const isLoading = useAuthStore((s) => s.isLoading);
  const setUser = useAuthStore((s) => s.setUser);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  // Interceptor: 401 → refresh → thử lại request ban đầu (chỉ khi không phải chính các endpoint /auth/).
  useEffect(() => {
    let refreshing = null;
    const id = axiosClient.interceptors.response.use(
      (res) => res,
      async (error) => {
        const original = error.config;
        const is401 = error.response?.status === 401;
        if (!is401 || !original || original._retried || original.url?.includes('/auth/')) throw error;
        original._retried = true;
        try {
          refreshing ??= axiosClient.post('/admin/auth/refresh').finally(() => { refreshing = null; });
          await refreshing;
          return axiosClient(original);
        } catch {
          clearAuth();
          throw error;
        }
      },
    );
    return () => axiosClient.interceptors.response.eject(id);
  }, [clearAuth]);

  useEffect(() => {
    if (user) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await axiosClient.get('/admin/auth/me');
        if (!cancelled) setUser(data);
      } catch (e) {
        if (cancelled) return;
        if (e.response?.status === 401) {
          try {
            const { data } = await axiosClient.post('/admin/auth/refresh');
            if (!cancelled) setUser(data.user);
            return;
          } catch { /* hết hạn hẳn → về trang đăng nhập */ }
        }
        if (!cancelled) clearAuth();
      }
    })();
    return () => { cancelled = true; };
  }, [user, setUser, clearAuth]);

  return { user, isLoading };
}

export const ADMIN_PERMISSIONS = ['poi:update', 'poi:approve', 'user:read', 'role:read', 'audit:read'];

export function hasPermission(user, permission) {
  return Boolean(user?.permissions?.includes(permission));
}

export function canAccessAdmin(user) {
  return ADMIN_PERMISSIONS.some((p) => hasPermission(user, p));
}
