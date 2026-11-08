import React, { Suspense, lazy } from 'react';
import { Navigate, Routes, Route } from 'react-router-dom';

// [Phúc] Phân hệ Chủ quán (Owner Portal — Lazy Loaded)
const PublicOwnerRegisterPage = lazy(() => import('./features/owner-portal/pages/PublicOwnerRegisterPage.jsx'));
const OwnerLayout = lazy(() => import('./features/owner-portal/OwnerLayout.jsx'));

// [Vũ] Phân hệ Quản trị (Admin Dashboard — Lazy Loaded)
const LoginPage = lazy(() => import('./features/admin-dashboard/pages/LoginPage.jsx'));
const AdminLayout = lazy(() => import('./features/admin-dashboard/AdminLayout.jsx'));

/**
 * App Router cho website Chủ quán và Quản trị:
 * - `/admin/login`     -> Trang đăng nhập chung (GuestRoute)
 * - `/register/owner`  -> Trang đăng ký chủ quán công khai (Phúc)
 * - `/admin/*`         -> Admin Dashboard (Vũ)
 * - `/owner/*`         -> Owner Portal B2B (Phúc)
 */
export default function App() {
  return (
    <Suspense fallback={<div className="p-6 text-center">Đang tải phân hệ...</div>}>
      <Routes>
        <Route path="/admin/login" element={<LoginPage />} />
        <Route path="/register/owner" element={<PublicOwnerRegisterPage />} />
        <Route path="/admin/*" element={<AdminLayout />} />
        <Route path="/owner/*" element={<OwnerLayout />} />
        <Route path="*" element={<Navigate to="/admin/login" replace />} />
      </Routes>
    </Suspense>
  );
}
