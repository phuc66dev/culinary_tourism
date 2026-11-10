import React, { useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import ShopLocationMap from '../../maps/ShopLocationMap.jsx';
import ReviewDialog from '../components/ReviewDialog.jsx';
import ReviewQueue, { ReviewStatus } from '../components/ReviewQueue.jsx';
import { hasPermission } from '../hooks/useAdminSession.js';
import { apiErrorMessage, assetUrl } from '../utils/assetUrl.js';
import { formatVietnamDateTime as fmt } from '../utils/vietnamTime.js';

const fields = {
  name: 'Tên quán', address: 'Địa chỉ', ward: 'Phường', category: 'Loại quán',
  original_description: 'Mô tả tiếng Việt', location: 'Vị trí trên bản đồ',
  images: 'Hình ảnh', trigger_radius: 'Bán kính kích hoạt', audio_priority: 'Ưu tiên audio',
};

const columns = [
  { key: 'poi_name', label: 'Tên quán', render: (item) => item.poi_name || 'Quán chưa có tên' },
  { key: 'changes', label: 'Nội dung thay đổi', sortable: false, render: (item) => {
    const changed = item.diff.filter((entry) => entry.changed);
    return changed.length ? changed.map(({ field }) => fields[field] ?? field).join(', ') : '—';
  } },
  { key: 'created_at', label: 'Ngày gửi', render: (item) => <span className="whitespace-nowrap">{fmt(item.created_at)}</span> },
  { key: 'status', label: 'Trạng thái', render: (item) => <ReviewStatus status={item.status} /> },
];

function DiffValue({ field, value }) {
  if (field === 'location' && value?.coordinates) {
    return <ShopLocationMap coordinates={value.coordinates} centerOn={value.coordinates} />;
  }
  if (field === 'images' && Array.isArray(value) && value.length) {
    return (
      <ul className="grid grid-cols-2 gap-2">
        {value.map((image, index) => (
          <li key={`${index}:${image}`}>
            <a href={assetUrl(image)} target="_blank" rel="noreferrer noopener">
              <img src={assetUrl(image)} alt={`Ảnh quán ${index + 1}`} loading="lazy"
                className="h-24 w-full rounded-md object-contain" />
            </a>
          </li>
        ))}
      </ul>
    );
  }
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) {
    return <span className="text-slate-500">Chưa có</span>;
  }
  return (
    <span className="whitespace-pre-wrap break-words">
      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
    </span>
  );
}

function SubmissionReview({ item, close, reviewed, reload }) {
  const user = useAuthStore((state) => state.user);
  const canReview = item.status === 'pending' && hasPermission(user, 'poi:approve');
  const changedCount = item.diff.filter((entry) => entry.changed).length;
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState('');

  async function review(action) {
    if (busy || stale) return;
    if (action === 'approve' &&
      !window.confirm(`Cập nhật ${changedCount} trường của “${item.poi_name}” vào POI Master?`)) return;
    setBusy(true);
    setError('');
    try {
      await axiosClient.post(`/admin/submissions/${item.id}/review`, {
        action, admin_note: note.trim() || null, expected_revision: item.poi_revision,
      });
      reviewed(action === 'approve' ? `Đã duyệt và cập nhật “${item.poi_name}”.` : 'Đã từ chối và gửi lý do cho chủ quán.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Không thể xử lý đề xuất.'));
      if (err.response?.status === 409) {
        setStale(true);
        reload();
      }
    } finally {
      setBusy(false);
    }
  }

  const footer = canReview && (
    <div className="space-y-3">
      {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
        {error}{stale && ' Đóng và mở lại đề xuất để xem dữ liệu mới nhất.'}
      </p>}
      {!stale && rejecting && (
        <label className="block text-sm font-medium">
          Lý do từ chối (gửi về chủ quán)
          <textarea autoFocus rows={2} maxLength={500} value={note} disabled={busy}
            onChange={(event) => setNote(event.target.value)}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2" />
        </label>
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
              <button type="button" disabled={busy} onClick={() => { setRejecting(true); setError(''); }}
                className="rounded-lg bg-red-100 px-4 py-2 text-red-800 disabled:opacity-40">Từ chối</button>
              <button type="button" disabled={busy || item.poi_revision == null || !changedCount}
                onClick={() => review('approve')}
                className="rounded-lg bg-teal-700 px-4 py-2 text-white disabled:opacity-40">
                {busy ? 'Đang xử lý…' : 'Duyệt và cập nhật quán'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );

  return (
    <ReviewDialog title={item.poi_name || 'Chi tiết đề xuất'}
      description="So sánh thông tin hiện tại với nội dung chủ quán đề xuất"
      busy={busy} onClose={close} footer={footer}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
          <ReviewStatus status={item.status} />
          <span>Ngày gửi {fmt(item.created_at)}</span>
          <span>{changedCount} trường thay đổi</span>
        </div>
        {!item.diff.length && <p className="text-sm text-slate-600">Đề xuất chưa có nội dung để so sánh.</p>}
        {item.diff.map(({ field, current, proposed, changed }) => (
          <section key={field} className="space-y-2">
            <h4 className="text-sm font-semibold">
              {fields[field] ?? field}{' '}
              {!changed && <span className="font-normal text-slate-500">· Không đổi</span>}
            </h4>
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div className="min-w-0 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <dt className="mb-2 text-xs font-semibold text-slate-600">Hiện tại</dt>
                <dd><DiffValue field={field} value={current} /></dd>
              </div>
              <div className={`min-w-0 rounded-lg border p-3 ${changed ? 'border-teal-200 bg-teal-50' : 'border-slate-200 bg-slate-50'}`}>
                <dt className="mb-2 text-xs font-semibold text-slate-700">Đề xuất</dt>
                <dd><DiffValue field={field} value={proposed} /></dd>
              </div>
            </dl>
          </section>
        ))}
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

export default function SubmissionReviewPage() {
  return (
    <ReviewQueue endpoint="/admin/submissions" title="Duyệt đề xuất thay đổi"
      searchPlaceholder="Tên quán hoặc mã quán" columns={columns}
      renderDetail={(item, controls) => <SubmissionReview item={item} {...controls} />} />
  );
}
