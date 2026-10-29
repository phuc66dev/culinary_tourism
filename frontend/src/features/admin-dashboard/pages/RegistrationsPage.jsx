import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { assetUrl, apiErrorMessage } from '../utils/assetUrl.js';
import { hasPermission } from '../hooks/useAdminSession.js';
import { formatVietnamDateTime } from '../utils/vietnamTime.js';

/**
 * RegistrationsPage — Kiểm duyệt đơn đăng ký Chủ quán (`poi_owner_registrations`) & giải mã CCCD Fernet.
 * Phụ trách: Vũ (Task 3.5)
 *
 * - Xem thông tin quán + ảnh mặt tiền; CCCD chỉ giải mã khi bấm "Xem CCCD" (có xác nhận, ghi audit, tự ẩn sau 30s).
 * - "Phê duyệt" → backend bật is_poi_owner_verified. "Từ chối" → bắt buộc nhập lý do gửi về chủ quán.
 */
const TABS = [
  ['pending', 'Chờ duyệt'],
  ['approved', 'Đã duyệt'],
  ['rejected', 'Đã từ chối'],
  ['', 'Tất cả'],
];
const STATUS_LABEL = { pending: 'Chờ duyệt', approved: 'Đã duyệt', rejected: 'Đã từ chối' };
const STATUS_STYLE = { pending: 'bg-amber-100 text-amber-800', approved: 'bg-green-100 text-green-800', rejected: 'bg-red-100 text-red-800' };
const CCCD_AUTO_HIDE_MS = 30_000;
const NOTE_MAX = 500;

const fmt = formatVietnamDateTime;

function Field({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-900">{children || '—'}</dd>
    </div>
  );
}

function StorefrontImage({ src, alt }) {
  const [failed, setFailed] = useState(false);
  const url = assetUrl(src);
  if (!url || failed) {
    return <div className="flex h-40 items-center justify-center rounded-lg border border-dashed border-slate-300 text-sm text-slate-500">Chưa có ảnh mặt tiền{failed ? ' (không tải được)' : ''}</div>;
  }
  return (
    <a href={url} target="_blank" rel="noreferrer noopener" title="Mở ảnh gốc">
      <img src={url} alt={alt} onError={() => setFailed(true)} className="max-h-64 w-full rounded-lg border border-slate-200 object-cover" />
    </a>
  );
}

export default function RegistrationsPage() {
  const user = useAuthStore((s) => s.user);
  const canReview = hasPermission(user, 'user:update');

  const [tab, setTab] = useState('pending');
  const [page, setPage] = useState(0);
  const limit = 25;
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [data, setData] = useState({ items: [], counts: {}, total: 0 });
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  const [cccd, setCccd] = useState(null);
  const [cccdLoading, setCccdLoading] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState('');
  const [toast, setToast] = useState('');
  const hideTimer = useRef(null);

  useEffect(() => { const t = setTimeout(() => setQuery(search.trim()), 300); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(0); setSelectedId(null); }, [query, tab]);

  const load = useCallback(async () => {
    setLoading(true);
    setListError('');
    try {
      const { data: res } = await axiosClient.get('/admin/registrations', { params: { status: tab || undefined, q: query || undefined, skip: page * limit, limit } });
      setData(res);
    } catch (e) {
      setListError(apiErrorMessage(e, 'Không tải được danh sách'));
    } finally {
      setLoading(false);
    }
  }, [tab, query, page]);

  useEffect(() => { load(); }, [load]);

  const selected = useMemo(() => data.items.find((i) => i.id === selectedId) || null, [data.items, selectedId]);

  const resetDetailState = useCallback(() => {
    clearTimeout(hideTimer.current);
    setCccd(null); setRejecting(false); setNote(''); setActionError('');
  }, []);
  useEffect(() => { resetDetailState(); }, [selectedId, resetDetailState]);
  useEffect(() => () => clearTimeout(hideTimer.current), []);

  async function revealCccd() {
    if (!window.confirm('Hiển thị số CCCD của chủ quán?\nThao tác này được ghi vào nhật ký hệ thống (audit log).')) return;
    setCccdLoading(true);
    setActionError('');
    try {
      const { data: res } = await axiosClient.get(`/admin/registrations/${selected.id}/cccd`);
      setCccd(res.cccd_number);
      clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => setCccd(null), CCCD_AUTO_HIDE_MS);
    } catch (e) {
      setActionError(apiErrorMessage(e, 'Không giải mã được CCCD'));
    } finally {
      setCccdLoading(false);
    }
  }

  async function review(action) {
    if (submitting) return;
    if (action === 'reject' && !note.trim()) { setActionError('Vui lòng nhập lý do từ chối để gửi về chủ quán.'); return; }
    if (action === 'approve' && !window.confirm(`Phê duyệt "${selected.poi_name}"? Chủ quán sẽ được cấp quyền quản lý quán.`)) return;
    setSubmitting(true);
    setActionError('');
    try {
      await axiosClient.post(`/admin/registrations/${selected.id}/review`, { action, admin_note: note.trim() || null });
      setToast(action === 'approve' ? `Đã phê duyệt "${selected.poi_name}".` : `Đã từ chối "${selected.poi_name}" và gửi lý do cho chủ quán.`);
      setSelectedId(null);
      await load();
    } catch (e) {
      setActionError(apiErrorMessage(e, 'Không xử lý được hồ sơ'));
      if (e.response?.status === 409) load(); // hồ sơ vừa được admin khác xử lý
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => { if (!toast) return undefined; const t = setTimeout(() => setToast(''), 5000); return () => clearTimeout(t); }, [toast]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold">Duyệt chủ quán</h2>
          <input
            type="search" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tên, quán, SĐT, email…" aria-label="Tìm hồ sơ"
            className="w-full max-w-xs rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-500"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2" role="tablist">
          {TABS.map(([value, label]) => {
            const count = value ? data.counts?.[value] : undefined;
            return (
              <button
                key={label} role="tab" aria-selected={tab === value} onClick={() => { setTab(value); setSelectedId(null); }}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${tab === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
              >
                {label}{count !== undefined ? ` (${count})` : ''}
              </button>
            );
          })}
        </div>
      </div>

      {toast && <div role="status" className="rounded-xl border border-green-300 bg-green-50 px-4 py-2 text-sm text-green-800">{toast}</div>}
      {listError && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{listError}</div>}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="overflow-hidden rounded-xl border bg-white lg:col-span-2">
          {loading && data.items.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Đang tải…</p>
          ) : data.items.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Không có hồ sơ nào.</p>
          ) : (
            <ul className="divide-y" aria-busy={loading}>
              {data.items.map((item) => (
                <li key={item.id}>
                  <button
                    onClick={() => setSelectedId(item.id)} aria-current={item.id === selectedId}
                    className={`w-full px-4 py-3 text-left hover:bg-slate-50 ${item.id === selectedId ? 'bg-slate-100' : ''}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold text-slate-900">{item.poi_name || '(chưa đặt tên quán)'}</span>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[item.status] || ''}`}>{STATUS_LABEL[item.status] || item.status}</span>
                    </div>
                    <div className="mt-0.5 truncate text-xs text-slate-600">{item.full_name} · {item.phone}</div>
                    <div className="text-[11px] text-slate-400">{fmt(item.created_at)}</div>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center justify-between gap-2 border-t p-3 text-xs">
            <button disabled={page === 0 || loading} onClick={() => { setPage((p) => p - 1); setSelectedId(null); }} className="rounded border px-3 py-1 disabled:opacity-40">← Trước</button>
            <span>{data.total} hồ sơ · Trang {page + 1}/{Math.max(1, Math.ceil(data.total / limit))}</span>
            <button disabled={loading || (page + 1) * limit >= data.total} onClick={() => { setPage((p) => p + 1); setSelectedId(null); }} className="rounded border px-3 py-1 disabled:opacity-40">Sau →</button>
          </div>
        </div>

        <div className="rounded-xl border bg-white p-4 lg:col-span-3">
          {!selected ? (
            <p className="text-sm text-slate-500">Chọn một hồ sơ ở danh sách bên trái để xem chi tiết và đối chiếu.</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-base font-bold">{selected.poi_name}</h3>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[selected.status] || ''}`}>{STATUS_LABEL[selected.status] || selected.status}</span>
              </div>

              <StorefrontImage src={selected.storefront_image_url} alt={`Mặt tiền ${selected.poi_name}`} />

              <dl className="grid gap-3 sm:grid-cols-2">
                <Field label="Chủ quán">{selected.full_name}</Field>
                <Field label="Số điện thoại">{selected.phone}</Field>
                <Field label="Email">{selected.email}</Field>
                <Field label="Ngày gửi (GMT+7)">{fmt(selected.created_at)}</Field>
                <div className="sm:col-span-2"><Field label="Địa chỉ quán">{selected.poi_address}</Field></div>
              </dl>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Số CCCD (đã mã hoá khi lưu trữ)</div>
                {!selected.cccd_available ? (
                  <p className="mt-1 text-sm text-amber-700">Hồ sơ không có CCCD — không thể đối chiếu.</p>
                ) : cccd ? (
                  <div className="mt-1 flex items-center gap-3">
                    <code className="rounded bg-white px-2 py-1 text-base font-semibold tracking-widest" aria-live="polite">{cccd}</code>
                    <button onClick={() => { clearTimeout(hideTimer.current); setCccd(null); }} className="text-xs font-medium text-slate-600 underline">Ẩn</button>
                    <span className="text-[11px] text-slate-400">Tự ẩn sau 30 giây</span>
                  </div>
                ) : (
                  <div className="mt-1 flex items-center gap-3">
                    <span className="text-base tracking-widest text-slate-400">••••••••••••</span>
                    {canReview ? (
                      <button onClick={revealCccd} disabled={cccdLoading} className="rounded bg-slate-800 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-700 disabled:opacity-50">
                        {cccdLoading ? 'Đang giải mã…' : 'Xem CCCD'}
                      </button>
                    ) : <span className="text-xs text-slate-500">Bạn không có quyền xem CCCD</span>}
                  </div>
                )}
              </div>

              {actionError && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{actionError}</div>}

              {selected.status === 'pending' && canReview && (
                rejecting ? (
                  <div className="space-y-2">
                    <label htmlFor="reject-note" className="block text-sm font-medium text-slate-700">Lý do từ chối (gửi về chủ quán)</label>
                    <textarea
                      id="reject-note" rows={3} maxLength={NOTE_MAX} value={note} onChange={(e) => setNote(e.target.value)} autoFocus
                      placeholder="VD: Ảnh mặt tiền bị mờ, vui lòng chụp lại rõ bảng hiệu."
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-red-400"
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-slate-400">{note.length}/{NOTE_MAX}</span>
                      <div className="flex gap-2">
                        <button onClick={() => { setRejecting(false); setNote(''); setActionError(''); }} disabled={submitting} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200">Quay lại</button>
                        <button onClick={() => review('reject')} disabled={submitting || !note.trim()} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50">
                          {submitting ? 'Đang gửi…' : 'Xác nhận từ chối'}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <button onClick={() => review('approve')} disabled={submitting} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50">
                      {submitting ? 'Đang xử lý…' : 'Phê duyệt'}
                    </button>
                    <button onClick={() => setRejecting(true)} disabled={submitting} className="rounded-lg bg-red-100 px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-200">Từ chối</button>
                  </div>
                )
              )}

              {selected.status !== 'pending' && (
                <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                  Đã xử lý lúc {fmt(selected.reviewed_at)}.{selected.admin_note && <> Ghi chú: <em>{selected.admin_note}</em></>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
