import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import AudioTaskMonitor from '../components/AudioTaskMonitor.jsx';
import AudioPreviewPanel from '../components/AudioPreviewPanel.jsx';
import { apiErrorMessage } from '../utils/assetUrl.js';

const LANGUAGES = [
  ['vi', 'Tiếng Việt · HoaiMyNeural'],
  ['en', 'English · JennyNeural'],
  ['zh', '中文 · XiaoxiaoNeural'],
  ['ja', '日本語 · NanamiNeural'],
  ['ko', '한국어 · SunHiNeural'],
];

export default function AudioTasksPage() {
  const [query, setQuery] = useState('');
  const [pois, setPois] = useState([]);
  const [selectedPoi, setSelectedPoi] = useState('');
  const [langs, setLangs] = useState(LANGUAGES.map(([code]) => code));
  const [searching, setSearching] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let disposed = false;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await axiosClient.get('/admin/pois', {
          params: { q: query.trim() || undefined, limit: 100 },
        });
        if (!disposed) {
          const items = data.items || [];
          setPois(items);
          setSelectedPoi((current) => items.some((p) => p.id === current) ? current : '');
          setError('');
        }
      } catch (err) {
        if (!disposed) setError(apiErrorMessage(err, 'Không tải được danh sách quán'));
      } finally {
        if (!disposed) setSearching(false);
      }
    }, 250);
    return () => { disposed = true; clearTimeout(timer); };
  }, [query]);

  const toggle = (code) => {
    setLangs((current) => current.includes(code) ? current.filter((x) => x !== code) : [...current, code]);
  };

  async function enqueue(event) {
    event.preventDefault();
    if (!selectedPoi || !langs.length) return;
    setSending(true);
    setError('');
    setNotice('');
    try {
      const ordered = LANGUAGES.map(([code]) => code).filter((code) => langs.includes(code));
      const { data } = await axiosClient.post('/admin/audio-tasks', {
        poi_id: selectedPoi, languages: ordered,
      });
      const name = pois.find((p) => p.id === selectedPoi)?.name || selectedPoi;
      setNotice(`Đã đưa “${name}” vào hàng đợi (${ordered.length} ngôn ngữ). Mã tác vụ: ${data.id}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const exists = detail?.task_id ? ` Mã tác vụ đang xử lý: ${detail.task_id}` : '';
      setError(apiErrorMessage(err, 'Không thêm được tác vụ') + exists);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border bg-white p-5">
        <h1 className="text-xl font-bold text-slate-900">Nhà máy Audio</h1>
        <p className="mt-1 text-sm text-slate-600">
          Tạo, theo dõi và nghe thử audio theo từng quán.
        </p>
      </header>

      <form onSubmit={enqueue} className="space-y-4 rounded-xl border bg-white p-5">
        <h2 className="font-semibold text-slate-800">Tạo tác vụ audio mới</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            Tìm quán ăn
            <input
              type="search" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Nhập tên quán tại Quận 4"
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Chọn POI {searching && <span className="font-normal">(đang tìm…)</span>}
            <select required value={selectedPoi} onChange={(e) => setSelectedPoi(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2">
              <option value="">-- Chọn quán --</option>
              {pois.map((poi) => <option value={poi.id} key={poi.id}>{poi.name} · {poi.ward || 'Chưa rõ phường'}</option>)}
            </select>
          </label>
        </div>

        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-slate-700">Ngôn ngữ cần tạo</legend>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {LANGUAGES.map(([code, label]) => (
              <label key={code} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <input type="checkbox" checked={langs.includes(code)} onChange={() => toggle(code)} />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        <button disabled={!selectedPoi || langs.length === 0 || sending} type="submit"
          className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-40">
          {sending ? 'Đang thêm vào hàng đợi…' : `Tạo audio (${langs.length} ngôn ngữ)`}
        </button>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        {notice && <p role="status" className="text-sm text-emerald-700">{notice}</p>}
        <p className="text-xs text-slate-500">Mỗi quán chỉ có một tác vụ đang xử lý. Chỉnh sửa nội dung tại <Link className="underline" to="/admin/pois">POI Master</Link>.</p>
      </form>

      {selectedPoi && (
        <section className="rounded-xl border bg-white p-5">
          <h2 className="font-semibold text-slate-800">Audio hiện có của quán đang chọn</h2>
          <p className="mt-1 text-sm text-slate-600">Nghe thử hoặc tải MP3 đã hoàn tất.</p>
          <AudioPreviewPanel key={selectedPoi} poiId={selectedPoi} />
        </section>
      )}

      <AudioTaskMonitor />
    </div>
  );
}
