import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { hasPermission } from '../hooks/useAdminSession.js';
import { apiErrorMessage } from '../utils/assetUrl.js';

const FIELDS = {
  name: 'Tên quán', address: 'Địa chỉ', ward: 'Phường', category: 'Loại quán',
  original_description: 'Mô tả tiếng Việt', location: 'Tọa độ', images: 'Hình ảnh',
  trigger_radius: 'Bán kính kích hoạt', audio_priority: 'Ưu tiên audio',
};
const STATUS = { pending: 'Chờ duyệt', approved: 'Đã duyệt', rejected: 'Từ chối', processing: 'Đang xử lý', review_error: 'Cần khôi phục' };
const STYLE = { pending: 'bg-amber-100 text-amber-900', approved: 'bg-green-100 text-green-900', rejected: 'bg-red-100 text-red-900' };
const fmtDate = (date) => date ? new Date(date).toLocaleString('vi-VN') : '—';
function Value({ value }) {
  if (value === undefined || value === null || value === '') return <span className="italic text-slate-400">Chưa có</span>;
  if (typeof value === 'object') return <pre className="whitespace-pre-wrap break-all text-xs">{JSON.stringify(value, null, 2)}</pre>;
  return <span className="whitespace-pre-wrap break-words">{String(value)}</span>;
}

export default function SubmissionReviewPage() {
  const user = useAuthStore((s) => s.user);
  const canApprove = hasPermission(user, 'poi:approve');
  const [status, setStatus] = useState('pending');
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0, counts: {} });
  const [selectedId, setSelectedId] = useState(null);
  const [note, setNote] = useState('');
  const [rejecting, setRejecting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [refresh, setRefresh] = useState(0);
  const limit = 25;
  useEffect(() => { const t = setTimeout(() => setQ(search.trim()), 300); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(0); setSelectedId(null); }, [q, status]);
  const reload = () => setRefresh((v) => v + 1);
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const { data: res } = await axiosClient.get('/admin/submissions', {
        params: { status: status || undefined, q: q || undefined, limit, skip: page * limit },
      });
      setData(res);
    } catch (e) { setError(apiErrorMessage(e, 'Không tải được submissions')); }
    finally { setLoading(false); }
  }, [status, q, page, refresh]);
  useEffect(() => { load(); }, [load]);
  const selected = useMemo(() => data.items.find((i) => i.id === selectedId) || null, [data.items, selectedId]);
  useEffect(() => { setNote(''); setRejecting(false); }, [selectedId]);

  async function review(action) {
    if (!selected || busy) return;
    if (action === 'reject' && !note.trim()) { setError('Phải nhập lý do từ chối.'); return; }
    if (action === 'approve' && !window.confirm(`Merge ${selected.diff.filter((f) => f.changed).length} trường của "${selected.poi_name}" vào POI Master?`)) return;
    setBusy(true); setError('');
    try {
      const { data: res } = await axiosClient.post(`/admin/submissions/${selected.id}/review`, {
        action, admin_note: note.trim() || null, expected_revision: selected.poi_revision,
      });
      setMessage(action === 'approve' ? `Đã duyệt và cập nhật dataset_version = ${res.dataset_version}` : 'Đã từ chối và gửi lý do cho chủ quán');
      setSelectedId(null); reload();
    } catch (e) {
      setError(apiErrorMessage(e, 'Không thể xử lý đề xuất'));
      if (e.response?.status === 409) reload();
    } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-4">
        <h2 className="text-xl font-bold">Duyệt đề xuất thay đổi</h2>
        {/* <p className="mt-1 text-sm text-slate-500">So sánh từng trường trước khi merge vào collection POI. Khi duyệt thành công, phiên bản dataset được tăng tự động.</p> */}
        <div className="mt-4 flex flex-wrap gap-2">
          {[["pending", "Chờ duyệt"], ["approved", "Đã duyệt"], ["rejected", "Đã từ chối"], ["", "Tất cả"]].map(([value, label]) => (
            <button key={value} onClick={() => setStatus(value)} aria-pressed={status === value}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${status === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}>
              {label}{value ? ` (${data.counts?.[value] ?? 0})` : ''}
            </button>
          ))}
          <input aria-label="Tìm theo tên quán" type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm quán…"
            className="ml-auto rounded-lg border px-3 py-1 text-sm" />
        </div>
      </div>
      {message && <p role="status" className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</p>}
      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="overflow-hidden rounded-xl border bg-white" aria-label="Danh sách đề xuất">
          {loading && <p className="p-4 text-sm text-slate-500">Đang tải…</p>}
          {!loading && !data.items.length && <p className="p-4 text-sm text-slate-500">Không có đề xuất phù hợp.</p>}
          <ul className="divide-y">
            {data.items.map((item) => <li key={item.id}>
              <button onClick={() => setSelectedId(item.id)} aria-current={selectedId === item.id}
                className={`w-full p-4 text-left hover:bg-slate-50 ${selectedId === item.id ? 'bg-slate-100' : ''}`}>
                <div className="flex justify-between gap-2"><strong className="truncate text-sm">{item.poi_name}</strong>
                  <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] ${STYLE[item.status] || 'bg-slate-100'}`}>{STATUS[item.status] || item.status}</span></div>
                <p className="mt-1 text-xs text-slate-500">{fmtDate(item.created_at)} · {item.diff.filter((d) => d.changed).length} trường thay đổi</p>
              </button>
            </li>)}
          </ul>
          <div className="flex items-center justify-between gap-2 border-t p-3 text-xs">
            <button disabled={!page || loading} onClick={() => setPage((v) => v - 1)} className="rounded border px-2 py-1 disabled:opacity-40">← Trước</button>
            <span>{page + 1}/{Math.max(1, Math.ceil(data.total / limit))}</span>
            <button disabled={(page + 1) * limit >= data.total || loading} onClick={() => setPage((v) => v + 1)} className="rounded border px-2 py-1 disabled:opacity-40">Sau →</button>
          </div>
        </section>
        <section className="rounded-xl border bg-white p-4 lg:col-span-2" aria-label="So sánh nội dung">
          {!selected ? <p className="text-sm text-slate-500">Chọn một đề xuất để xem nội dung hiện tại và nội dung mới của quán.</p> : <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div><h3 className="text-lg font-bold">{selected.poi_name}</h3>
                <p className="text-xs text-slate-500">Phiên bản POI hiện tại: {selected.poi_revision ?? 'Không tồn tại'} · Mã đề xuất: {selected.id}</p></div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STYLE[selected.status] || 'bg-slate-100'}`}>{STATUS[selected.status] || selected.status}</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs font-semibold uppercase tracking-wide">
              <div className="rounded-lg bg-slate-100 p-3">Nội dung hiện tại</div>
              <div className="rounded-lg bg-teal-100 p-3 text-teal-900">Nội dung chủ quán đề xuất</div>
            </div>
            {!selected.diff.length && <p className="text-sm text-amber-700">Đề xuất chưa có nội dung để so sánh.</p>}
            {selected.diff.map((d) => <div key={d.field} className="space-y-1">
              <h4 className="text-sm font-semibold">{FIELDS[d.field] || d.field} {d.changed ? <span className="text-amber-700">· Có thay đổi</span> : <span className="text-slate-400">· Không đổi</span>}</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="min-w-0 rounded-lg border bg-slate-50 p-3"><Value value={d.current} /></div>
                <div className={`min-w-0 rounded-lg border p-3 ${d.changed ? 'border-teal-300 bg-teal-50' : 'bg-slate-50'}`}><Value value={d.proposed} /></div>
              </div>
            </div>)}
            {selected.status === 'pending' && canApprove && <div className="border-t pt-4">
              {rejecting ? <div className="space-y-2">
                <label htmlFor="submission-note" className="block text-sm font-medium">Lý do từ chối (sẽ gửi về chủ quán)</label>
                <textarea id="submission-note" rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)}
                  className="w-full rounded-lg border p-2 text-sm" placeholder="Nêu rõ nội dung cần bổ sung hoặc sửa lại…" />
                <p className="text-right text-xs text-slate-400">{note.length}/500</p>
                <div className="flex gap-2"><button onClick={() => setRejecting(false)} disabled={busy} className="rounded-lg bg-slate-100 px-4 py-2 text-sm">Hủy</button>
                  <button onClick={() => review('reject')} disabled={busy || !note.trim()} className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Xác nhận từ chối</button></div>
              </div> : <div className="flex gap-2">
                <button onClick={() => review('approve')} disabled={busy || selected.poi_revision === null || !selected.diff.length || !selected.diff.some((d) => d.changed)}
                  className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{busy ? 'Đang xử lý…' : 'Phê duyệt & Merge'}</button>
                <button onClick={() => setRejecting(true)} disabled={busy} className="rounded-lg bg-red-100 px-4 py-2 text-sm font-semibold text-red-800">Từ chối</button>
              </div>}
            </div>}
            {selected.status !== 'pending' && <p className="rounded-lg bg-slate-50 p-3 text-sm">Đã xử lý: {fmtDate(selected.reviewed_at)} {selected.admin_note && <> · Lý do/ghi chú: {selected.admin_note}</>}</p>}
          </div>}
        </section>
      </div>
    </div>
  );
}
