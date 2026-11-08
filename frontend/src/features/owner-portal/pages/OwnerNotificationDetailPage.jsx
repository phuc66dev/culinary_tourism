import { FiArrowLeft, FiArrowRight } from 'react-icons/fi';
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../../admin-dashboard/utils/assetUrl.js';

export default function OwnerNotificationDetailPage({ onRead }) {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true); setError(''); setItem(null);
    axiosClient.get('/owner/notifications/' + id)
      .then(({ data }) => { if (alive) {
        setItem(data);
        onRead?.();
      } })
      .catch((err) => { if (alive) setError(apiErrorMessage(err, 'Không đọc được thông báo')); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [id, onRead]);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link to="/owner/notifications" className="inline-flex items-center gap-2 text-sm font-semibold text-orange-800 hover:underline"><FiArrowLeft aria-hidden="true" /> Tất cả thông báo</Link>
      {loading && <div role="status" className="rounded-xl border bg-white p-6 text-sm text-slate-600">Đang tải thông báo…</div>}
      {error && <div role="alert" className="rounded-xl border border-red-200 bg-white p-6 text-sm text-red-800"><h1 className="font-bold">Không mở được thông báo</h1><p className="mt-1">{error}</p></div>}
      {item && <article className="rounded-2xl border border-amber-100 bg-white p-5 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-bold text-orange-900">{item.type === 'registration_review' ? 'Hồ sơ chủ quán' : item.type === 'submission_review' ? 'Đề xuất cập nhật' : 'Thông báo'}</span><span className="text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}</span></div>
        <h1 className="mt-4 text-2xl font-bold leading-tight text-slate-900">{item.title || 'Thông báo từ ban quản trị'}</h1>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{item.message || 'Không có nội dung thông báo.'}</p>
        {item.admin_note && <section className="mt-6 rounded-xl border-l-4 border-orange-500 bg-amber-50 p-4 sm:p-5"><h2 className="text-sm font-bold text-slate-900">Ghi chú của ban quản trị</h2><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.admin_note}</p></section>}
        <div className="mt-7 border-t border-slate-100 pt-4"><Link to={item.type === 'registration_review' ? '/owner/status' : item.type === 'submission_review' ? '/owner/submissions' : '/owner/notifications'} className="inline-flex items-center gap-2 text-sm font-semibold text-orange-800 hover:underline">{item.type === 'registration_review' ? 'Xem trạng thái hồ sơ' : item.type === 'submission_review' ? 'Xem đề xuất' : 'Trở về thông báo'}<FiArrowRight aria-hidden="true" /></Link></div>
      </article>}
    </div>
  );
}
