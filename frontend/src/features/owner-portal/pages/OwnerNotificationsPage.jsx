import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../../admin-dashboard/utils/assetUrl.js';

export default function OwnerNotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    axiosClient.get('/owner/notifications')
      .then(({ data }) => {
        if (alive) setNotifications(Array.isArray(data) ? data : data?.items || []);
      })
      .catch((e) => {
        if (alive) setError(apiErrorMessage(e, 'Không tải được danh sách thông báo'));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => { alive = false; };
  }, []);

  return (
    <div className="rounded-xl border bg-white p-6 shadow-xs">
      <h2 className="text-xl font-bold text-slate-800">Thông báo từ Quản trị viên</h2>
      <p className="mt-1 text-sm text-slate-500">Xem các thông báo về trạng thái duyệt hồ sơ và duyệt món ăn.</p>

      {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
      {loading && <p className="mt-4 text-sm text-slate-500">Đang tải thông báo…</p>}

      {!loading && notifications.length === 0 && (
        <div className="mt-6 rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-500">
          Chưa có thông báo nào.
        </div>
      )}

      {notifications.length > 0 && (
        <div className="mt-4 divide-y">
          {notifications.map((n) => (
            <div key={n.id || n._id} className="py-3 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-800">{n.title || 'Thông báo hệ thống'}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{n.created_at ? new Date(n.created_at).toLocaleString('vi-VN') : '—'}</p>
                <p className="text-sm text-slate-600 mt-1 line-clamp-1">{n.message}</p>
              </div>
              <Link to={`/owner/notifications/${n.id || n._id}`} className="text-xs font-medium text-orange-700 underline shrink-0 ml-4">
                Xem chi tiết →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
