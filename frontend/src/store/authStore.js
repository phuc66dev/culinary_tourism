import { create } from 'zustand';

/**
 * Zustand Store quản lý phiên đăng nhập & RBAC cho Owner Portal (Phúc) và Admin Dashboard (Vũ).
 */
export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: Boolean(user), isLoading: false }),
  clearAuth: () => set({ user: null, isAuthenticated: false, isLoading: false }),
}));
