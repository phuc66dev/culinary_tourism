import React, { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import { useAuthStore } from "../../../store/authStore.js";
import { apiErrorMessage } from "../utils/assetUrl.js";
import { canAccessAdmin } from "../hooks/useAdminSession.js";
import "../admin.css";

/**
 * LoginPage — Đăng nhập bằng httpOnly Cookie JWT (`POST /admin/auth/login`), dùng chung Admin & Chủ quán.
 * Phụ trách: Vũ (Task 3.2)
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setUser } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function destination(account) {
    const isAdmin = canAccessAdmin(account);
    const isOwner = account.role === "poi_owner";
    if (!isAdmin && !isOwner) return null;
    if (account.must_change_password) return "/admin/change-password";
    const from = location.state?.from;
    if (isAdmin) {
      return typeof from === "string" &&
        from.startsWith("/admin/") &&
        from !== "/admin/login"
        ? from
        : "/admin";
    }
    return "/owner";
  }

  const currentDestination = user && destination(user);
  if (currentDestination) return <Navigate to={currentDestination} replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);
    try {
      const { data } = await axiosClient.post("/admin/auth/login", {
        email: email.trim(),
        password,
      });
      const next = destination(data.user);
      if (!next) {
        setError("Website chỉ dành cho tài khoản chủ quán và quản trị viên.");
        setSubmitting(false);
        return;
      }
      setUser(data.user);
      navigate(next, { replace: true });
    } catch (err) {
      setError(
        err.response?.status === 401
          ? "Email hoặc mật khẩu không đúng"
          : apiErrorMessage(err, "Đăng nhập thất bại"),
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="admin-login-shell">
      <div className="admin-login-card">
        <div className="admin-login-header">
          <div className="admin-brand admin-brand--standalone">
            <span className="admin-brand-mark">Q4</span>
            <span>
              <strong>QUẬN 4</strong>
              <small>Ẩm thực Quận 4</small>
            </span>
          </div>
          <h1>Đăng nhập</h1>
          <p>Dành cho chủ quán và quản trị viên.</p>
        </div>
        <form onSubmit={handleSubmit} className="admin-login-form">
          {error && (
            <div role="alert" className="admin-login-error">
              {error}
            </div>
          )}
          <label htmlFor="login-email">
            Email
            <input
              id="login-email"
              type="email"
              required
              autoComplete="username"
              autoFocus
              placeholder="admin@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label htmlFor="login-password">
            Mật khẩu
            <input
              id="login-password"
              type="password"
              required
              maxLength={72}
              autoComplete="current-password"
              placeholder="Nhập mật khẩu"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
        </form>
        <div className="admin-login-footer">
          <Link className="underline text-sm" to="/register/owner">
            Đăng ký tài khoản chủ quán
          </Link>
        </div>
      </div>
    </div>
  );
}
