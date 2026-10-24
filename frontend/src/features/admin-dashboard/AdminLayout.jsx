import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage.jsx';
import POIManagementPage from './pages/POIManagementPage.jsx';
import RegistrationsPage from './pages/RegistrationsPage.jsx';
import SubmissionReviewPage from './pages/SubmissionReviewPage.jsx';
import UsersManagementPage from './pages/UsersManagementPage.jsx';
import RoleManagementPage from './pages/RoleManagementPage.jsx';
import AuditLogsPage from './pages/AuditLogsPage.jsx';
import ChangePasswordPage from './pages/ChangePasswordPage.jsx';
import AudioTaskMonitor from './components/AudioTaskMonitor.jsx';

/**
 * AdminLayout — Bảng điều khiển Ban Quản Trị (`/admin/*`).
 * Phụ trách: Vũ (Nhánh `feature/admin-core`)
 */
export default function AdminLayout() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center justify-between border-b bg-slate-900 px-6 py-4 text-white">
        <div className="font-bold">🛠️ Admin Dashboard — Du Lịch Ẩm Thực Quận 4</div>
        <nav className="flex flex-wrap gap-4 text-xs font-medium text-slate-300">
          <Link to="/admin">Dashboard</Link>
          <Link to="/admin/pois">POI Master</Link>
          <Link to="/admin/registrations">Duyệt Chủ Quán</Link>
          <Link to="/admin/submissions">Duyệt Submissions</Link>
          <Link to="/admin/users">Users</Link>
          <Link to="/admin/roles">Roles (RBAC)</Link>
          <Link to="/admin/audit-logs">Audit Logs</Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 p-6">
        <AudioTaskMonitor />
        <Routes>
          <Route index element={<DashboardPage />} />
          <Route path="pois" element={<POIManagementPage />} />
          <Route path="registrations" element={<RegistrationsPage />} />
          <Route path="submissions" element={<SubmissionReviewPage />} />
          <Route path="users" element={<UsersManagementPage />} />
          <Route path="roles" element={<RoleManagementPage />} />
          <Route path="audit-logs" element={<AuditLogsPage />} />
          <Route path="change-password" element={<ChangePasswordPage />} />
        </Routes>
      </main>
    </div>
  );
}
