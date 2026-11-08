import React, { useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../utils/assetUrl.js';

const input = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm';
const primary = 'rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white hover:bg-green-800 disabled:opacity-50';

export default function RegistrationPOIAssignment({ registration, canLink, canCreate, busy, onApprove }) {
  const [name, setName] = useState(registration.poi_name || '');
  const [address, setAddress] = useState(registration.poi_address || '');
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');
  const [poiId, setPoiId] = useState('');
  const [creating, setCreating] = useState(false);

  function resetResults() {
    setResults(null);
    setPoiId('');
    setCreating(false);
    setError('');
  }

  async function search(event) {
    event.preventDefault();
    resetResults();
    setSearching(true);
    try {
      const { data } = await axiosClient.get('/admin/registrations/' + registration.id + '/poi-candidates', {
        params: { name: name.trim(), address: address.trim() },
      });
      setResults(data);
    } catch (err) {
      setError(apiErrorMessage(err, 'Không tìm được quán trong POI Master'));
    } finally {
      setSearching(false);
    }
  }

  function createDraft(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const longitude = Number(fields.get('longitude'));
    const latitude = Number(fields.get('latitude'));
    if (!fields.get('longitude') || !fields.get('latitude') || !Number.isFinite(longitude) || !Number.isFinite(latitude)) {
      setError('Nhập kinh độ và vĩ độ của quán.');
      return;
    }
    onApprove({ draft: {
      ward: fields.get('ward').trim(),
      original_description: fields.get('description').trim(),
      location: { type: 'Point', coordinates: [longitude, latitude] },
    } });
  }

  const recovering = registration.status === 'approved';

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3" aria-label="Tìm và gắn quán">
      <h4 className="text-sm font-semibold">{recovering ? 'Bổ sung quán cho hồ sơ đã duyệt' : 'Tìm quán trước khi phê duyệt'}</h4>
      <p className="text-sm text-slate-600">Đối chiếu tên và địa chỉ với POI Master. Nếu tên quán được ghi khác, thử tìm chỉ theo địa chỉ hoặc một phần tên.</p>
      <form onSubmit={search} className="space-y-2">
        <fieldset disabled={busy || searching} className="grid gap-2 sm:grid-cols-2">
          <label className="text-sm">Tên quán
            <input type="search" className={input} maxLength={180} value={name} onChange={(event) => { setName(event.target.value); resetResults(); }} />
          </label>
          <label className="text-sm">Địa chỉ
            <input type="search" className={input} maxLength={400} value={address} onChange={(event) => { setAddress(event.target.value); resetResults(); }} />
          </label>
        </fieldset>
        <button type="submit" disabled={busy || searching || (!name.trim() && !address.trim())} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50">
          {searching ? 'Đang tìm…' : 'Tìm trong POI Master'}
        </button>
      </form>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      {results && (
        <>
          {results.items.length ? (
            <fieldset disabled={busy || !canLink} className="space-y-2">
              <legend className="mb-2 text-sm font-semibold">Quán có thể trùng</legend>
              {results.items.map((poi) => (
                <label key={poi.id} className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-2 text-sm">
                  <input type="radio" name="registration-poi" className="mt-1" checked={poiId === poi.id} disabled={!poi.can_link}
                    onChange={() => { setPoiId(poi.id); setCreating(false); }} />
                  <span className="min-w-0 break-words">
                    <strong>{poi.name}</strong><span className="block text-slate-600">{poi.address || 'Chưa có địa chỉ'}</span>
                    <span className="text-xs text-slate-500">{poi.is_active ? 'Đang công khai' : 'Đang ẩn'}{!poi.can_link && ' · Đã có chủ quán khác'}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          ) : <p role="status" className="text-sm text-slate-600">Không tìm thấy quán theo tiêu chí này.</p>}
          {results.has_more && <p className="text-sm text-slate-600">Có thêm kết quả. Hãy tìm với tên hoặc địa chỉ cụ thể hơn trước khi tạo nháp.</p>}
          {poiId && <button type="button" disabled={busy} className={primary} onClick={() => onApprove({ poi_id: poiId })}>
            {busy ? 'Đang xử lý…' : recovering ? 'Gắn quán đã chọn' : 'Phê duyệt và gắn quán'}
          </button>}
          {results.has_exact_match && !poiId && (
            <p className="text-sm text-slate-600">Đã có quán trùng tên và địa chỉ của hồ sơ. Hãy chọn quán có sẵn để gắn.</p>
          )}
          {canCreate && !poiId && !results.has_more && !results.has_exact_match && (
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" disabled={busy} checked={creating} onChange={(event) => setCreating(event.target.checked)} />
              Đã đối chiếu kết quả và xác nhận quán chưa có trong POI Master
            </label>
          )}
          {creating && (
            <form onSubmit={createDraft} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
              <h5 className="text-sm font-semibold">Tạo quán nháp</h5>
              <p className="break-words text-sm text-slate-600">{registration.poi_name} · {registration.poi_address}. Quán sẽ được tạo ở trạng thái ẩn.</p>
              <fieldset disabled={busy} className="grid gap-2 sm:grid-cols-2">
                <label className="text-sm sm:col-span-2">Phường<input className={input} name="ward" required maxLength={80} /></label>
                <label className="text-sm">Kinh độ<input className={input} name="longitude" type="number" required min="-180" max="180" step="any" /></label>
                <label className="text-sm">Vĩ độ<input className={input} name="latitude" type="number" required min="-90" max="90" step="any" /></label>
                <label className="text-sm sm:col-span-2">Mô tả tiếng Việt<textarea className={input} name="description" required rows={3} maxLength={8000} /></label>
              </fieldset>
              <button type="submit" disabled={busy} className={primary}>
                {busy ? 'Đang xử lý…' : recovering ? 'Tạo nháp và gắn quán' : 'Phê duyệt và tạo quán nháp'}
              </button>
            </form>
          )}
        </>
      )}
    </section>
  );
}
