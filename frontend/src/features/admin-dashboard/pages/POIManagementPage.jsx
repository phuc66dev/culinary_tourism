import React, { useCallback, useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import axiosClient from '../../../api/axiosClient.js';
import { useAuthStore } from '../../../store/authStore.js';
import { hasPermission } from '../hooks/useAdminSession.js';
import { apiErrorMessage } from '../utils/assetUrl.js';
import AudioPreviewPanel from '../components/AudioPreviewPanel.jsx';

const DEFAULT_COORDS = [106.7028, 10.7582];
const INPUT = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-teal-600 focus:outline-none';
const ACTION = 'rounded-lg px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40';
const emptyForm = () => ({
  name: '', category: 'street_food', address: '', ward: 'Phường 8', original_description: '',
  longitude: String(DEFAULT_COORDS[0]), latitude: String(DEFAULT_COORDS[1]),
  trigger_radius: '30', audio_priority: '5', images: '',
});

function SatellitePicker({ coords, onChange }) {
  const mount = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const callback = useRef(onChange);
  callback.current = onChange;
  const [mapError, setMapError] = useState('');

  useEffect(() => {
    if (!mount.current) return undefined;
    let map;
    try {
      map = new maplibregl.Map({
        container: mount.current,
        center: coords, zoom: 16,
        style: {
          version: 8,
          sources: { satellite: {
            type: 'raster', tileSize: 256,
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
            attribution: 'Imagery © Esri, Maxar, Earthstar Geographics and GIS User Community',
          } },
          layers: [{ id: 'satellite', type: 'raster', source: 'satellite' }],
        },
      });
      mapRef.current = map;
      const marker = new maplibregl.Marker({ color: '#e11d48', draggable: true }).setLngLat(coords).addTo(map);
      markerRef.current = marker;
      const pick = (point) => callback.current([Number(point.lng.toFixed(7)), Number(point.lat.toFixed(7))]);
      map.on('click', (event) => pick(event.lngLat));
      marker.on('dragend', () => pick(marker.getLngLat()));
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
      map.on('error', () => setMapError('Không tải được lớp ảnh vệ tinh. Vẫn có thể nhập tọa độ thủ công.'));
    } catch (error) { setMapError('Trình duyệt không hỗ trợ bản đồ vệ tinh. Hãy nhập tọa độ thủ công.'); }
    return () => { mapRef.current = null; markerRef.current = null; map?.remove(); };
    // mounted once; marker position is synchronized separately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!coords.every(Number.isFinite)) return;
    markerRef.current?.setLngLat(coords);
  }, [coords[0], coords[1]]);
  return (
    <div>
      <div ref={mount} className="h-64 w-full overflow-hidden rounded-lg border bg-slate-200" aria-label="Bản đồ vệ tinh chọn tọa độ POI" />
      <p className="mt-1 text-xs text-slate-500">Bấm lên ảnh vệ tinh hoặc kéo ghim đỏ để chọn chính xác kinh độ, vĩ độ. Dữ liệu nền: Esri World Imagery (cần mạng).</p>
      {mapError && <p role="alert" className="mt-1 text-xs text-amber-700">{mapError}</p>}
    </div>
  );
}

function POIForm({ poi, saving, error, onSave, onClose }) {
  const [form, setForm] = useState(() => poi ? {
    name: poi.name || '', category: poi.category || 'street_food', address: poi.address || '',
    ward: poi.ward || '', original_description: poi.original_description || '',
    longitude: String(poi.location?.coordinates?.[0] ?? DEFAULT_COORDS[0]),
    latitude: String(poi.location?.coordinates?.[1] ?? DEFAULT_COORDS[1]),
    trigger_radius: String(poi.trigger_radius ?? 30), audio_priority: String(poi.audio_priority ?? 5),
    images: (poi.images || []).join('\n'),
  } : emptyForm());
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const coords = [Number(form.longitude), Number(form.latitude)];

  function submit(event) {
    event.preventDefault();
    if (!coords.every(Number.isFinite) || !(-180 <= coords[0] && coords[0] <= 180 && -90 <= coords[1] && coords[1] <= 90)) return;
    onSave({ name: form.name.trim(), address: form.address.trim(), ward: form.ward.trim(),
      category: form.category.trim(), original_description: form.original_description.trim(),
      location: { type: 'Point', coordinates: coords },
      trigger_radius: Number(form.trigger_radius), audio_priority: Number(form.audio_priority),
      images: form.images.split('\n').map((v) => v.trim()).filter(Boolean),
      ...(poi ? { expected_revision: poi.revision } : {}),
    });
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3" role="dialog" aria-modal="true" aria-labelledby="poi-form-title">
      <form onSubmit={submit} className="max-h-[94vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 id="poi-form-title" className="text-lg font-bold">{poi ? `Sửa ${poi.name}` : 'Thêm quán ăn mới'}</h3>
          <button type="button" onClick={onClose} className="text-sm underline">Đóng</button>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <label className="block text-sm">Tên quán *<input required maxLength={180} className={INPUT} value={form.name} onChange={(e) => set('name', e.target.value)} /></label>
            <label className="block text-sm">Địa chỉ tại Quận 4 *<input required maxLength={400} className={INPUT} value={form.address} onChange={(e) => set('address', e.target.value)} /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">Phường *<input required maxLength={80} className={INPUT} value={form.ward} onChange={(e) => set('ward', e.target.value)} /></label>
              <label className="text-sm">Loại món ăn *<input required className={INPUT} value={form.category} onChange={(e) => set('category', e.target.value)} /></label>
            </div>
            <label className="block text-sm">Mô tả gốc (tiếng Việt) *<textarea required maxLength={8000} rows={4} className={INPUT} value={form.original_description} onChange={(e) => set('original_description', e.target.value)} /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">Bán kính kích hoạt (m)<input required type="number" min="5" max="500" className={INPUT} value={form.trigger_radius} onChange={(e) => set('trigger_radius', e.target.value)} /></label>
              <label className="text-sm">Ưu tiên audio<input required type="number" min="1" max="10" className={INPUT} value={form.audio_priority} onChange={(e) => set('audio_priority', e.target.value)} /></label>
            </div>
            <label className="block text-sm">URL ảnh quán (mỗi dòng một URL)<textarea rows={3} className={INPUT} value={form.images} onChange={(e) => set('images', e.target.value)} /></label>
          </div>
          <div className="space-y-3">
            <SatellitePicker coords={coords.every(Number.isFinite) ? coords : DEFAULT_COORDS}
              onChange={([lng, lat]) => setForm((f) => ({ ...f, longitude: String(lng), latitude: String(lat) }))} />
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">Kinh độ (longitude)<input required type="number" step="any" min="-180" max="180" className={INPUT} value={form.longitude} onChange={(e) => set('longitude', e.target.value)} /></label>
              <label className="text-sm">Vĩ độ (latitude)<input required type="number" step="any" min="-90" max="90" className={INPUT} value={form.latitude} onChange={(e) => set('latitude', e.target.value)} /></label>
            </div>
            <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">POI mới luôn ở trạng thái <strong>Ẩn</strong>. Chỉ được bật công khai sau khi có bản dịch và audio tiếng Anh hoàn chỉnh.</div>
          </div>
        </div>
        {error && <p role="alert" className="mt-3 rounded bg-red-50 p-2 text-sm text-red-800">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={onClose} className={`${ACTION} bg-slate-100`}>Hủy</button>
          <button type="submit" disabled={saving} className={`${ACTION} bg-teal-700 text-white`}>{saving ? 'Đang lưu…' : poi ? 'Lưu thay đổi' : 'Thêm POI'}</button>
        </div>
      </form>
    </div>
  );
}

function EnglishForm({ poi, onClose, onSaved }) {
  const [title, setTitle] = useState(poi.activation?.en?.title || '');
  const [description, setDescription] = useState(poi.activation?.en?.description || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  async function save(event) {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await axiosClient.put(`/admin/pois/${poi.id}/localizations/en`, {
        title: title.trim(), description: description.trim(), expected_revision: poi.revision,
      });
      onSaved();
    } catch (e) { setError(apiErrorMessage(e, 'Không lưu được bản dịch')); }
    finally { setSaving(false); }
  }
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" role="dialog" aria-modal="true" aria-labelledby="en-title">
    <form onSubmit={save} className="w-full max-w-xl space-y-3 rounded-xl bg-white p-5 shadow-xl">
      <h3 id="en-title" className="text-lg font-bold">Bản dịch tiếng Anh · {poi.name}</h3>
      <p className="text-sm text-slate-600">Mọi chỉnh sửa nội dung EN đều đặt audio về trạng thái chờ sinh lại. Phải tắt công khai trước khi sửa bản dịch.</p>
      <label className="block text-sm">Tên quán tiếng Anh *<input required maxLength={180} value={title} onChange={(e) => setTitle(e.target.value)} className={INPUT} /></label>
      <label className="block text-sm">Mô tả tiếng Anh *<textarea required rows={6} maxLength={8000} value={description} onChange={(e) => setDescription(e.target.value)} className={INPUT} /></label>
      {error && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-800">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onClose} className={`${ACTION} bg-slate-100`}>Hủy</button>
        <button disabled={saving} type="submit" className={`${ACTION} bg-teal-700 text-white`}>{saving ? 'Đang lưu…' : 'Lưu nội dung EN'}</button>
      </div>
    </form>
  </div>;
}

export default function POIManagementPage() {
  const user = useAuthStore((s) => s.user);
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [ward, setWard] = useState('');
  const [active, setActive] = useState('');
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0, wards: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [englishPOI, setEnglishPOI] = useState(null);
  const [previewPoiId, setPreviewPoiId] = useState(null);
  const [editing, setEditing] = useState(undefined); // undefined = no form; null = create form
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const limit = 25;
  const reload = () => setRefresh((n) => n + 1);

  useEffect(() => { const t = setTimeout(() => setDebounced(search.trim()), 300); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(0); }, [debounced, ward, active]);
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const { data: res } = await axiosClient.get('/admin/pois', { params: {
        q: debounced || undefined, ward: ward || undefined, is_active: active === '' ? undefined : active === 'true',
        limit, skip: page * limit,
      } });
      setData((prev) => ({ ...res, wards: res.wards?.length ? res.wards : prev.wards }));
    } catch (e) { setError(apiErrorMessage(e, 'Không tải được POI')); }
    finally { setLoading(false); }
  }, [debounced, ward, active, page, refresh]);
  useEffect(() => { load(); }, [load]);
  // TTS runs asynchronously: revisit Activation Gate while Admin keeps this page open.
  // This refresh does not generate any audio; it merely re-reads server-side readiness.
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') setRefresh((n) => n + 1);
    }, 12000);
    return () => window.clearInterval(timer);
  }, []);

  async function save(payload) {
    setSaving(true); setFormError('');
    try {
      if (editing) await axiosClient.patch(`/admin/pois/${editing.id}`, payload);
      else await axiosClient.post('/admin/pois', payload);
      setEditing(undefined); setMessage(editing ? 'Đã cập nhật POI' : 'Đã thêm POI (đang ẩn)'); reload();
    } catch (e) { setFormError(apiErrorMessage(e, 'Không lưu được POI')); }
    finally { setSaving(false); }
  }
  async function changeActive(poi) {
    if (!hasPermission(user, 'poi:toggle') || !hasPermission(user, 'poi:update')) return;
    const next = !poi.is_active;
    if (next && !poi.activation?.ready) return;
    if (!window.confirm(`${next ? 'Công khai' : 'Ẩn'} quán "${poi.name}"?`)) return;
    setBusyId(poi.id); setError('');
    try {
      await axiosClient.patch(`/admin/pois/${poi.id}`, { is_active: next, expected_revision: poi.revision });
      setMessage(`${poi.name}: ${next ? 'Đã công khai' : 'Đã ẩn'}`); reload();
    } catch (e) { setError(apiErrorMessage(e, 'Không đổi được trạng thái')); }
    finally { setBusyId(null); }
  }
  async function deletePOI(poi) {
    if (!window.confirm(`XÓA VĨNH VIỄN "${poi.name}" cùng bản dịch và menu? Không thể hoàn tác.`)) return;
    setBusyId(poi.id); setError('');
    try { await axiosClient.delete(`/admin/pois/${poi.id}`); setMessage(`Đã xóa ${poi.name}`); reload(); }
    catch (e) { setError(apiErrorMessage(e, 'Không thể xóa quán')); }
    finally { setBusyId(null); }
  }
  async function enqueueAudio(poi) {
    setBusyId(poi.id); setError('');
    try {
      await axiosClient.post('/admin/audio-tasks', { poi_id: poi.id, languages: ['en'] });
      setMessage(`Đã đưa ${poi.name} vào hàng đợi sinh âm thanh tiếng Anh.`); reload();
    } catch (e) { setError(apiErrorMessage(e, 'Không thể tạo tác vụ audio')); }
    finally { setBusyId(null); }
  }
  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-white p-4">
        <div><h2 className="text-xl font-bold">POI Master</h2><p className="text-sm text-slate-500">{data.total} quán phù hợp bộ lọc</p></div>
        <div className="flex gap-2">
          <button type="button" onClick={reload} disabled={loading} className={`${ACTION} border border-slate-300 bg-white text-slate-700`}>Làm mới</button>
          {hasPermission(user, 'poi:create') && <button onClick={() => { setEditing(null); setFormError(''); }} className={`${ACTION} bg-teal-700 text-white`}>+ Thêm quán</button>}
        </div>
      </header>
      <div className="grid gap-3 rounded-xl border bg-white p-4 sm:grid-cols-3">
        <label className="text-sm">Tìm tên quán<input type="search" placeholder="Tên quán…" className={INPUT} value={search} onChange={(e) => setSearch(e.target.value)} /></label>
        <label className="text-sm">Lọc phường<select className={INPUT} value={ward} onChange={(e) => setWard(e.target.value)}><option value="">Tất cả phường</option>{data.wards.map((w) => <option key={w} value={w}>{w}</option>)}</select></label>
        <label className="text-sm">Trạng thái<select className={INPUT} value={active} onChange={(e) => setActive(e.target.value)}><option value="">Tất cả</option><option value="true">Đã công khai</option><option value="false">Đang ẩn</option></select></label>
      </div>
      {message && <div role="status" className="rounded-lg border border-green-300 bg-green-50 p-3 text-sm text-green-900">{message}</div>}
      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</div>}
      <div className="overflow-x-auto rounded-xl border bg-white">
        <table className="min-w-[970px] w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-600"><tr><th className="p-3">Quán ăn</th><th className="p-3">Phường</th><th className="p-3">Tọa độ (lng, lat)</th><th className="p-3">Activation Gate</th><th className="p-3">Công khai</th><th className="p-3">Thao tác</th></tr></thead>
          <tbody className="divide-y">
            {data.items.map((poi) => {
              const ready = poi.activation?.ready;
              const pending = busyId === poi.id;
              return (
                <tr key={poi.id}>
                  <td className="p-3 align-top"><strong>{poi.name}</strong><p className="mt-1 max-w-xs text-xs text-slate-500">{poi.address}</p><p className="mt-1 text-xs text-slate-400">Phiên bản POI: {poi.revision}</p></td>
                  <td className="p-3 align-top">{poi.ward || '—'}</td>
                  <td className="p-3 align-top font-mono text-xs">{(poi.location?.coordinates || []).map((v) => Number(v).toFixed(6)).join(', ')}</td>
                  <td className="max-w-xs p-3 align-top">
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${ready ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>{ready ? 'Đạt' : 'Chưa đạt'}</span>
                    {!ready && <ul className="mt-1 space-y-1 text-xs text-amber-800">{poi.activation?.reasons?.map((r) => <li key={r}>• {r}</li>)}</ul>}
                    {poi.activation?.en?.audio_url && poi.activation.en.audio_status === 'completed' && (
                      <button type="button" onClick={() => setPreviewPoiId((id) => id === poi.id ? null : poi.id)}
                        className="mt-2 block text-xs font-medium text-teal-700 underline"
                        aria-expanded={previewPoiId === poi.id}>
                        {previewPoiId === poi.id ? 'Ẩn trình phát EN' : '▶ Nghe audio EN'}
                      </button>
                    )}
                    {previewPoiId === poi.id && <AudioPreviewPanel poiId={poi.id} onlyLang="en" compact />}
                    {hasPermission(user, 'poi:update') && <button onClick={() => setEnglishPOI(poi)} disabled={pending}
                      className="mt-2 block text-xs font-medium text-teal-700 underline disabled:opacity-50">Sửa bản dịch EN</button>}
                    {!ready && hasPermission(user, 'poi:update') && <button onClick={() => enqueueAudio(poi)} disabled={pending} className="mt-2 block text-xs font-medium text-teal-700 underline disabled:opacity-50">Tạo audio EN</button>}
                  </td>
                  <td className="p-3 align-top">
                    <span className={`block text-xs font-medium ${poi.is_active ? 'text-green-700' : 'text-slate-500'}`}>{poi.is_active ? 'Đang công khai' : 'Đang ẩn'}</span>
                    {hasPermission(user, 'poi:toggle') && hasPermission(user, 'poi:update') && <button onClick={() => changeActive(poi)} disabled={pending || (!poi.is_active && !ready)} title={!poi.is_active && !ready ? poi.activation?.reasons?.join('; ') : undefined} className={`${ACTION} mt-2 ${poi.is_active ? 'bg-slate-200 text-slate-900' : 'bg-green-700 text-white'}`}>{poi.is_active ? 'Tắt công khai' : 'Bật công khai'}</button>}
                  </td>
                  <td className="p-3 align-top"><div className="flex gap-2">
                    {hasPermission(user, 'poi:update') && <button disabled={pending} onClick={() => { setEditing(poi); setFormError(''); }} className="text-teal-700 underline">Sửa</button>}
                    {hasPermission(user, 'poi:delete') && <button disabled={pending} onClick={() => deletePOI(poi)} className="text-red-700 underline">Xóa</button>}
                  </div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {loading && <p className="p-4 text-sm text-slate-500">Đang tải…</p>}
        {!loading && data.items.length === 0 && <p className="p-4 text-sm text-slate-500">Không tìm thấy quán phù hợp.</p>}
      </div>
      <div className="flex items-center justify-end gap-3 text-sm">
        <button disabled={page === 0 || loading} onClick={() => setPage((p) => p - 1)} className={`${ACTION} bg-white`}>← Trang trước</button>
        <span>Trang {page + 1} / {Math.max(1, Math.ceil(data.total / limit))}</span>
        <button disabled={(page + 1) * limit >= data.total || loading} onClick={() => setPage((p) => p + 1)} className={`${ACTION} bg-white`}>Trang sau →</button>
      </div>
      {englishPOI && <EnglishForm poi={englishPOI} onClose={() => setEnglishPOI(null)} onSaved={() => {
        setEnglishPOI(null); setMessage('Đã lưu bản dịch EN. Hãy sinh lại audio để đủ điều kiện kích hoạt.'); reload();
      }} />}
      {editing !== undefined && <POIForm key={editing?.id || 'new'} poi={editing} saving={saving} error={formError} onSave={save} onClose={() => setEditing(undefined)} />}
    </div>
  );
}
