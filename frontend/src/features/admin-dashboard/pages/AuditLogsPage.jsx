import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { vietnamDateParts, vietnamLocalToUtcIso } from '../utils/vietnamTime.js';

const PAGE_SIZE = 25;
const FILTERS_INITIAL = { q: '', action: '', user_id: '', resource: '', from_time: '', to_time: '' };
const ACTIONS = [
  ['poi.create', 'Thêm quán ăn'],
  ['poi.update', 'Cập nhật quán ăn'],
  ['poi.english_update', 'Sửa bản dịch tiếng Anh'],
  ['poi.delete_requested', 'Yêu cầu xóa quán'],
  ['poi.delete', 'Xóa quán ăn'],
  ['owner.registration_approve', 'Phê duyệt chủ quán'],
  ['owner.registration_reject', 'Từ chối chủ quán'],
  ['owner.cccd_reveal', 'Xem thông tin CCCD'],
  ['poi.submission_approve', 'Phê duyệt đề xuất'],
  ['poi.submission_reject', 'Từ chối đề xuất'],
  ['audio.task_enqueue', 'Tạo tác vụ audio'],
  ['audio.task_pause', 'Tạm dừng audio'],
  ['audio.task_resume', 'Tiếp tục audio'],
  ['audio.task_cancel', 'Hủy tác vụ audio'],
  ['audio.task_completed', 'Hoàn tất audio'],
  ['audio.task_purged', 'Dọn lịch sử audio'],
  ['auth.login', 'Đăng nhập'],
  ['auth.login_failed', 'Đăng nhập thất bại'],
  ['auth.login_rate_limited', 'Chặn đăng nhập quá nhiều lần'],
  ['auth.refresh', 'Gia hạn phiên đăng nhập'],
  ['auth.logout', 'Đăng xuất'],
  ['auth.change_password', 'Đổi mật khẩu'],
  ['user.create', 'Tạo tài khoản'],
  ['user.update', 'Cập nhật tài khoản'],
  ['user.soft_delete', 'Vô hiệu hóa tài khoản'],
  ['user.password_reset', 'Đặt lại mật khẩu'],
  ['role.create', 'Tạo vai trò'],
  ['role.update', 'Cập nhật vai trò'],
  ['role.delete', 'Xóa vai trò'],
];
const ACTION_LABELS = Object.fromEntries(ACTIONS);
const DETAIL_LABELS = {
  before: 'Trước khi thay đổi', after: 'Sau khi thay đổi', changed_fields: 'Trường đã thay đổi',
  fields: 'Trường được cập nhật', poi_name: 'Tên quán', address: 'Địa chỉ', ward: 'Phường',
  role: 'Vai trò', previous_role: 'Vai trò trước', is_active: 'Trạng thái tài khoản',
  dataset_version: 'Phiên bản dữ liệu', status: 'Trạng thái hồ sơ', has_note: 'Có ghi chú duyệt',
  deleted_poi: 'Số quán đã xóa', deleted_localizations: 'Số bản dịch đã xóa',
  deleted_menu_items: 'Số món đã xóa', languages: 'Ngôn ngữ', poi_id: 'Mã quán',
  permissions: 'Quyền truy cập', full_name: 'Họ tên', reason: 'Lý do',
};
const ROLE_LABELS = { super_admin: 'Super Admin', admin: 'Admin', poi_owner: 'Chủ quán', user: 'Người dùng' };
const TARGET_TYPES = {
  user: 'Tài khoản', poi: 'Quán ăn', role: 'Vai trò', registration: 'Hồ sơ chủ quán',
  submission: 'Đề xuất chỉnh sửa', audio_task: 'Tác vụ audio', audio_tasks: 'Tác vụ audio', auth: 'Xác thực',
};

// The API historically returned offset-less UTC strings; never parse these as local time.
const dateTime = vietnamDateParts;
const isoLocal = vietnamLocalToUtcIso;

function resourceParts(resource = '') {
  const [type, ...id] = String(resource).split(':');
  return { type, id: id.join(':') };
}

function actionLabel(action) { return ACTION_LABELS[action] || action || 'Hoạt động hệ thống'; }

function targetLabel(item) {
  const { type, id } = resourceParts(item.resource);
  const title = item.target_name || item.details?.poi_name || item.details?.target_name;
  if (title) return title;
  if (type === 'role') return ROLE_LABELS[id] || id;
  if (type === 'auth') return 'Phiên đăng nhập';
  return TARGET_TYPES[type] || 'Đối tượng hệ thống';
}

function displayValue(value, key) {
  if (value === undefined || value === null || value === '') return '—';
  if (key === 'role' && ROLE_LABELS[value]) return ROLE_LABELS[value];
  if (key === 'status' && value === 'approved') return 'Đã phê duyệt';
  if (key === 'status' && value === 'rejected') return 'Đã từ chối';
  if (key === 'is_active') return value ? 'Đang hoạt động' : 'Đã vô hiệu hóa';
  if (typeof value === 'boolean') return value ? 'Có' : 'Không';
  if (Array.isArray(value)) return value.length ? value.map((entry) => displayValue(entry)).join(', ') : 'Không có';
  if (typeof value === 'object') return Object.entries(value).map(([k, v]) => `${DETAIL_LABELS[k] || k}: ${displayValue(v, k)}`).join(' · ');
  return String(value);
}

function EventStatus({ action }) {
  if (action === 'auth.login_failed') return <span className="rounded-md bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700">Thất bại</span>;
  if (action === 'auth.login_rate_limited') return <span className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">Bị chặn</span>;
  if (action === 'poi.delete_requested') return <span className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">Yêu cầu</span>;
  return <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">Đã ghi nhận</span>;
}

function Details({ item }) {
  const details = item.details || {};
  const { type, id } = resourceParts(item.resource);
  const before = details.before;
  const after = details.after;
  const remaining = Object.entries(details).filter(([key]) => !['before', 'after'].includes(key));
  const [showRaw, setShowRaw] = useState(false);
  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 text-sm shadow-sm" aria-label={`Chi tiết sự kiện ${item.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <h3 className="font-semibold text-slate-900">{actionLabel(item.action)}</h3>
          <p className="mt-1 text-xs text-slate-500">Mã hành động: <code>{item.action}</code></p>
        </div>
        <EventStatus action={item.action} />
      </div>
      <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2 xl:grid-cols-3">
        <Info label="Thực hiện bởi" value={item.actor_name || item.actor_email || (item.user_id ? 'Tài khoản quản trị' : 'Hệ thống / chưa xác định')} secondary={item.actor_name ? item.actor_email : null} />
        <Info label="Vai trò" value={ROLE_LABELS[item.actor_role] || item.actor_role || 'Chưa lưu'} />
        <Info label="Thời gian" value={`${dateTime(item.created_at).time} ${dateTime(item.created_at).day}`} />
        <Info label="Đối tượng tác động" value={targetLabel(item)} secondary={item.target_email || null} />
        <Info label="Loại đối tượng" value={TARGET_TYPES[type] || type || 'Không xác định'} />
        <Info label="Địa chỉ IP" value={item.ip || 'Chưa ghi nhận'} />
      </div>
      {(before !== undefined || after !== undefined) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {[['Trước khi thay đổi', before], ['Sau khi thay đổi', after]].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <h4 className="mb-2 font-semibold text-slate-700">{label}</h4>
              {value && typeof value === 'object' && !Array.isArray(value) ? (
                <dl className="space-y-2">{Object.entries(value).map(([key, entry]) => <div key={key} className="flex flex-wrap justify-between gap-2"><dt className="text-slate-500">{DETAIL_LABELS[key] || key}</dt><dd className="font-medium text-slate-800">{displayValue(entry, key)}</dd></div>)}</dl>
              ) : <p className="text-slate-600">{value == null ? 'Không có dữ liệu' : displayValue(value)}</p>}
            </div>
          ))}
        </div>
      )}
      {remaining.length > 0 ? (
        <div>
          <h4 className="mb-2 font-semibold text-slate-800">Thông tin bổ sung</h4>
          <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
            {remaining.map(([key, value]) => <div key={key} className="min-w-0"><dt className="text-xs text-slate-500">{DETAIL_LABELS[key] || key}</dt><dd className="break-words text-slate-800">{displayValue(value, key)}</dd></div>)}
          </dl>
        </div>
      ) : before === undefined && after === undefined ? <p className="text-slate-500">Sự kiện này không lưu dữ liệu trước/sau.</p> : null}
      <div className="border-t border-slate-100 pt-3">
        <button type="button" onClick={() => setShowRaw((value) => !value)} aria-expanded={showRaw} className="text-xs font-medium text-slate-600 underline underline-offset-2 hover:text-slate-900">
          {showRaw ? 'Ẩn thông tin kỹ thuật' : 'Xem thông tin kỹ thuật'}
        </button>
        {showRaw && <div className="mt-3 space-y-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          <p><b>Mã sự kiện:</b> <code className="break-all">{item.id}</code></p>
          <p><b>Mã tài khoản thao tác:</b> <code className="break-all">{item.user_id || 'Không có'}</code></p>
          <p><b>Mã đối tượng:</b> <code className="break-all">{id || item.resource || 'Không có'}</code></p>
          <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-all rounded border bg-white p-3">{JSON.stringify(details, null, 2)}</pre>
        </div>}
      </div>
    </div>
  );
}

function Info({ label, value, secondary }) {
  return <div className="min-w-0"><div className="text-xs text-slate-500">{label}</div><div className="break-words font-medium text-slate-800">{value || '—'}</div>{secondary && <div className="break-all text-xs text-slate-500">{secondary}</div>}</div>;
}

export default function AuditLogsPage() {
  const [form, setForm] = useState(FILTERS_INITIAL);
  const [filters, setFilters] = useState(FILTERS_INITIAL);
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(null);
  const [advanced, setAdvanced] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const fetchLogs = async () => {
      setLoading(true);
      setError('');
      try {
        const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
        const { data: result } = await axiosClient.get('/admin/audit-logs', {
          params: { ...params, from_time: isoLocal(filters.from_time), to_time: isoLocal(filters.to_time), skip: page * PAGE_SIZE, limit: PAGE_SIZE },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setData(result);
      } catch (err) {
        if (!controller.signal.aborted) setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Không thể tải nhật ký.');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    fetchLogs();
    return () => controller.abort();
  }, [filters, page, reload]);

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const items = useMemo(() => data.items || [], [data.items]);
  const change = useCallback((key, value) => setForm((prev) => ({ ...prev, [key]: value })), []);
  const apply = (event) => {
    event.preventDefault();
    if (form.from_time && form.to_time && new Date(form.from_time) > new Date(form.to_time)) {
      setError('Thời gian bắt đầu phải trước thời gian kết thúc.');
      return;
    }
    setExpanded(null);
    setPage(0);
    setFilters({ ...form });
  };
  const reset = () => {
    setForm({ ...FILTERS_INITIAL });
    setFilters({ ...FILTERS_INITIAL });
    setPage(0);
    setExpanded(null);
    setError('');
  };

  return <section className="space-y-4" aria-label="Nhật ký thao tác">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Nhật ký thao tác</h1>
        {/* <p className="mt-1 text-sm text-slate-500">Theo dõi ai đã làm gì và tác động đến dữ liệu nào.</p> */}
      </div>
      <button type="button" onClick={() => setReload((prev) => prev + 1)} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Làm mới</button>
    </div>

    <form onSubmit={apply} className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="min-w-[220px] flex-[2] text-xs font-medium text-slate-600">Tìm kiếm
          <input type="search" value={form.q} maxLength={100} onChange={(e) => change('q', e.target.value)} placeholder="Tên quán, tên người, email, mã đối tượng..." className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-900" />
        </label>
        <label className="min-w-[180px] flex-1 text-xs font-medium text-slate-600">Hành động
          <select value={form.action} onChange={(e) => change('action', e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-900">
            <option value="">Tất cả hành động</option>
            {ACTIONS.map(([action, label]) => <option key={action} value={action}>{label}</option>)}
          </select>
        </label>
        <button type="submit" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">Tìm kiếm</button>
        <button type="button" onClick={() => setAdvanced((v) => !v)} aria-expanded={advanced} className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">{advanced ? 'Ẩn bộ lọc' : 'Bộ lọc thêm'}</button>
        <button type="button" onClick={reset} className="px-2 py-2 text-sm text-slate-500 hover:text-slate-900">Đặt lại</button>
      </div>
      {advanced && <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs font-medium text-slate-600">Từ ngày
          <input type="datetime-local" value={form.from_time} onChange={(e) => change('from_time', e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" />
        </label>
        <label className="text-xs font-medium text-slate-600">Đến ngày
          <input type="datetime-local" value={form.to_time} onChange={(e) => change('to_time', e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" />
        </label>
        <label className="text-xs font-medium text-slate-600">ID người thực hiện
          <input value={form.user_id} maxLength={64} onChange={(e) => change('user_id', e.target.value)} placeholder="Mã tài khoản" className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" />
        </label>
        <label className="text-xs font-medium text-slate-600">ID đối tượng
          <input value={form.resource} maxLength={200} onChange={(e) => change('resource', e.target.value)} placeholder="user:... / poi:..." className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" />
        </label>
      </div>}
    </form>

    {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-sm text-slate-500">
        <span>{loading ? 'Đang tải nhật ký...' : `${data.total} sự kiện`}</span>
        <span>Trang {page + 1} / {totalPages}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
            <tr>
              <th className="px-4 py-3">Thời gian (GMT+7)</th>
              <th className="px-4 py-3">Người thực hiện</th>
              <th className="px-4 py-3">Hành động</th>
              <th className="px-4 py-3">Đối tượng</th>
              <th className="px-4 py-3">Trạng thái</th>
              <th className="px-4 py-3 text-right">Chi tiết</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const date = dateTime(item.created_at);
              const type = resourceParts(item.resource).type;
              const isOpen = expanded === item.id;
              return <React.Fragment key={item.id}>
                <tr className="border-t border-slate-100 align-top hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-3"><div className="font-medium text-slate-800">{date.time}</div><div className="text-xs text-slate-500">{date.day}</div></td>
                  <td className="px-4 py-3"><div className="font-medium text-slate-800">{item.actor_name || (item.actor_role && ROLE_LABELS[item.actor_role]) || item.actor_email || (item.user_id ? 'Tài khoản quản trị' : 'Hệ thống / chưa xác định')}</div><div className="max-w-[200px] truncate text-xs text-slate-500" title={item.actor_email || ''}>{item.actor_name ? item.actor_email : (item.actor_role && item.actor_email ? item.actor_email : '')}</div></td>
                  <td className="px-4 py-3"><div className="font-medium text-slate-800">{actionLabel(item.action)}</div></td>
                  <td className="max-w-[230px] px-4 py-3"><div className="font-medium text-slate-800">{targetLabel(item)}</div><div className="truncate text-xs text-slate-500" title={item.target_email || item.resource || ''}>{item.target_email || (TARGET_TYPES[type] || item.resource || '—')}</div></td>
                  <td className="whitespace-nowrap px-4 py-3"><EventStatus action={item.action} /></td>
                  <td className="whitespace-nowrap px-4 py-3 text-right"><button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100" aria-expanded={isOpen} onClick={() => setExpanded(isOpen ? null : item.id)}>{isOpen ? 'Thu gọn' : 'Xem chi tiết'}</button></td>
                </tr>
                {isOpen && <tr className="border-t border-slate-100 bg-slate-50"><td colSpan={6} className="p-3 sm:p-4"><Details item={item} /></td></tr>}
              </React.Fragment>;
            })}
            {!loading && items.length === 0 && <tr><td colSpan={6} className="px-4 py-12 text-center text-sm text-slate-500">Không có nhật ký phù hợp với bộ lọc.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
    <div className="flex items-center justify-end gap-3 text-sm">
      <button type="button" disabled={loading || page === 0} onClick={() => { setPage((p) => Math.max(0, p - 1)); setExpanded(null); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 disabled:opacity-40">Trang trước</button>
      <span className="text-slate-600">{page + 1} / {totalPages}</span>
      <button type="button" disabled={loading || page + 1 >= totalPages} onClick={() => { setPage((p) => p + 1); setExpanded(null); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 disabled:opacity-40">Trang sau</button>
    </div>
  </section>;
}
