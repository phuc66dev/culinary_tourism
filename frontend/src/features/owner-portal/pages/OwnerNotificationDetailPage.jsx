import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../../admin-dashboard/utils/assetUrl.js';

export default function OwnerNotificationDetailPage() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    axiosClient.get(`/owner/notifications/${id}`).then(({ data }) => { if (alive) setItem(data); })
      .catch((e) => { if (alive) setError(apiErrorMessage(e, 'Không đọc được thông báo')); });
    return () => { alive = false; };
  }, [id]);
  return <div className="rounded-xl border bg-white p-6">
    <Link to="/owner/notifications" className="text-sm text-orange-700 underline">← Trở về thông báo</Link>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    {!error && !item && <p className="mt-3 text-sm text-slate-500">Đang tải thông báo…</p>}
    {item && <article className="mt-4 space-y-3">
      <h2 className="text-xl font-bold">{item.title || 'Kết quả kiểm duyệt'}</h2>
      <time className="block text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString('vi-VN') : '—'}</time>
      <p className="text-sm">{item.message}</p>
      {item.admin_note && <div className="rounded-lg border-l-4 border-orange-500 bg-amber-50 p-4">
        <h3 className="text-sm font-semibold">Ghi chú của Ban quản trị</h3>
        <p className="mt-1 whitespace-pre-wrap text-sm">{item.admin_note}</p>
      </div>}
    </article>}
  </div>;
}
