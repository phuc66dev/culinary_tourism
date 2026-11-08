import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../../admin-dashboard/utils/assetUrl.js';

export default function OwnerNotificationsPage() {
  const [data, setData] = useState({ items: [], unread_count: 0, total: 0 });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    axiosClient.get('/owner/notifications').then(({ data: result }) => { if (alive) setData(result); })
      .catch((e) => { if (alive) setError(apiErrorMessage(e, 'Không lấy được thông báo')); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);
  return <section className="rounded-xl border bg-white p-5">
    <h2 className="text-xl font-bold">Thông báo kiểm duyệt</h2>
    <p className="mt-1 text-sm text-slate-500">{data.unread_count} thông báo chưa đọc · {data.total} tổng số</p>
    {loading && <p className="mt-4 text-sm">Đang tải thông báo…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    {!loading && !data.items.length && <p className="mt-4 text-sm text-slate-500">Chưa có thông báo.</p>}
    <ul className="mt-4 divide-y">{data.items.map((item) => <li key={item.id}>
      <Link to={`/owner/notifications/${item.id}`} className="block rounded-lg p-3 hover:bg-amber-50">
        <div className="flex items-center gap-2 text-sm"><strong>{item.title || 'Thông báo'}</strong>
          {!item.is_read && <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs text-orange-900">Mới</span>}
        </div>
        <p className="mt-1 text-sm text-slate-600">{item.message}</p>
        <time className="text-xs text-slate-400">{item.created_at ? new Date(item.created_at).toLocaleString('vi-VN') : ''}</time>
      </Link>
    </li>)}</ul>
    {data.total > data.items.length && <p className="mt-4 text-xs text-slate-500">Đang hiển thị {data.items.length} thông báo mới nhất.</p>}
  </section>;
}
