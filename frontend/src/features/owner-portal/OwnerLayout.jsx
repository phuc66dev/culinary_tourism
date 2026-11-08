import React, { useCallback, useEffect, useState } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import LogoutConfirmation from "../LogoutConfirmation.jsx";
import axiosClient from "../../api/axiosClient.js";
import { useAuthStore } from "../../store/authStore.js";
import { useAdminSession } from "../admin-dashboard/hooks/useAdminSession.js";
import toast, { Toaster } from "react-hot-toast";
import {
  FiChevronRight, FiCoffee, FiFileText, FiGrid, FiLogOut,
  FiMapPin, FiMenu, FiShield, FiUser, FiX,
} from "react-icons/fi";
import OwnerInbox from "./components/OwnerInbox.jsx";
import { apiErrorMessage } from "../admin-dashboard/utils/assetUrl.js";
import OwnerDashboardPage from "./pages/OwnerDashboardPage.jsx";
import OwnerPOIPage from "./pages/OwnerPOIPage.jsx";
import OwnerSubmissionsPage from "./pages/OwnerSubmissionsPage.jsx";
import RegistrationStatusPage from "./pages/RegistrationStatusPage.jsx";
import OwnerNotificationDetailPage from "./pages/OwnerNotificationDetailPage.jsx";
import OwnerNotificationsPage from "./pages/OwnerNotificationsPage.jsx";
import "../admin-dashboard/admin.css";
import "./owner.css";

const groups = [
  { label: "Tổng quan", items: [{ to: "/owner", label: "Dashboard", Icon: FiGrid, end: true }] },
  { label: "Quản lý quán", items: [
    { to: "/owner/poi", label: "Thông tin quán", Icon: FiMapPin },
    { to: "/owner/menu", label: "Thực đơn", Icon: FiCoffee },
    { to: "/owner/submissions", label: "Đề xuất cập nhật", Icon: FiFileText },
  ] },
];
const navItems = [
  ...groups.flatMap((group) => group.items),
  { to: "/owner/status", label: "Hồ sơ chủ quán" },
  { to: "/owner/notifications", label: "Thông báo" },
];
const initials = (value) => (value || "Q").trim().split(/\s+/).slice(-2).map((part) => part[0]).join("").toUpperCase();

export default function OwnerLayout() {
  const { user, isLoading } = useAdminSession();
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [shops, setShops] = useState([]);
  const [shopId, setShopId] = useState("");
  const [shopsLoading, setShopsLoading] = useState(true);
  const [shopsError, setShopsError] = useState("");
  const [shopRequest, setShopRequest] = useState(0);
  const [updatingShop, setUpdatingShop] = useState(false);
  const [readVersion, setReadVersion] = useState(0);
  const onNotificationRead = useCallback(() => setReadVersion((value) => value + 1), []);
  const canManageShops = user?.role === "poi_owner" && user.is_poi_owner_verified;
  const shop = shops.find((item) => item.id === shopId) || shops[0];
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKeyDown = (event) => { if (event.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  useEffect(() => {
    if (!canManageShops) return undefined;
    const controller = new AbortController();
    setShopsLoading(true);
    setShopsError("");
    axiosClient.get("/owner/pois/me", { signal: controller.signal })
      .then(({ data }) => setShops(data.items || []))
      .catch((err) => {
        if (!controller.signal.aborted) setShopsError(apiErrorMessage(err, "Không tải được danh sách quán"));
      })
      .finally(() => { if (!controller.signal.aborted) setShopsLoading(false); });
    return () => controller.abort();
  }, [canManageShops, user?.id, shopRequest]);

  function reloadShops() {
    setShopRequest((value) => value + 1);
  }

  async function toggleAvailability() {
    if (!shop || updatingShop || shopsLoading || shopsError) return;
    const isOpen = !shop.is_open;
    setUpdatingShop(true);
    try {
      await axiosClient.put("/owner/pois/" + shop.id, { is_open: isOpen });
      setShops((items) => items.map((item) => item.id === shop.id ? { ...item, is_open: isOpen } : item));
      toast.success(shop.name + (isOpen ? " đang mở cửa." : " đã đóng cửa."));
    } catch (err) {
      toast.error(apiErrorMessage(err, "Không cập nhật được trạng thái quán"));
      if (err.response?.status === 409) reloadShops();
    } finally {
      setUpdatingShop(false);
    }
  }

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try { await axiosClient.post("/admin/auth/logout"); } catch { /* Clear local session even if server session has expired. */ }
    finally { clearAuth(); navigate("/admin/login", { replace: true }); }
  }

  const logoutConfirmation = <LogoutConfirmation open={logoutOpen} busy={loggingOut}
    onClose={() => setLogoutOpen(false)} onConfirm={logout} />;

  if (isLoading) return <div className="admin-initializing" role="status">Đang xác thực phiên đăng nhập…</div>;
  if (!user) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  if (user.role !== "poi_owner") return (
    <div className="admin-shell admin-password-guard">
        {logoutConfirmation}
      <div className="admin-access-denied"><FiShield size={30} aria-hidden="true" /><h1>Cổng dành cho chủ quán</h1><p>Tài khoản hiện tại không có quyền truy cập khu vực này.</p><button type="button" className="admin-button-primary" onClick={() => setLogoutOpen(true)} disabled={loggingOut}>Đăng xuất</button></div>
    </div>
  );

  const isAccountPage = location.pathname === "/owner/status"
    || location.pathname === "/owner/notifications"
    || location.pathname.startsWith("/owner/notifications/");
  if (!user.is_poi_owner_verified && !isAccountPage) {
    return <Navigate to="/owner/status" replace state={{ restrictedFrom: location.pathname }} />;
  }

  const current = navItems.find((item) => item.end ? location.pathname === item.to : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)) || navItems[0];
  const name = user.full_name || user.email || "Chủ quán";
  return (
    <div className="admin-shell owner-admin">
      {logoutConfirmation}
      <Toaster position="top-right" containerStyle={{ top: "calc(var(--owner-header-height) + 12px)", zIndex: 100 }} />
      <a href="#owner-main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2">Bỏ qua điều hướng</a>
      {menuOpen && <button type="button" className="admin-mobile-backdrop" onClick={() => setMenuOpen(false)} aria-label="Đóng menu" />}
      <aside className={`admin-sidebar ${menuOpen ? "is-open" : ""}`} aria-label="Điều hướng chủ quán">
        <div className="admin-sidebar-head">
          <NavLink to="/owner" className="admin-brand" aria-label="Về tổng quan"><span className="admin-brand-mark">Q4</span><span><strong>QUẬN 4</strong><small>Culinary Owner</small></span></NavLink>
          <button className="admin-sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Đóng menu" type="button"><FiX aria-hidden="true" /></button>
        </div>
        <div className="admin-sidebar-scroll">
          {groups.map((group) => <div className="admin-nav-group" key={group.label}><div className="admin-nav-heading">{group.label}</div><nav aria-label={group.label}>{group.items.map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `admin-nav-link ${isActive ? "is-active" : ""}`}><item.Icon size={18} aria-hidden="true" /><span>{item.label}</span></NavLink>)}</nav></div>)}
        </div>
        <div className="admin-sidebar-footer"><div className="admin-user-avatar" aria-hidden="true">{initials(name)}</div><div className="admin-user-details"><strong title={name}>{name}</strong><small>Chủ quán</small></div><button className="admin-logout" type="button" onClick={() => setLogoutOpen(true)} disabled={loggingOut} aria-label="Đăng xuất" title="Đăng xuất"><FiLogOut size={18} aria-hidden="true" /></button></div>
      </aside>
      <div className="admin-workspace">
        <header className="admin-topbar owner-topbar">
          <div className="admin-topbar-location">
            <button className="admin-menu-toggle" type="button" onClick={() => setMenuOpen(true)}
              aria-label="Mở menu" aria-expanded={menuOpen}><FiMenu size={21} aria-hidden="true" /></button>
            <span className="admin-topbar-parent">Chủ quán</span>
            <FiChevronRight size={14} className="admin-topbar-chevron" aria-hidden="true" />
            <span className="admin-topbar-current">{current.label}</span>
          </div>
          <div className="admin-topbar-right">
            {canManageShops && (
              <div className="owner-status-control">
                {shops.length > 1 && (
                  <select value={shop?.id || ""} disabled={updatingShop || shopsLoading}
                    onChange={(event) => setShopId(event.target.value)} aria-label="Chọn quán đang quản lý">
                    {shops.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                )}
                <span>Trạng thái</span>
                <button type="button" className="owner-switch" role="switch" aria-checked={!!shop?.is_open}
                  aria-label={shop ? "Trạng thái hoạt động của " + shop.name : "Trạng thái hoạt động"}
                  title={shopsError || (shop ? (shop.is_open ? "Đang mở cửa" : "Đang đóng cửa") : "Chưa có quán được liên kết")}
                  disabled={!shop || updatingShop || shopsLoading || !!shopsError} aria-busy={updatingShop}
                  onClick={toggleAvailability}>
                  <span aria-hidden="true" />
                </button>
              </div>
            )}
            <OwnerInbox key={user.id} readVersion={readVersion} />
            <Link to="/owner/status" className="owner-header-action owner-profile-link"
              aria-label="Hồ sơ chủ quán" title="Hồ sơ chủ quán">
              <FiUser size={18} aria-hidden="true" />
            </Link>
          </div>
        </header>
        <main className="admin-page" id="owner-main">
          <Routes>
            <Route index element={<OwnerDashboardPage shops={shops} />} />
            <Route path="poi" element={<OwnerPOIPage key={"info-" + shop?.id} selected={shop} loading={shopsLoading} shopError={shopsError} onRetry={reloadShops} />} />
            <Route path="menu" element={<OwnerPOIPage key={"menu-" + shop?.id} mode="menu" selected={shop} loading={shopsLoading} shopError={shopsError} onRetry={reloadShops} />} />
            <Route path="submissions" element={<OwnerSubmissionsPage />} />
            <Route path="status" element={<RegistrationStatusPage />} />
            <Route path="notifications" element={<OwnerNotificationsPage />} />
            <Route path="notifications/:id" element={<OwnerNotificationDetailPage onRead={onNotificationRead} />} />
            <Route path="*" element={(
              <div className="owner-not-found">
                <h1>Không tìm thấy trang</h1>
                <p>Đường dẫn cổng chủ quán không tồn tại.</p>
                <NavLink className="admin-button-primary" to="/owner">Về tổng quan</NavLink>
              </div>
            )} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
