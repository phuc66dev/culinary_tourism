import React, { useEffect, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { hasPermission } from '../hooks/useAdminSession.js';
import { apiErrorMessage } from '../utils/assetUrl.js';

export default function RoleManagementPage() {
  const current = useAuthStore((s) => s.user);
  const [items, setItems] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [priority, setPriority] = useState(5);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const canCreate = hasPermission(current, 'role:create');
  const canUpdate = hasPermission(current, 'role:update');
  const canDelete = hasPermission(current, 'role:delete');
  async function load() {
    try {
      const { data } = await axiosClient.get('/admin/roles');
      setItems(data.items); setCatalog(data.permission_catalog);
    } catch (err) { setError(apiErrorMessage(err, 'Không thể tải danh sách vai trò')); }
  }
  useEffect(() => { load(); }, []);
  const groups = catalog.reduce((out, perm) => {
    const domain = perm.split(':')[0]; (out[domain] ||= []).push(perm); return out;
  }, {});
  const editing = selected?.name && selected.name !== 'super_admin';
  const disabled = busy || (!selected?.isNew && !canUpdate) || selected?.name === 'super_admin';
  async function submit(e) {
    e.preventDefault(); setError(''); setNotice(''); setBusy(true);
    try {
      if (selected.isNew) await axiosClient.post('/admin/roles', { name, permissions: selected.permissions, priority: Number(priority) });
      else await axiosClient.patch(`/admin/roles/${selected.name}`, { permissions: selected.permissions, priority: Number(priority) });
      setNotice('Đã lưu vai trò, quyền có hiệu lực trên request tiếp theo.'); setSelected(null); await load();
    } catch (err) { setError(apiErrorMessage(err, 'Không thể lưu vai trò')); }
    finally { setBusy(false); }
  }
  function edit(role) { setSelected({ ...role, permissions: [...role.permissions] }); setName(role.name); setPriority(role.priority); }
  function toggle(perm) { setSelected((prev) => ({ ...prev, permissions: prev.permissions.includes(perm) ? prev.permissions.filter((p) => p !== perm) : [...prev.permissions, perm] })); }
  async function remove(role) {
    if (!window.confirm(`Xóa vai trò ${role.name}? Chỉ xóa được khi không có tài khoản đang dùng.`)) return;
    setBusy(true); setError('');
    try { await axiosClient.delete(`/admin/roles/${role.name}`); setSelected(null); setNotice('Đã xóa vai trò.'); await load(); }
    catch (err) { setError(apiErrorMessage(err, 'Không thể xóa vai trò')); }
    finally { setBusy(false); }
  }
  return <section className="space-y-4">
    <div><h1 className="text-xl font-bold">Vai trò & Phân quyền (Dynamic RBAC)</h1><p className="text-sm text-slate-600">Quyền super_admin luôn cố định.</p></div>
    {error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>}
    {notice && <div role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{notice}</div>}
    <div className="flex flex-wrap gap-3">
      {canCreate && <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white" onClick={() => { setSelected({ isNew: true, name: '', permissions: [] }); setName(''); setPriority(5); }}>+ Tạo vai trò</button>}
      {items.map((role) => <button key={role.name} className={`rounded-lg border px-4 py-2 text-sm ${selected?.name === role.name ? 'border-slate-900 bg-slate-200' : 'bg-white'}`} onClick={() => edit(role)}>{role.name} ({role.permissions.length})</button>)}
    </div>
    {selected && <form className="space-y-4 rounded-xl border bg-white p-4" onSubmit={submit}>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block text-sm">Tên vai trò
          <input disabled={!selected.isNew} value={name} required pattern="[a-z][a-z0-9_]{2,49}" onChange={(e) => setName(e.target.value)} className="mt-1 w-full rounded border px-3 py-2 disabled:bg-slate-100" />
        </label>
        <label className="block text-sm">Mức ưu tiên
          <input type="number" min={1} max={99} disabled={disabled} value={priority} onChange={(e) => setPriority(e.target.value)} className="mt-1 w-full rounded border px-3 py-2 disabled:bg-slate-100" />
        </label>
      </div>
      {selected.name === 'super_admin' && <p className="rounded bg-amber-50 p-3 text-sm text-amber-900">Vai trò super_admin được bảo vệ; chỉ đọc.</p>}
      <div className="grid gap-3 md:grid-cols-3">
        {Object.entries(groups).map(([domain, permissions]) => <fieldset key={domain} className="rounded-lg border p-3"><legend className="px-1 font-medium uppercase">{domain}</legend>
          {permissions.map((perm) => <label key={perm} className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" disabled={disabled} checked={selected.permissions.includes(perm)} onChange={() => toggle(perm)} /> {perm}</label>)}
        </fieldset>)}
      </div>
      <div className="flex flex-wrap gap-2">
        <button disabled={disabled || (selected.isNew && !canCreate)} className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50">{selected.isNew ? 'Tạo vai trò' : 'Lưu quyền'}</button>
        <button type="button" onClick={() => setSelected(null)} className="rounded border px-4 py-2 text-sm">Đóng</button>
        {editing && !selected.is_system && canDelete && <button type="button" disabled={busy} onClick={() => remove(selected)} className="rounded border border-red-400 px-4 py-2 text-sm text-red-700">Xóa vai trò</button>}
      </div>
    </form>}
  </section>;
}
