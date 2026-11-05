import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { hasPermission } from '../hooks/useAdminSession.js';
import AdminIcon from '../components/AdminIcon.jsx';

const METRICS = [
  { key: 'pois', label: 'Quán ăn', subtitle: 'Địa điểm trong hệ thống', permission: 'poi:update', href: '/admin/pois', icon: 'pin', request: () => axiosClient.get('/admin/pois', { params: { limit: 10 } }), count: (data) => data.total },
  { key: 'registrations', label: 'Hồ sơ chờ duyệt', subtitle: 'Đăng ký chủ quán', permission: 'user:read', href: '/admin/registrations', icon: 'registrations', request: () => axiosClient.get('/admin/registrations', { params: { status: 'pending', limit: 10 } }), count: (data) => data.total },
  { key: 'submissions', label: 'Đề xuất chờ duyệt', subtitle: 'Thay đổi thông tin POI', permission: 'poi:approve', href: '/admin/submissions', icon: 'submissions', request: () => axiosClient.get('/admin/submissions', { params: { status: 'pending', limit: 10 } }), count: (data) => data.total },
  { key: 'audio', label: 'Audio đang xử lý', subtitle: 'Đang chạy hoặc chờ', permission: 'poi:update', href: '/admin/audio-tasks', icon: 'audio', request: () => axiosClient.get('/admin/audio-tasks'), count: (data) => (data.items || []).filter((task) => ['queued', 'running'].includes(task.status)).length },
];

const QUICK_ACTIONS = [
  { label: 'Quản lý POI', description: 'Xem danh sách và trạng thái công khai', href: '/admin/pois', icon: 'pin', permission: 'poi:update' },
  { label: 'Duyệt hồ sơ chủ quán', description: 'Xử lý hồ sơ cần xác minh', href: '/admin/registrations', icon: 'registrations', permission: 'user:read' },
  { label: 'Duyệt đề xuất', description: 'Đối chiếu thay đổi trước khi công khai', href: '/admin/submissions', icon: 'submissions', permission: 'poi:approve' },
  { label: 'Giám sát Audio', description: 'Theo dõi và nghe thử âm thanh', href: '/admin/audio-tasks', icon: 'audio', permission: 'poi:update' },
];

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [retry, setRetry] = useState(0);
  const visible = METRICS.filter((item) => hasPermission(user, item.permission));

  const refresh = useCallback(() => setRetry((n) => n + 1), []);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const currentMetrics = METRICS.filter((item) => hasPermission(user, item.permission));
    Promise.allSettled(currentMetrics.map((item) => item.request())).then((results) => {
      if (cancelled) return;
      const next = {};
      results.forEach((result, index) => {
        const metric = currentMetrics[index];
        if (result.status === 'fulfilled') {
          const value = metric.count(result.value.data);
          next[metric.key] = Number.isFinite(value) ? value : null;
        } else next[metric.key] = null;
      });
      setStats(next);
      setUpdatedAt(new Date());
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [user, retry]);

  return (
    <div className="admin-dashboard">
      <div className="admin-dashboard-heading">
        <div><div className="admin-eyebrow">TỔNG QUAN</div><h1>Dashboard</h1><p>Theo dõi dữ liệu và các công việc quản trị.</p></div>
        <button type="button" className="admin-refresh-button" onClick={refresh} disabled={loading}><AdminIcon name="refresh" size={16} />{loading ? 'Đang cập nhật' : 'Làm mới'}</button>
      </div>
      <div className="admin-metrics-grid">
        {visible.map((item) => (
          <Link key={item.key} to={item.href} className="admin-metric-card">
            <div className="admin-metric-head"><span>{item.label}</span><AdminIcon name={item.icon} size={19} /></div>
            <div className="admin-metric-value">{loading && !(item.key in stats) ? '···' : stats[item.key] ?? '—'}</div>
            <div className="admin-metric-foot"><span>{item.subtitle}</span><AdminIcon name="arrow" size={16} /></div>
          </Link>
        ))}
        {!visible.length && <p className="admin-empty-state">Tài khoản hiện chưa có quyền xem số liệu quản trị.</p>}
      </div>
      <div className="admin-dashboard-section">
        <div className="admin-section-header"><h2>Truy cập nhanh</h2><p>Các công việc thường dùng</p></div>
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
      <p className="admin-dashboard-caption" aria-live="polite">{updatedAt ? `Dữ liệu cập nhật lúc ${updatedAt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}.` : 'Đang tải số liệu…'}</p>
    </div>
  );
}
