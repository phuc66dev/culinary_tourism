import React, { useEffect, useState } from 'react';
import { Routes, Route, NavLink, Navigate, useLocation, useNavigate } from 'react-router-dom';
import axiosClient from '../../api/axiosClient.js';
import { useAuthStore } from '../../store/authStore.js';
import { canAccessAdmin, hasPermission, useAdminSession } from './hooks/useAdminSession.js';
import AdminIcon from './components/AdminIcon.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import POIManagementPage from './pages/POIManagementPage.jsx';
import RegistrationsPage from './pages/RegistrationsPage.jsx';
import SubmissionReviewPage from './pages/SubmissionReviewPage.jsx';
import UsersManagementPage from './pages/UsersManagementPage.jsx';
import RoleManagementPage from './pages/RoleManagementPage.jsx';
import AuditLogsPage from './pages/AuditLogsPage.jsx';
import ChangePasswordPage from './pages/ChangePasswordPage.jsx';
import AudioTasksPage from './pages/AudioTasksPage.jsx';
import './admin.css';

const GROUPS = [
  { label: 'Tổng quan', items: [
    { path: '/admin', label: 'Dashboard', icon: 'dashboard', end: true },
  ] },
  { label: 'Nội dung', items: [
    { path: '/admin/pois', label: 'POI Master', permission: 'poi:update', icon: 'pin' },
    { path: '/admin/registrations', label: 'Duyệt chủ quán', permission: 'user:read', icon: 'registrations' },
    { path: '/admin/submissions', label: 'Duyệt đề xuất', permission: 'poi:approve', icon: 'submissions' },
  ] },
  { label: 'Vận hành', items: [
    { path: '/admin/audio-tasks', label: 'Nhà máy Audio', permission: 'poi:update', icon: 'audio' },
  ] },
  { label: 'Hệ thống', items: [
    { path: '/admin/users', label: 'Tài khoản', permission: 'user:read', icon: 'users' },
    { path: '/admin/roles', label: 'Vai trò & quyền', permission: 'role:read', icon: 'shield' },
    { path: '/admin/audit-logs', label: 'Nhật ký thao tác', permission: 'audit:read', icon: 'history' },
    { path: '/admin/change-password', label: 'Đổi mật khẩu', icon: 'lock' },
  ] },
];

const NAV = GROUPS.flatMap((group) => group.items);
const roleLabel = (role) => ({ super_admin: 'Super Admin', admin: 'Admin', poi_owner: 'Chủ quán' }[role] || role || 'Quản trị viên');
const initials = (value) => (value || 'A').trim().split(/\s+/).slice(-2).map((part) => part[0]).join('').toUpperCase();

export default function AdminLayout() {
  const { user, isLoading } = useAdminSession();
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKeyDown = (event) => { if (event.key === 'Escape') setMenuOpen(false); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [menuOpen]);

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try { await axiosClient.post('/admin/auth/logout'); }
    finally { clearAuth(); navigate('/admin/login', { replace: true }); }
  }

  if (isLoading) return <div className="admin-initializing" role="status">Đang xác thực phiên đăng nhập…</div>;
  if (!user) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;

  if (user.must_change_password) {
    return (
      <div className="admin-shell admin-password-guard">
        <div className="admin-password-panel">
          <div className="admin-brand admin-brand--standalone"><span className="admin-brand-mark">Q4</span><span><strong>QUẬN 4</strong><small>Quản trị hệ thống</small></span></div>
          <div className="admin-auth-warning" role="alert">Bạn cần đổi mật khẩu trước khi sử dụng hệ thống.</div>
          <ChangePasswordPage />
          <button className="admin-text-action" onClick={logout} disabled={loggingOut} type="button">Đăng xuất</button>
        </div>
      </div>
    );
  }
  if (!canAccessAdmin(user)) {
    return (
      <div className="admin-shell admin-password-guard">
        <div className="admin-access-denied">
          <AdminIcon name="shield" size={30} />
          <h1>Không có quyền truy cập</h1>
          <p>Tài khoản {user.email} không có quyền truy cập bảng điều khiển quản trị.</p>
          <button type="button" className="admin-button-primary" onClick={logout}>Đăng xuất</button>
        </div>
      </div>
    );
  }

  const current = NAV.find((item) => item.end ? location.pathname === item.path : location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)) || NAV[0];
  const name = user.full_name || user.email || 'Quản trị viên';
  return (
    <div className="admin-shell">
      {menuOpen && <button type="button" className="admin-mobile-backdrop" onClick={() => setMenuOpen(false)} aria-label="Đóng menu" />}
      <aside className={`admin-sidebar ${menuOpen ? 'is-open' : ''}`} aria-label="Điều hướng quản trị">
        <div className="admin-sidebar-head">
          <NavLink to="/admin" className="admin-brand" aria-label="Về Dashboard">
            <span className="admin-brand-mark">Q4</span>
            <span><strong>QUẬN 4</strong><small>Culinary Admin</small></span>
          </NavLink>
          <button className="admin-sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Đóng menu" type="button"><AdminIcon name="close" /></button>
        </div>
        <div className="admin-sidebar-scroll">
          {GROUPS.map((group) => {
            const visible = group.items.filter((item) => !item.permission || hasPermission(user, item.permission));
            if (!visible.length) return null;
            return (
              <div className="admin-nav-group" key={group.label}>
                <div className="admin-nav-heading">{group.label}</div>
                <nav aria-label={group.label}>
                  {visible.map((item) => (
                    <NavLink key={item.path} to={item.path} end={item.end}
                      className={({ isActive }) => `admin-nav-link ${isActive ? 'is-active' : ''}`}>
                      <AdminIcon name={item.icon} size={18} /><span>{item.label}</span>
                    </NavLink>
                  ))}
                </nav>
              </div>
            );
          })}
        </div>
        <div className="admin-sidebar-footer">
          <div className="admin-user-avatar" aria-hidden="true">{initials(name)}</div>
          <div className="admin-user-details"><strong title={name}>{name}</strong><small>{roleLabel(user.role)}</small></div>
          <button className="admin-logout" type="button" onClick={logout} disabled={loggingOut} aria-label="Đăng xuất" title="Đăng xuất"><AdminIcon name="logout" size={18} /></button>
        </div>
      </aside>

      <div className="admin-workspace">
        <header className="admin-topbar">
          <div className="admin-topbar-location">
            <button className="admin-menu-toggle" type="button" onClick={() => setMenuOpen(true)} aria-label="Mở menu" aria-expanded={menuOpen}><AdminIcon name="menu" size={21} /></button>
            <span className="admin-topbar-parent">Quản trị</span><AdminIcon name="chevron" size={14} className="admin-topbar-chevron" />
            <span className="admin-topbar-current">{current.label}</span>
          </div>
          <div className="admin-topbar-right"><span className="admin-online-dot" aria-hidden="true" /><span className="admin-topbar-role">{roleLabel(user.role)}</span><span className="admin-topbar-avatar" aria-label={name}>{initials(name)}</span></div>
        </header>
        <main className="admin-page" id="main-content">
          <Routes>
            <Route index element={<DashboardPage />} />
            <Route path="pois" element={<POIManagementPage />} />
            <Route path="audio-tasks" element={hasPermission(user, 'poi:update') ? <AudioTasksPage /> : <div role="alert">Không có quyền quản lý audio.</div>} />
            <Route path="registrations" element={<RegistrationsPage />} />
            <Route path="submissions" element={<SubmissionReviewPage />} />
            <Route path="users" element={<UsersManagementPage />} />
            <Route path="roles" element={<RoleManagementPage />} />
            <Route path="audit-logs" element={<AuditLogsPage />} />
            <Route path="change-password" element={<ChangePasswordPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
