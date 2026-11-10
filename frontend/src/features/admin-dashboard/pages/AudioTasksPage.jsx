import React, { useEffect, useRef, useState } from 'react';
import { FiCheck, FiChevronDown, FiPlus, FiSearch } from 'react-icons/fi';
import { Link } from 'react-router-dom';
import axiosClient from '../../../api/axiosClient.js';
import AudioTaskMonitor from '../components/AudioTaskMonitor.jsx';
import ReviewDialog from '../components/ReviewDialog.jsx';
import { apiErrorMessage } from '../utils/assetUrl.js';
import './audio-studio.css';

const LANGUAGES = [
  ['vi', 'Tiếng Việt'],
  ['en', 'English'],
  ['zh', '中文'],
  ['ja', '日本語'],
  ['ko', '한국어'],
];
const POIS_PER_PAGE = 30;

function ShopPicker({ selected, onSelect }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [result, setResult] = useState(null);
  const trigger = useRef(null);
  const requestKey = JSON.stringify([query.trim(), page]);
  const current = result?.key === requestKey ? result : null;

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const { data } = await axiosClient.get('/admin/pois', {
          params: { q: query.trim() || undefined, limit: POIS_PER_PAGE, skip: page * POIS_PER_PAGE },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setResult({ key: requestKey, data });
      } catch (error) {
        if (!controller.signal.aborted) {
          setResult({ key: requestKey, error: apiErrorMessage(error, 'Không tải được danh sách quán.') });
        }
      }
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [open, query, page, requestKey]);

  function closePicker() {
    setOpen(false);
    trigger.current?.focus();
  }

  return (
    <div>
      <label htmlFor="audio-shop-picker" className="mb-2 block text-sm font-semibold">Quán cần tạo audio</label>
      <button ref={trigger} id="audio-shop-picker" type="button" className="audio-picker-trigger"
        aria-expanded={open} aria-controls={open ? 'audio-shop-options' : undefined}
        onClick={() => setOpen((value) => !value)}>
        <span>{selected?.name || 'Chọn quán'}</span><FiChevronDown aria-hidden="true" />
      </button>
      {open && (
        <div id="audio-shop-options" className="audio-picker-menu">
          <label className="audio-search">
            <FiSearch aria-hidden="true" />
            <input autoFocus type="search" aria-label="Tìm quán để tạo audio" placeholder="Nhập tên quán…"
              value={query} onKeyDown={(event) => { if (event.key === 'Enter') event.preventDefault(); }}
              onChange={(event) => { setQuery(event.target.value); setPage(0); }} />
          </label>
          {!current && <p role="status" className="p-3 text-sm text-slate-600">Đang tìm quán…</p>}
          {current?.error && <p role="alert" className="p-3 text-sm text-red-800">{current.error}</p>}
          {current?.data && (
            <>
              <ul className="audio-picker-options" aria-label="Danh sách quán">
                {current.data.items.map((poi) => (
                  <li key={poi.id}>
                    <button type="button" aria-pressed={selected?.id === poi.id}
                      onClick={() => { onSelect(poi); closePicker(); }}>
                      <span><strong>{poi.name}</strong>{poi.ward && <small>{poi.ward}</small>}</span>
                      {selected?.id === poi.id && <FiCheck aria-hidden="true" />}
                    </button>
                  </li>
                ))}
              </ul>
              {!current.data.items.length && <p className="p-3 text-sm text-slate-600">Không tìm thấy quán phù hợp.</p>}
              {(page > 0 || current.data.total > POIS_PER_PAGE) && (
                <div className="flex items-center justify-between border-t border-slate-200 p-2 text-xs">
                  <button type="button" className="audio-small-button" disabled={page === 0}
                    onClick={() => setPage(page - 1)}>Quán trước</button>
                  <span>Trang {page + 1}</span>
                  <button type="button" className="audio-small-button" disabled={(page + 1) * POIS_PER_PAGE >= current.data.total}
                    onClick={() => setPage(page + 1)}>Quán tiếp theo</button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function CreateAudioDialog({ onClose, onCreated }) {
  const [selected, setSelected] = useState(null);
  const [langs, setLangs] = useState(LANGUAGES.map(([code]) => code));
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  function toggle(code) {
    setLangs((current) => current.includes(code) ? current.filter((lang) => lang !== code) : [...current, code]);
  }

  async function enqueue(event) {
    event.preventDefault();
    if (sending || !selected || !langs.length) return;
    setSending(true);
    setError('');
    const languages = LANGUAGES.map(([code]) => code).filter((code) => langs.includes(code));
    try {
      await axiosClient.post('/admin/audio-tasks', { poi_id: selected.id, languages });
      onCreated(`Đã đưa “${selected.name}” vào hàng đợi tạo audio (${languages.length} ngôn ngữ).`);
    } catch (err) {
      const taskId = err.response?.data?.detail?.task_id;
      setError(apiErrorMessage(err, 'Không thêm được tác vụ') + (taskId ? ` Mã tác vụ đang xử lý: ${taskId}` : ''));
    } finally {
      setSending(false);
    }
  }

  return (
    <ReviewDialog widthClass="max-w-xl" title="Tạo audio cho quán" description="Chọn quán và các ngôn ngữ cần tạo."
      busy={sending} onClose={onClose}
      footer={<div className="flex flex-wrap justify-end gap-2">
        <button type="button" className="audio-small-button px-4" onClick={onClose} disabled={sending}>Hủy</button>
        <button type="submit" form="create-shop-audio" className="audio-primary" disabled={sending || !selected || !langs.length}>
          {sending ? 'Đang thêm vào hàng đợi…' : `Tạo audio (${langs.length} ngôn ngữ)`}
        </button>
      </div>}>
      <form id="create-shop-audio" onSubmit={enqueue} className="space-y-5">
        <fieldset disabled={sending} className="space-y-5">
          <ShopPicker selected={selected} onSelect={setSelected} />
          <fieldset>
            <legend className="mb-2 text-sm font-semibold">Ngôn ngữ cần tạo</legend>
            <div className="audio-language-options">
              {LANGUAGES.map(([code, label]) => (
                <label key={code} className="audio-language-option">
                  <input type="checkbox" checked={langs.includes(code)} onChange={() => toggle(code)} />{label}
                </label>
              ))}
            </div>
          </fieldset>
        </fieldset>
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <p className="text-xs text-slate-600">Mỗi quán chỉ có một tác vụ đang xử lý. Chỉnh sửa nội dung tại <Link className="underline" to="/admin/pois">POI Master</Link>.</p>
      </form>
    </ReviewDialog>
  );
}

export default function AudioTasksPage() {
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState('');
  const [refreshVersion, setRefreshVersion] = useState(0);

  return (
    <div className="audio-studio">
      <header className="audio-studio-heading">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Nhà máy Audio</h1>
          <p className="mt-1 text-sm text-slate-600">Tạo, theo dõi và nghe thử audio theo từng quán.</p>
        </div>
        <button type="button" aria-haspopup="dialog" className="audio-primary" onClick={() => setCreating(true)}>
          <FiPlus aria-hidden="true" size={17} /> Tạo audio cho quán
        </button>
      </header>
      {notice && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{notice}</p>}
      <AudioTaskMonitor refreshVersion={refreshVersion} />
      {creating && <CreateAudioDialog onClose={() => setCreating(false)} onCreated={(message) => {
        setNotice(message);
        setCreating(false);
        setRefreshVersion((value) => value + 1);
      }} />}
    </div>
  );
}
