import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { apiErrorMessage } from '../utils/assetUrl.js';

export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();
  async function submit(e) {
    e.preventDefault(); setError('');
    if (newPassword !== confirm) return setError('Mật khẩu xác nhận không khớp.');
    if (newPassword.length < 12) return setError('Mật khẩu mới phải có tối thiểu 12 ký tự.');
    setBusy(true);
    try {
      await axiosClient.post('/admin/auth/change-password', { current_password: currentPassword, new_password: newPassword });
      clearAuth(); setMessage('Đã đổi mật khẩu, toàn bộ phiên đăng nhập cũ bị thu hồi. Hãy đăng nhập lại.');
      setCurrentPassword(''); setNewPassword(''); setConfirm('');
    } catch (err) { setError(apiErrorMessage(err, 'Đổi mật khẩu không thành công')); }
    finally { setBusy(false); }
  }
  return (
    <section className="mx-auto max-w-lg rounded-xl border bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold">Đổi mật khẩu</h1>
      <p className="mt-2 text-sm text-slate-600">Mật khẩu mới cần tối thiểu 12 ký tự. Sau khi lưu bạn sẽ phải đăng nhập lại.</p>
      {error && <div role="alert" className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {message ? <div role="status" className="mt-3 rounded border border-green-200 bg-green-50 p-3 text-sm">{message}<button className="ml-2 underline" onClick={() => navigate('/admin/login', { replace: true })}>Đăng nhập</button></div> :
        <form onSubmit={submit} className="mt-4 space-y-4">
          {[["Mật khẩu hiện tại", currentPassword, setCurrentPassword, 'current-password'],
            ["Mật khẩu mới", newPassword, setNewPassword, 'new-password'],
            ["Nhập lại mật khẩu mới", confirm, setConfirm, 'new-password']].map(([label, value, setter, autoComplete]) =>
            <label key={label} className="block text-sm font-medium">{label}
              <input type="password" value={value} onChange={(e) => setter(e.target.value)} autoComplete={autoComplete} required maxLength={72}
                className="mt-1 w-full rounded-lg border px-3 py-2" />
            </label>)}
          <button disabled={busy} className="rounded-lg bg-slate-900 px-5 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? 'Đang lưu…' : 'Đổi mật khẩu'}</button>
        </form>}
    </section>
  );
}
