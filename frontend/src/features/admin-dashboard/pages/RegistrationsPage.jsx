import React, { useEffect, useRef, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import ShopLocationMap from '../../maps/ShopLocationMap.jsx';
import ReviewDialog from '../components/ReviewDialog.jsx';
import ReviewQueue, { ReviewStatus } from '../components/ReviewQueue.jsx';
import { hasPermission } from '../hooks/useAdminSession.js';
import { apiErrorMessage, assetUrl } from '../utils/assetUrl.js';
import { formatVietnamDateTime as fmt } from '../utils/vietnamTime.js';

const columns = [
  { key: 'poi_name', label: 'Tên quán', render: (item) => item.poi_name || 'Quán chưa có tên' },
  { key: 'full_name', label: 'Chủ quán', render: (item) => item.full_name || '—' },
  { key: 'contact', label: 'Liên hệ', sortable: false, render: (item) => (
    <div className="min-w-32 break-words">
      <div>{item.phone || '—'}</div>
      {item.email && <div className="text-xs text-slate-500">{item.email}</div>}
    </div>
  ) },
  { key: 'created_at', label: 'Ngày gửi', render: (item) => <span className="whitespace-nowrap">{fmt(item.created_at)}</span> },
  { key: 'status', label: 'Trạng thái', render: (item) => <ReviewStatus status={item.status} /> },
];

function Field({ label, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="mt-0.5 break-words text-sm text-slate-900">{children || '—'}</dd>
    </div>
  );
}

function StorefrontImage({ src, name }) {
  const [failed, setFailed] = useState(false);
  const url = assetUrl(src);
  if (!url || failed) {
    return <p className="grid h-60 place-items-center rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-600">
      {failed ? 'Không tải được ảnh mặt tiền.' : 'Hồ sơ chưa có ảnh mặt tiền.'}
    </p>;
  }
  return (
    <a href={url} target="_blank" rel="noreferrer noopener" aria-label="Mở ảnh mặt tiền gốc">
      <img src={url} alt={`Mặt tiền ${name}`} onError={() => setFailed(true)}
        className="h-60 w-full rounded-lg border border-slate-200 object-contain" />
    </a>
  );
}

function RegistrationReview({ item, close, reviewed, reload }) {
  const user = useAuthStore((state) => state.user);
  const canReview = hasPermission(user, 'user:update');
  const canPublish = hasPermission(user, 'poi:toggle') &&
    (hasPermission(user, 'poi:update') || hasPermission(user, 'poi:create'));
  const canApprove = canReview && !item.linked_poi_id && ['pending', 'approved'].includes(item.status);
  const canReject = canReview && item.status === 'pending';
  const storedPin = item.poi_location?.coordinates;
  const [legacyPin, setLegacyPin] = useState(null);
  const [cccd, setCccd] = useState(null);
  const [cccdLoading, setCccdLoading] = useState(false);
  const [cccdError, setCccdError] = useState('');
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState('');
  const hideTimer = useRef(null);
  const cccdRequest = useRef(null);

  useEffect(() => () => {
    clearTimeout(hideTimer.current);
    cccdRequest.current?.abort();
  }, []);

  function hideCccd() {
    clearTimeout(hideTimer.current);
    setCccd(null);
  }

  async function revealCccd() {
    if (!window.confirm('Hiển thị số CCCD của chủ quán? Thao tác được ghi vào nhật ký hệ thống.')) return;
    const controller = new AbortController();
    cccdRequest.current = controller;
    setCccdLoading(true);
    setCccdError('');
    try {
      const { data } = await axiosClient.get(`/admin/registrations/${item.id}/cccd`, { signal: controller.signal });
      if (!controller.signal.aborted) {
        setCccd(data.cccd_number);
        hideTimer.current = setTimeout(hideCccd, 30_000);
      }
    } catch (err) {
      if (!controller.signal.aborted) setCccdError(apiErrorMessage(err, 'Không đọc được CCCD.'));
    } finally {
      if (!controller.signal.aborted) setCccdLoading(false);
    }
  }

  async function review(action) {
    if (busy || stale) return;
    setBusy(true);
    setError('');
    try {
      const decision = { action, admin_note: note.trim() || null };
      if (action === 'approve' && !storedPin && legacyPin) {
        decision.poi_location = { type: 'Point', coordinates: legacyPin };
      }
      await axiosClient.post(`/admin/registrations/${item.id}/review`, decision);
      reviewed(action === 'approve' ? `Đã duyệt và công khai “${item.poi_name}”.` : `Đã từ chối hồ sơ “${item.poi_name}”.`);
    } catch (err) {
      setError(apiErrorMessage(err, 'Không xử lý được hồ sơ.'));
      if (err.response?.status === 409) {
        setStale(true);
        reload();
      }
    } finally {
      setBusy(false);
    }
  }

  const footer = (error || canApprove || canReject) && (
    <div className="space-y-3">
      {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
        {error}{stale && ' Đóng và mở lại hồ sơ để xem dữ liệu mới nhất.'}
      </p>}
      {!stale && rejecting && (
        <label className="block text-sm font-medium">
          Lý do từ chối (gửi về chủ quán)
          <textarea autoFocus rows={2} maxLength={500} value={note} disabled={busy}
            onChange={(event) => setNote(event.target.value)}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2" />
        </label>
      )}
      {!stale && canApprove && !canPublish && !rejecting && (
        <p className="text-sm text-slate-600">Cần quyền công khai và quyền tạo hoặc cập nhật quán để duyệt.</p>
      )}
      {!stale && (
        <div className="flex flex-wrap justify-end gap-2 text-sm font-semibold">
          {rejecting ? (
            <>
              <button type="button" disabled={busy} onClick={() => { setRejecting(false); setNote(''); setError(''); }}
                className="rounded-lg border border-slate-300 px-4 py-2">Quay lại</button>
              <button type="button" disabled={busy || !note.trim()} onClick={() => review('reject')}
                className="rounded-lg bg-red-700 px-4 py-2 text-white disabled:opacity-40">
                {busy ? 'Đang gửi…' : 'Xác nhận từ chối'}
              </button>
            </>
          ) : (
            <>
              {canReject && <button type="button" disabled={busy} onClick={() => { setRejecting(true); setError(''); }}
                className="rounded-lg bg-red-100 px-4 py-2 text-red-800 disabled:opacity-40">Từ chối</button>}
              {canApprove && canPublish && <button type="button" disabled={busy || (!storedPin && !legacyPin)}
                onClick={() => review('approve')}
                className="rounded-lg bg-teal-700 px-4 py-2 text-white disabled:opacity-40">
                {busy ? 'Đang duyệt…' : 'Duyệt và công khai quán'}
              </button>}
            </>
          )}
        </div>
      )}
    </div>
  );

  return (
    <ReviewDialog title={item.poi_name || 'Hồ sơ chủ quán'} description="Đối chiếu hồ sơ đăng ký và vị trí quán"
      busy={busy} onClose={close} footer={footer}>
      <div className="space-y-5">
        <ReviewStatus status={item.status} />
        <dl className="grid gap-3 sm:grid-cols-2">
          <Field label="Chủ quán">{item.full_name}</Field>
          <Field label="Số điện thoại">{item.phone}</Field>
          <Field label="Email">{item.email}</Field>
          <Field label="Ngày gửi">{fmt(item.created_at)}</Field>
          <div className="sm:col-span-2"><Field label="Địa chỉ quán">{item.poi_address}</Field></div>
        </dl>
        <div className="grid items-start gap-4 md:grid-cols-2">
          <section className="min-w-0 space-y-2">
            <h4 className="text-sm font-semibold">Ảnh mặt tiền</h4>
            <StorefrontImage src={item.storefront_image_url} name={item.poi_name} />
          </section>
          <section className="min-w-0 space-y-2" aria-label="Vị trí quán">
            <h4 className="text-sm font-semibold">Vị trí quán</h4>
            {(storedPin || (canApprove && canPublish)) ? (
              <>
                <ShopLocationMap coordinates={storedPin ?? legacyPin} centerOn={storedPin}
                  showCenterPinButton={false} disabled={busy || stale}
                  onPick={storedPin ? undefined : setLegacyPin} />
                <p className="text-sm text-slate-600">
                  {storedPin ? 'Ghim do chủ quán gửi cùng hồ sơ.'
                    : legacyPin ? 'Đã chọn vị trí. Bấm trên bản đồ để thay đổi.'
                    : 'Hồ sơ cũ chưa có ghim. Bấm trên bản đồ để chọn vị trí trước khi duyệt.'}
                </p>
              </>
            ) : <p className="text-sm text-slate-600">Hồ sơ chưa có vị trí đã ghim.</p>}
          </section>
        </div>
        <div className="space-y-2 rounded-lg bg-slate-50 p-3">
          <h4 className="text-sm font-semibold">Căn cước công dân</h4>
          {item.cccd_available ? (
            <div className="flex flex-wrap items-center gap-3">
              <code aria-live="polite" className="tracking-widest">{cccd || '••••••••••••'}</code>
              {cccd ? (
                <>
                  <button type="button" onClick={hideCccd} className="text-sm font-semibold underline">Ẩn</button>
                  <span className="text-xs text-slate-600">Tự ẩn sau 30 giây</span>
                </>
              ) : canReview && (
                <button type="button" onClick={revealCccd} disabled={cccdLoading}
                  className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40">
                  {cccdLoading ? 'Đang giải mã…' : 'Xem CCCD'}
                </button>
              )}
            </div>
          ) : <p className="text-sm text-slate-600">Không có CCCD để đối chiếu.</p>}
          {cccdError && <p role="alert" className="text-sm text-red-800">{cccdError}</p>}
        </div>
        {item.linked_poi_id && <p className="text-sm font-medium text-green-800">Đã gắn quán trong POI Master.</p>}
        {item.status !== 'pending' && (
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            Đã xử lý lúc {fmt(item.reviewed_at)}.
            {item.admin_note && <p className="mt-1 whitespace-pre-wrap break-words">{item.admin_note}</p>}
          </div>
        )}
      </div>
    </ReviewDialog>
  );
}

export default function RegistrationsPage() {
  return (
    <ReviewQueue endpoint="/admin/registrations" title="Duyệt chủ quán"
      searchPlaceholder="Tên, quán, SĐT hoặc email" columns={columns}
      renderDetail={(item, controls) => <RegistrationReview item={item} {...controls} />} />
  );
}
