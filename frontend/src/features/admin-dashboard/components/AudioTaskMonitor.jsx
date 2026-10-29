import React, { useCallback, useEffect, useRef, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../utils/assetUrl.js';
import AudioPreviewPanel from './AudioPreviewPanel.jsx';

/** Task 3.9 — SSE monitor. Snapshot REST is also available during reconnects. */
const MAX_AUTH_RETRIES = 3;
const ACTIVE = ['queued', 'running', 'paused'];
const LANG_LABEL = { vi: 'Tiếng Việt', en: 'English', zh: '中文', ja: '日本語', ko: '한국어' };
const STATUS_LABEL = {
  queued: 'Đang chờ', running: 'Đang chạy', paused: 'Tạm dừng',
  completed: 'Hoàn tất', failed: 'Lỗi', cancelled: 'Đã hủy',
};
const STATUS_STYLE = {
  queued: 'bg-slate-200 text-slate-700', running: 'bg-purple-200 text-purple-900',
  paused: 'bg-amber-200 text-amber-900', completed: 'bg-green-200 text-green-900',
  failed: 'bg-red-200 text-red-900', cancelled: 'bg-slate-200 text-slate-600',
};

function streamUrl() {
  const base = axiosClient.defaults.baseURL.replace(/\/$/, '');
  return new URL(`${base}/admin/audio-tasks/stream`, window.location.origin).toString();
}

function TaskRow({ task, busy, onAction, onManualSave, clock }) {
  const [showAudio, setShowAudio] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [manualLang, setManualLang] = useState('');
  const [manualTitle, setManualTitle] = useState('');
  const [manualDescription, setManualDescription] = useState('');
  const [manualError, setManualError] = useState('');
  const [manualNotice, setManualNotice] = useState('');
  const [savingManual, setSavingManual] = useState(false);
  const [savedManualLangs, setSavedManualLangs] = useState([]);
  const pendingLanguages = (task.languages || []).slice(task.done || 0).filter((lang) => lang !== 'vi');
  const unfilledLanguages = pendingLanguages.filter((lang) => !savedManualLangs.includes(lang));
  const selectedManualLang = unfilledLanguages.includes(manualLang) ? manualLang : (unfilledLanguages[0] || '');
  const isRateLimited = task.status === 'queued' && Boolean(task.retry_at);
  const due = isRateLimited ? new Date(task.retry_at).getTime() : NaN;
  const remaining = Number.isFinite(due) ? Math.max(0, Math.ceil((due - clock) / 1000)) : null;

  async function saveManual(event) {
    event.preventDefault();
    setSavingManual(true);
    setManualError('');
    setManualNotice('');
    try {
      await onManualSave(task.id, selectedManualLang, manualTitle.trim(), manualDescription.trim());
      setManualNotice(`Đã lưu ${LANG_LABEL[selectedManualLang] || selectedManualLang}. Nhập tiếp ngôn ngữ còn thiếu rồi nhấn Resume.`);
      setManualTitle('');
      setManualDescription('');
      setSavedManualLangs((current) => [...new Set([...current, selectedManualLang])]);
      const rest = unfilledLanguages.filter((l) => l !== selectedManualLang);
      if (rest.length) setManualLang(rest[0]);
    } catch (err) {
      setManualError(apiErrorMessage(err, 'Không lưu được bản dịch'));
    } finally {
      setSavingManual(false);
    }
  }
  const active = ACTIVE.includes(task.status);
  const pct = task.total ? Math.min(100, Math.max(0, Math.round((task.done / task.total) * 100))) : 0;
  const name = task.poi_name || task.poi_id;
  const btn = 'rounded px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40';
  const startLabel = task.status === 'running' ? 'Đang tạo audio cho' : task.status === 'paused' ? 'Đã tạm dừng audio cho' : 'Đang chờ tạo audio cho';

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-sm text-slate-900">
            {active ? startLabel : 'Audio của'} <strong>{name}</strong>: <strong>{task.done}/{task.total}</strong> ngôn ngữ
            <span className={`ml-2 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[task.status] || ''}`}>
              {STATUS_LABEL[task.status] || task.status}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {task.status === 'running' && task.current_language ? `Đang xử lý ${LANG_LABEL[task.current_language] || task.current_language} · ` : ''}
            Đã dùng lại cache: {task.cache_hits || 0} tệp
            {task.recovered_at ? ' · Đã khôi phục sau restart' : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(task.done > 0 || task.status === 'completed') && (
            <button type="button" onClick={() => setShowAudio((v) => !v)}
              aria-expanded={showAudio}
              className={`${btn} bg-teal-700 text-white hover:bg-teal-800`}>
              {showAudio ? 'Ẩn trình phát' : '🎧 Nghe / Tải MP3'}
            </button>
          )}
          {['queued', 'running'].includes(task.status) && (
            <button type="button" disabled={busy} onClick={() => onAction(task.id, 'pause')}
              className={`${btn} bg-amber-100 text-amber-900 hover:bg-amber-200`}>Pause</button>
          )}
          {isRateLimited && (
            <button type="button" disabled={busy} onClick={() => onAction(task.id, 'retry')}
              className={`${btn} border border-slate-300 bg-white text-slate-700 hover:bg-slate-100`}>Thử lại ngay</button>
          )}
          {pendingLanguages.length > 0 && (isRateLimited || ['paused', 'failed'].includes(task.status)) && (
            <button type="button" onClick={() => setShowManual((v) => !v)}
              className={`${btn} border border-teal-300 bg-white text-teal-800 hover:bg-teal-50`}>
              {showManual ? 'Ẩn nhập bản dịch' : 'Nhập bản dịch thủ công'}
            </button>
          )}
          {['paused', 'failed'].includes(task.status) && (
            <button type="button" disabled={busy} onClick={() => onAction(task.id, 'resume')}
              className={`${btn} bg-green-100 text-green-900 hover:bg-green-200`}>
              {task.status === 'failed' ? 'Thử lại' : 'Resume'}
            </button>
          )}
          {(active || task.status === 'failed') && (
            <button type="button" disabled={busy} onClick={() => onAction(task.id, 'cancel')}
              className={`${btn} bg-red-100 text-red-800 hover:bg-red-200`}>Cancel</button>
          )}
        </div>
      </div>
      <div role="progressbar" aria-label={`Tiến độ audio ${name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full transition-all duration-500 ${task.status === 'paused' ? 'bg-amber-500' : task.status === 'failed' ? 'bg-red-500' : 'bg-purple-600'}`}
          style={{ width: `${pct}%` }} />
      </div>
      {isRateLimited && (
        <p role="status" className="mt-2 text-xs text-amber-800">
          Google Translate đang giới hạn (lần {task.translation_retries || 1}/3).{' '}
          {remaining === null ? 'Chưa xác định thời gian thử lại.' : remaining > 0
            ? `Tự thử lại lúc ${new Date(task.retry_at).toLocaleString('vi-VN')} (còn khoảng ${Math.ceil(remaining / 60)} phút).`
            : 'Đã đến hạn thử lại; đang đợi worker tiếp nhận (thường trong 15 giây).'}{' '}
          Nếu Google vẫn từ chối, có thể nhập bản dịch thủ công rồi tiếp tục tạo MP3.
        </p>
      )}
      {task.status === 'failed' && task.error && <p role="alert" className="mt-2 text-xs text-red-700">{task.error}</p>}
      {showManual && pendingLanguages.length > 0 && (
        <form onSubmit={saveManual} className="mt-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-sm font-semibold text-slate-800">Bản dịch để tạo MP3 (không gọi Google)</p>
          <p className="text-xs text-slate-600">Dán tên và mô tả đã dịch đúng ngôn ngữ. Khi lưu, hệ thống sẽ tạm dừng tác vụ; nhập đủ các ngôn ngữ còn thiếu rồi nhấn Resume.</p>
          {savedManualLangs.length > 0 && <p className="text-xs text-emerald-800">Đã lưu trong phiên này: {savedManualLangs.map((l) => LANG_LABEL[l] || l).join(', ')}.</p>}
          {unfilledLanguages.length === 0 ? (
            <p className="text-sm text-slate-700">Đã lưu các bản dịch còn thiếu. Nhấn <strong>Resume</strong> để tiếp tục tạo MP3.</p>
          ) : (<>
          <label className="block text-xs font-medium text-slate-700">Ngôn ngữ
            <select className="mt-1 w-full rounded border border-slate-300 bg-white p-2 text-sm"
              value={selectedManualLang} onChange={(e) => { setManualLang(e.target.value); setManualTitle(''); setManualDescription(''); setManualNotice(''); }}>
              {unfilledLanguages.map((lang) => <option key={lang} value={lang}>{LANG_LABEL[lang] || lang}</option>)}
            </select>
          </label>
          <label className="block text-xs font-medium text-slate-700">Tên quán đã dịch
            <input required maxLength={180} value={manualTitle} onChange={(e) => setManualTitle(e.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white p-2 text-sm" placeholder="Nhập tên bằng ngôn ngữ đã chọn" />
          </label>
          <label className="block text-xs font-medium text-slate-700">Mô tả đã dịch
            <textarea required maxLength={8000} rows={4} value={manualDescription} onChange={(e) => setManualDescription(e.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white p-2 text-sm" placeholder="Dán mô tả đầy đủ" />
          </label>
          {manualError && <p role="alert" className="text-xs text-red-700">{manualError}</p>}
          {manualNotice && <p role="status" className="text-xs text-emerald-700">{manualNotice}</p>}
          <button type="submit" disabled={savingManual || busy || !selectedManualLang || !manualTitle.trim() || !manualDescription.trim()}
            className={`${btn} bg-teal-700 text-white hover:bg-teal-800`}>
            {savingManual ? 'Đang lưu…' : 'Lưu bản dịch'}
          </button>
          </>)}
        </form>
      )}
      {showAudio && <AudioPreviewPanel poiId={task.poi_id} compact />}
    </li>
  );
}

export default function AudioTaskMonitor() {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const authRetries = useRef(0);
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 10000);
    return () => clearInterval(timer);
  }, []);

  const load = useCallback(async () => {
    try {
      const { data } = await axiosClient.get('/admin/audio-tasks');
      setTasks(data.items || []);
      setError('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Không tải được danh sách tác vụ'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let es;
    let timer;
    let disposed = false;
    load();

    const connect = () => {
      if (disposed) return;
      es = new EventSource(streamUrl(), { withCredentials: true });
      es.onopen = () => { setConnected(true); authRetries.current = 0; };
      es.addEventListener('tasks', (event) => {
        try { setTasks(JSON.parse(event.data)); } catch { /* giữ snapshot cuối cùng nếu payload lỗi */ }
      });
      es.onerror = () => {
        setConnected(false);
        if (es.readyState !== EventSource.CLOSED) return; // browser tự retry khi CONNECTING
        es.close();
        if (disposed || authRetries.current >= MAX_AUTH_RETRIES) return;
        authRetries.current += 1;
        axiosClient.post('/admin/auth/refresh')
          .then(() => { timer = setTimeout(() => !disposed && connect(), 500); })
          .catch(() => setError('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.'));
      };
    };
    connect();
    return () => { disposed = true; clearTimeout(timer); es?.close(); };
  }, [load]);

  const act = useCallback(async (id, action) => {
    setBusyId(id);
    setError('');
    try {
      await axiosClient.post(`/admin/audio-tasks/${id}/${action}`);
      await load(); // cập nhật ngay cả khi SSE đang ngắt kết nối
    } catch (err) {
      setError(apiErrorMessage(err, 'Không thực hiện được thao tác'));
    } finally {
      setBusyId(null);
    }
  }, [load]);

  const saveManual = useCallback(async (taskId, lang, title, description) => {
    await axiosClient.put(`/admin/audio-tasks/${encodeURIComponent(taskId)}/translations/${encodeURIComponent(lang)}`, {
      title, description,
    });
    await load();
  }, [load]);

  const filtered = tasks.filter((t) => filter === 'all' || (filter === 'active' ? ACTIVE.includes(t.status) : t.status === filter));
  const running = tasks.filter((t) => t.status === 'running').length;
  const queued = tasks.filter((t) => t.status === 'queued').length;
  const paused = tasks.filter((t) => t.status === 'paused').length;

  return (
    <section className="rounded-xl border border-purple-200 bg-purple-50 p-5" aria-label="Giám sát tác vụ audio">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-purple-950">🎧 Giám sát Audio Task Pipeline</h2>
          <p className="mt-1 text-xs text-purple-900">
            {running} đang chạy · {queued} đang chờ · {paused} tạm dừng · {tasks.length} tác vụ gần nhất
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-purple-900">
          <span className="flex items-center gap-1.5" role="status">
            <span className={`h-2 w-2 rounded-full ${connected ? 'bg-green-500' : 'bg-slate-400'}`} />
            {connected ? 'SSE trực tiếp' : 'SSE đang kết nối lại'}
          </span>
          <button type="button" onClick={load} className="rounded border border-purple-300 bg-white px-2 py-1">Tải lại</button>
        </div>
      </div>
      {error && <div role="alert" className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">{error}</div>}
      <div className="mt-4 flex items-center gap-3 text-sm">
        <label htmlFor="audio-task-status-filter">Trạng thái</label>
        <select id="audio-task-status-filter" value={filter} onChange={(e) => setFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white p-2 text-sm">
          <option value="all">Tất cả</option><option value="active">Đang xử lý</option>
          <option value="completed">Hoàn tất</option><option value="failed">Lỗi</option>
          <option value="cancelled">Đã hủy</option>
        </select>
      </div>
      {loading ? <p className="mt-3 text-sm">Đang tải tác vụ…</p> : filtered.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">Không có tác vụ phù hợp.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {filtered.map((t) => <TaskRow key={t.id} task={t} busy={busyId === t.id} onAction={act} onManualSave={saveManual} clock={clock} />)}
        </ul>
      )}
    </section>
  );
}
