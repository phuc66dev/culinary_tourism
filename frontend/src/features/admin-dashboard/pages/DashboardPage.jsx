import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import { useAuthStore } from "../../../store/authStore.js";
import { hasPermission } from "../hooks/useAdminSession.js";
import AdminIcon from "../components/AdminIcon.jsx";
import AdminOperationsPanel from "../components/AdminOperationsPanel.jsx";
import { apiErrorMessage } from "../utils/assetUrl.js";

const METRICS = [
  {
    key: "pois", label: "Quán ăn", subtitle: "Địa điểm trong hệ thống",
    permission: "poi:update", href: "/admin/pois", icon: "pin",
    request: () => axiosClient.get("/admin/pois", { params: { limit: 1 } }),
    count: (data) => data.total,
  },
  {
    key: "registrations", label: "Hồ sơ chờ duyệt", subtitle: "Đăng ký chủ quán",
    permission: "user:read", href: "/admin/registrations", icon: "registrations",
    request: () => axiosClient.get("/admin/registrations", { params: { status: "pending", limit: 1 } }),
    count: (data) => data.total,
  },
  {
    key: "submissions", label: "Đề xuất chờ duyệt", subtitle: "Thay đổi thông tin POI",
    permission: "poi:approve", href: "/admin/submissions", icon: "submissions",
    request: () => axiosClient.get("/admin/submissions", { params: { status: "pending", limit: 1 } }),
    count: (data) => data.total,
  },
  {
    key: "audio", label: "Audio đang xử lý", subtitle: "Đang chạy, chờ hoặc tạm dừng",
    permission: "poi:update", href: "/admin/audio-tasks", icon: "audio",
    request: () => axiosClient.get("/admin/audio-tasks"),
    count: (data) => (data.items || []).filter((task) => ["queued", "running", "paused"].includes(task.status)).length,
  },
];

const QUICK_ACTIONS = [
  { label: "Quản lý POI", description: "Xem danh sách và trạng thái công khai", href: "/admin/pois", icon: "pin", permission: "poi:update" },
  { label: "Duyệt hồ sơ chủ quán", description: "Xử lý hồ sơ cần xác minh", href: "/admin/registrations", icon: "registrations", permission: "user:read" },
  { label: "Duyệt đề xuất", description: "Đối chiếu thay đổi trước khi công khai", href: "/admin/submissions", icon: "submissions", permission: "poi:approve" },
  { label: "Giám sát Audio", description: "Theo dõi và nghe thử âm thanh", href: "/admin/audio-tasks", icon: "audio", permission: "poi:update" },
];

const countFormat = new Intl.NumberFormat("vi-VN");

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const canViewAnalytics = hasPermission(user, "analytics:view");
  const [stats, setStats] = useState({});
  const [analytics, setAnalytics] = useState(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);
  const [retry, setRetry] = useState(0);
  const visible = METRICS.filter((item) => hasPermission(user, item.permission));

  const refresh = useCallback(() => setRetry((n) => n + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");

    if (canViewAnalytics) {
      axiosClient.get("/admin/dashboard/stats", { params: { days }, signal: controller.signal })
        .then(({ data }) => {
          if (controller.signal.aborted) return;
          setAnalytics(data);
          setStats({
            pois: data.summary.pois.total,
            registrations: data.summary.registrations.pending,
            submissions: data.summary.submissions.pending,
            audio: data.summary.audio.processing,
          });
          setUpdatedAt(new Date(data.generated_at));
        })
        .catch((err) => {
          if (!controller.signal.aborted) {
            setError(apiErrorMessage(err, "Không tải được dữ liệu thống kê."));
            setAnalytics(null);
            setStats({});
            setUpdatedAt(null);
          }
        })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    } else {
      const currentMetrics = METRICS.filter((item) => hasPermission(user, item.permission));
      Promise.allSettled(currentMetrics.map((item) => item.request())).then((results) => {
        if (controller.signal.aborted) return;
        const next = {};
        results.forEach((result, index) => {
          const item = currentMetrics[index];
          next[item.key] = result.status === "fulfilled" ? item.count(result.value.data) : null;
        });
        setStats(next);
        if (results.some((result) => result.status === "rejected")) {
          setError("Không thể tải đầy đủ số liệu. Hãy thử làm mới.");
        } else {
          setUpdatedAt(new Date());
        }
        setLoading(false);
      });
    }
    return () => controller.abort();
  }, [canViewAnalytics, user, days, retry]);

  return (
    <div className="admin-dashboard">
      <div className="admin-dashboard-heading">
        <div>
          <div className="admin-eyebrow">TỔNG QUAN</div>
          <h1>Dashboard</h1>
          <p>Theo dõi dữ liệu thực tế và các công việc quản trị.</p>
        </div>
        <button type="button" className="admin-refresh-button" onClick={refresh} disabled={loading}>
          <AdminIcon name="refresh" size={16} />
          {loading ? "Đang cập nhật" : "Làm mới"}
        </button>
      </div>
      {error && (
        <div className="admin-dashboard-error" role="alert">
          <AdminIcon name="alert" size={17} />
          <span>{error}</span>
          <button type="button" onClick={refresh}>Thử lại</button>
        </div>
      )}
      {!canViewAnalytics && <div className="admin-metrics-grid">
        {visible.map((item) => (
          <Link key={item.key} to={item.href} className="admin-metric-card">
            <div className="admin-metric-head">
              <span>{item.label}</span>
              <AdminIcon name={item.icon} size={19} />
            </div>
            <div className="admin-metric-value">
              {loading && !(item.key in stats) ? "···" : stats[item.key] == null ? "—" : countFormat.format(stats[item.key])}
            </div>
            <div className="admin-metric-foot">
              <span>{item.subtitle}</span>
              <AdminIcon name="arrow" size={16} />
            </div>
          </Link>
        ))}
        {!visible.length && !canViewAnalytics && <p className="admin-empty-state">Tài khoản hiện chưa có quyền xem số liệu quản trị.</p>}
      </div>}
      {canViewAnalytics && (loading && (!analytics || analytics.days !== days) ? (
        <div className="admin-analytics-loading" role="status">Đang tải biểu đồ và thống kê…</div>
      ) : analytics ? (
        <AdminOperationsPanel data={analytics} days={days} onDaysChange={setDays} user={user} />
      ) : null)}
      <div className="admin-dashboard-section">
        <div className="admin-section-header">
          <h2>Truy cập nhanh</h2>
          <p>Các công việc thường dùng</p>
        </div>
        <div className="admin-quick-grid">
          {QUICK_ACTIONS.filter((item) => hasPermission(user, item.permission)).map((item) => (
            <Link to={item.href} key={item.href} className="admin-quick-link">
              <span className="admin-quick-icon"><AdminIcon name={item.icon} size={19} /></span>
              <span><strong>{item.label}</strong><small>{item.description}</small></span>
              <AdminIcon name="chevron" size={17} className="admin-quick-arrow" />
            </Link>
          ))}
        </div>
      </div>
      <p className="admin-dashboard-caption" aria-live="polite">
        {updatedAt
          ? `Dữ liệu cập nhật lúc ${updatedAt.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Ho_Chi_Minh" })} (giờ Việt Nam).`
          : loading ? "Đang tải số liệu…" : "Chưa cập nhật được số liệu."}
      </p>
    </div>
  );
}
