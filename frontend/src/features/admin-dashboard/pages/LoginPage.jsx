import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { apiErrorMessage } from '../utils/assetUrl.js';
import { canAccessAdmin } from '../hooks/useAdminSession.js';
import '../admin.css';

/**
 * LoginPage — Đăng nhập bằng httpOnly Cookie JWT (`POST /admin/auth/login`), dùng chung Admin & Chủ quán.
 * Phụ trách: Vũ (Task 3.2)
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setUser } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const destination = (u) => (u.must_change_password ? '/admin/change-password' : canAccessAdmin(u) ? location.state?.from || '/admin' : u.role === 'poi_owner' ? '/owner' : '/');

  if (user) return <Navigate to={destination(user)} replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    setError('');
    setSubmitting(true);
    try {
      const { data } = await axiosClient.post('/admin/auth/login', { email: email.trim(), password });
      setUser(data.user);
      navigate(destination(data.user), { replace: true });
    } catch (err) {
      setError(err.response?.status === 401 ? 'Email hoặc mật khẩu không đúng' : apiErrorMessage(err, 'Đăng nhập thất bại'));
      setSubmitting(false);
    }
  }

  return (
    <div className="admin-login-shell">
      <div className="admin-login-card">
        <div className="admin-login-header">
          <div className="admin-brand admin-brand--standalone">
            <span className="admin-brand-mark">Q4</span>
            <span><strong>QUẬN 4</strong><small>Culinary Admin</small></span>
          </div>
          <h1>Đăng nhập</h1>
          <p>Truy cập hệ thống quản trị ẩm thực Quận 4.</p>
        </div>
        <form onSubmit={handleSubmit} className="admin-login-form">
          {error && <div role="alert" className="admin-login-error">{error}</div>}
          <label htmlFor="login-email">Email
            <input id="login-email" type="email" required autoComplete="username" autoFocus
              placeholder="admin@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label htmlFor="login-password">Mật khẩu
            <input id="login-password" type="password" required maxLength={72}
              autoComplete="current-password" placeholder="Nhập mật khẩu"
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <button type="submit" disabled={submitting}>{submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
        </form>
        <div className="admin-login-footer">Hệ thống nội bộ · Chỉ dành cho tài khoản được cấp quyền</div>
      </div>
    </div>
  );
}
