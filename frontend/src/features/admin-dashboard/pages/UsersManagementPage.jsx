import React, { useCallback, useEffect, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { apiErrorMessage } from '../utils/assetUrl.js';
import { hasPermission } from '../hooks/useAdminSession.js';

const blank = { email: '', full_name: '', password: '', role: 'admin', is_active: true };

export default function UsersManagementPage() {
  const user = useAuthStore((s) => s.user);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [roles, setRoles] = useState([]);
  const [search, setSearch] = useState('');
  const [filterRole, setFilterRole] = useState('');
  const [page, setPage] = useState(0);
  const [create, setCreate] = useState(null);
  const [editing, setEditing] = useState(null);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const limit = 20;
  const canCreate = hasPermission(user, 'user:create');
  const canEdit = hasPermission(user, 'user:update');
  const canDelete = hasPermission(user, 'user:delete');

  const load = useCallback(async () => {
    try {
      const { data } = await axiosClient.get('/admin/users', { params: { q: search || undefined, role: filterRole || undefined, limit, skip: page * limit } });
      setItems(data.items); setTotal(data.total);
    } catch (err) { setError(apiErrorMessage(err, 'Không thể tải tài khoản')); }
  }, [search, filterRole, page]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    axiosClient.get('/admin/roles').then(({ data }) => setRoles(data.items || [])).catch(() => {
      // users may have user:read without role:read; use known roles only for display
      setRoles([{ name: 'admin' }, { name: 'poi_owner' }, { name: 'user' }]);
    });
  }, []);
  const run = async (action, doneMessage) => {
    setBusy(true); setError(''); setNotice('');
    try { await action(); setNotice(doneMessage); setCreate(null); setEditing(null); setPassword(''); await load(); }
    catch (err) { setError(apiErrorMessage(err, 'Thao tác không thành công')); }
    finally { setBusy(false); }
  };
  const options = roles.filter((r) => r.name !== 'super_admin');
  const textInput = 'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm';

  return <section className="space-y-4">
    <div><h1 className="text-xl font-bold">Quản lý tài khoản</h1><p className="text-sm text-slate-600">Chỉ hiển thị thông tin quản trị, không trả mật khẩu hoặc CCCD.</p></div>
    {error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>}
    {notice && <div role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{notice}</div>}
    <div className="flex flex-wrap gap-3">
      <input aria-label="Tìm tài khoản" className={textInput + ' max-w-sm'} value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} placeholder="Tìm email hoặc họ tên" />
      <select aria-label="Lọc vai trò" className={textInput + ' max-w-xs'} value={filterRole} onChange={(e) => { setFilterRole(e.target.value); setPage(0); }}>
        <option value="">Tất cả vai trò</option>{roles.map((r) => <option key={r.name} value={r.name}>{r.name}</option>)}
      </select>
      {canCreate && <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white" onClick={() => { setCreate({ ...blank }); setEditing(null); }}>+ Tạo tài khoản</button>}
    </div>
    {create && <form className="space-y-3 rounded-xl border bg-white p-4" onSubmit={(e) => { e.preventDefault(); run(() => axiosClient.post('/admin/users', create), 'Đã tạo tài khoản. Người dùng phải đổi mật khẩu khi đăng nhập lần đầu.'); }}>
      <h2 className="font-semibold">Tạo tài khoản mới</h2>
      <div className="grid gap-3 md:grid-cols-2">
        <input className={textInput} aria-label="Email mới" placeholder="Email" type="email" required value={create.email} onChange={(e) => setCreate({ ...create, email: e.target.value })}/>
        <input className={textInput} aria-label="Họ tên mới" placeholder="Họ và tên" required value={create.full_name} onChange={(e) => setCreate({ ...create, full_name: e.target.value })}/>
        <input className={textInput} aria-label="Mật khẩu tạm" type="password" minLength={12} maxLength={72} placeholder="Mật khẩu tạm (≥ 12 ký tự)" required value={create.password} onChange={(e) => setCreate({ ...create, password: e.target.value })}/>
        <select className={textInput} aria-label="Vai trò mới" value={create.role} onChange={(e) => setCreate({ ...create, role: e.target.value })}>{options.map((r) => <option key={r.name}>{r.name}</option>)}</select>
      </div>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={create.is_active} onChange={(e) => setCreate({ ...create, is_active: e.target.checked })}/> Kích hoạt tài khoản</label>
      <div className="flex gap-2"><button disabled={busy} className="rounded bg-slate-900 px-4 py-2 text-sm text-white">Tạo</button><button type="button" onClick={() => setCreate(null)} className="rounded border px-4 py-2 text-sm">Hủy</button></div>
    </form>}
    {editing && <form className="space-y-3 rounded-xl border bg-white p-4" onSubmit={(e) => { e.preventDefault(); run(() => axiosClient.patch(`/admin/users/${editing.id}`, { full_name: editing.full_name, role: editing.role, is_active: editing.is_active }), 'Đã cập nhật tài khoản.'); }}>
      <h2 className="font-semibold">Chỉnh sửa: {editing.email}</h2>
      <div className="grid gap-3 md:grid-cols-2">
        <input className={textInput} aria-label="Họ tên" required value={editing.full_name || ''} onChange={(e) => setEditing({ ...editing, full_name: e.target.value })}/>
        <select className={textInput} aria-label="Vai trò" value={editing.role} onChange={(e) => setEditing({ ...editing, role: e.target.value })}>{options.map((r) => <option key={r.name}>{r.name}</option>)}</select>
      </div>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })}/> Đang hoạt động</label>
      <div className="flex gap-2"><button disabled={busy} className="rounded bg-slate-900 px-4 py-2 text-sm text-white">Lưu</button><button type="button" onClick={() => setEditing(null)} className="rounded border px-4 py-2 text-sm">Hủy</button></div>
      {canEdit && <div className="border-t pt-3"><label className="block text-sm">Đặt mật khẩu tạm (ít nhất 12 ký tự)</label><div className="mt-2 flex gap-2"><input className={textInput} type="password" aria-label="Mật khẩu reset" minLength={12} maxLength={72} value={password} onChange={(e) => setPassword(e.target.value)}/><button type="button" disabled={busy || password.length < 12} className="rounded border px-4 py-2 text-sm disabled:opacity-50" onClick={() => { if (window.confirm('Thu hồi mọi phiên đăng nhập của tài khoản này?')) run(() => axiosClient.post(`/admin/users/${editing.id}/reset-password`, { password }), 'Đã đặt lại mật khẩu và thu hồi phiên.'); }}>Reset</button></div></div>}
    </form>}
    <div className="overflow-x-auto rounded-xl border bg-white"><table className="min-w-full text-left text-sm"><thead className="bg-slate-100"><tr>{['Email', 'Họ tên', 'Vai trò', 'Trạng thái', 'Thao tác'].map((h) => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead><tbody>
      {items.map((item) => <tr key={item.id} className="border-t"><td className="px-3 py-3">{item.email}</td><td className="px-3 py-3">{item.full_name}</td><td className="px-3 py-3">{item.role}</td><td className="px-3 py-3">{item.is_active ? 'Hoạt động' : 'Đã khóa'}</td><td className="space-x-2 whitespace-nowrap px-3 py-3">
        {canEdit && item.role !== 'super_admin' && item.id !== user.id && <button onClick={() => { setEditing({ ...item }); setCreate(null); }} className="text-blue-700 underline">Sửa</button>}
        {canDelete && item.role !== 'super_admin' && item.id !== user.id && <button className="text-red-700 underline" onClick={() => { if (window.confirm(`Vô hiệu hóa tài khoản ${item.email}?`)) run(() => axiosClient.delete(`/admin/users/${item.id}`), 'Đã vô hiệu hóa tài khoản.'); }}>Xóa</button>}
      </td></tr>)}
      {items.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-500">Không có tài khoản phù hợp.</td></tr>}
    </tbody></table></div>
    <div className="flex items-center gap-3 text-sm"><span>Tổng: {total}</span><button className="rounded border px-3 py-1 disabled:opacity-40" disabled={page === 0} onClick={() => setPage(page - 1)}>Trước</button><span>Trang {page + 1}</span><button className="rounded border px-3 py-1 disabled:opacity-40" disabled={(page + 1) * limit >= total} onClick={() => setPage(page + 1)}>Sau</button></div>
  </section>;
}
