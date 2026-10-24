import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import OwnerDashboardPage from './pages/OwnerDashboardPage.jsx';
import OwnerPOIPage from './pages/OwnerPOIPage.jsx';
import OwnerSubmissionsPage from './pages/OwnerSubmissionsPage.jsx';
import RegistrationStatusPage from './pages/RegistrationStatusPage.jsx';
import OwnerNotificationDetailPage from './pages/OwnerNotificationDetailPage.jsx';

/**
 * OwnerLayout — Khung giao diện Cổng Chủ Quán B2B (`/owner/*`).
 * Phụ trách: Phúc (Nhánh `feature/owner-portal`)
 *
 * Lưu ý Gate (Task 2.3):
 * Nếu `user.is_poi_owner_verified !== true`, tự động điều hướng về `RegistrationStatusPage`.
 */
export default function OwnerLayout() {
  return (
    <div className="min-h-screen bg-amber-50/40">
      <header className="flex items-center justify-between border-b bg-white px-6 py-4 shadow-xs">
        <div className="font-bold text-orange-700">🏪 Cổng Chủ Quán Quận 4 (Owner Portal)</div>
        <nav className="flex gap-4 text-sm font-medium text-slate-600">
          <Link to="/owner">Tổng quan</Link>
          <Link to="/owner/poi">Quản lý Quán & Menu</Link>
          <Link to="/owner/submissions">Lịch sử Gửi duyệt</Link>
          <Link to="/owner/status">Trạng thái Hồ sơ</Link>
        </nav>
      </header>

      <main className="mx-auto max-w-5xl p-6">
        <Routes>
          <Route index element={<OwnerDashboardPage />} />
          <Route path="poi" element={<OwnerPOIPage />} />
          <Route path="submissions" element={<OwnerSubmissionsPage />} />
          <Route path="status" element={<RegistrationStatusPage />} />
          <Route path="notifications/:id" element={<OwnerNotificationDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
