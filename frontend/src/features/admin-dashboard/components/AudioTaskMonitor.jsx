import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FiChevronLeft, FiChevronRight, FiHeadphones, FiInfo, FiRefreshCw, FiSearch } from 'react-icons/fi';
import ReviewDialog from './ReviewDialog.jsx';
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
  queued: 'bg-slate-200 text-slate-700', running: 'bg-blue-100 text-blue-900',
  paused: 'bg-amber-200 text-amber-900', completed: 'bg-green-200 text-green-900',
  failed: 'bg-red-200 text-red-900', cancelled: 'bg-slate-200 text-slate-600',
};

function streamUrl() {
  const base = axiosClient.defaults.baseURL.replace(/\/$/, '');
  return new URL(`${base}/admin/audio-tasks/stream`, window.location.origin).toString();
}

function TaskDetails({ task, busy, onAction, onManualSave, clock }) {
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
  const isWaitingToRetry = task.status === 'queued' && Boolean(task.retry_at);
  const isSpeechRetry = task.retry_kind === 'speech';
  const isRateLimited = isWaitingToRetry && !isSpeechRetry;
  const due = isWaitingToRetry ? new Date(task.retry_at).getTime() : NaN;
  const remaining = Number.isFinite(due) ? Math.max(0, Math.ceil((due - clock) / 1000)) : null;

  async function saveManual(event) {
    event.preventDefault();
    setSavingManual(true);
    setManualError('');
    setManualNotice('');
    try {
      await onManualSave(task.id, selectedManualLang, manualTitle.trim(), manualDescription.trim());
      setManualNotice(`Đã lưu ${LANG_LABEL[selectedManualLang] || selectedManualLang}. Nhập tiếp ngôn ngữ còn thiếu rồi nhấn Tiếp tục.`);
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
    <div className="rounded-lg border border-slate-200 bg-white p-4">
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
          {['queued', 'running'].includes(task.status) && (
            <button type="button" disabled={busy} onClick={() => onAction(task.id, 'pause')}
              className={`${btn} bg-amber-100 text-amber-900 hover:bg-amber-200`}>Tạm dừng</button>
          )}
          {isWaitingToRetry && (
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
              {task.status === 'failed' ? 'Thử lại' : 'Tiếp tục'}
            </button>
          )}
          {(active || task.status === 'failed') && (
            <button type="button" disabled={busy} onClick={() => onAction(task.id, 'cancel')}
              className={`${btn} bg-red-100 text-red-800 hover:bg-red-200`}>Hủy tác vụ</button>
          )}
        </div>
      </div>
      <div role="progressbar" aria-label={`Tiến độ audio ${name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full transition-all duration-500 ${task.status === 'paused' ? 'bg-amber-500' : task.status === 'failed' ? 'bg-red-500' : 'bg-blue-600'}`}
          style={{ width: `${pct}%` }} />
      </div>
      {isWaitingToRetry && (
        <p role="status" className="mt-2 text-xs text-amber-800">
          {task.error || (isSpeechRetry ? 'Dịch vụ tạo MP3 đang gián đoạn.' : 'Google Translate đang giới hạn.')}{' '}
          (Lượt thử lại {isSpeechRetry ? task.speech_retries : task.translation_retries || 1}/3).{' '}
          {remaining === null ? 'Chưa xác định thời gian thử lại.' : remaining > 0
            ? `Tự thử lại lúc ${new Date(task.retry_at).toLocaleString('vi-VN')} (còn khoảng ${Math.ceil(remaining / 60)} phút).`
            : 'Đã đến hạn thử lại; đang đợi worker tiếp nhận (thường trong 15 giây).'}{' '}
          {!isSpeechRetry && 'Có thể nhập bản dịch thủ công rồi tiếp tục tạo MP3.'}
        </p>
      )}
      {task.status === 'failed' && task.error && <p role="alert" className="mt-2 text-xs text-red-700">{task.error}</p>}
      {showManual && pendingLanguages.length > 0 && (
        <form onSubmit={saveManual} className="mt-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-sm font-semibold text-slate-800">Bản dịch để tạo MP3 (không gọi Google)</p>
          <p className="text-xs text-slate-600">Dán tên và mô tả đã dịch đúng ngôn ngữ. Khi lưu, hệ thống sẽ tạm dừng tác vụ; nhập đủ các ngôn ngữ còn thiếu rồi nhấn Tiếp tục.</p>
          {savedManualLangs.length > 0 && <p className="text-xs text-emerald-800">Đã lưu trong phiên này: {savedManualLangs.map((l) => LANG_LABEL[l] || l).join(', ')}.</p>}
          {unfilledLanguages.length === 0 ? (
            <p className="text-sm text-slate-700">Đã lưu các bản dịch còn thiếu. Nhấn <strong>Tiếp tục</strong> để tiếp tục tạo MP3.</p>
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
    </div>
  );
}

export default function AudioTaskMonitor({ refreshVersion = 0 }) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(15);
  const [dialog, setDialog] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const authRetries = useRef(0);
  const actionInFlight = useRef(false);
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

  useEffect(() => { load(); }, [load, refreshVersion]);

  useEffect(() => {
    let es;
    let timer;
    let disposed = false;
    const connect = () => {
      if (disposed) return;
      es = new EventSource(streamUrl(), { withCredentials: true });
      es.onopen = () => { setConnected(true); authRetries.current = 0; };
      es.addEventListener('tasks', (event) => {
        try { const snapshot = JSON.parse(event.data); if (Array.isArray(snapshot)) { setTasks(snapshot); setLoading(false); } } catch { /* giữ snapshot cuối cùng nếu payload lỗi */ }
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
    if (actionInFlight.current) return;
    actionInFlight.current = true;
    setBusyId(id);
    setActionError(null);
    try {
      await axiosClient.post(`/admin/audio-tasks/${id}/${action}`);
      await load(); // cập nhật ngay cả khi SSE đang ngắt kết nối
    } catch (err) {
      setActionError({ id, message: apiErrorMessage(err, 'Không thực hiện được thao tác') });
    } finally {
      actionInFlight.current = false;
      setBusyId(null);
    }
  }, [load]);

  const saveManual = useCallback(async (taskId, lang, title, description) => {
    if (actionInFlight.current) throw new Error('Một thao tác khác đang xử lý.');
    actionInFlight.current = true;
    setBusyId(taskId);
    try {
      await axiosClient.put(`/admin/audio-tasks/${encodeURIComponent(taskId)}/translations/${encodeURIComponent(lang)}`, {
        title, description,
      });
      await load();
    } finally {
      actionInFlight.current = false;
      setBusyId(null);
    }
  }, [load]);

  const filtered = tasks.filter((task) =>
    (filter === 'all' || (filter === 'active' ? ACTIVE.includes(task.status) : task.status === filter)) &&
    (task.poi_name || task.poi_id || '').toLocaleLowerCase('vi').includes(search.trim().toLocaleLowerCase('vi')));
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  useEffect(() => { setPage((value) => Math.min(value, pageCount - 1)); }, [pageCount]);
  const running = tasks.filter((t) => t.status === 'running').length;
  const queued = tasks.filter((t) => t.status === 'queued').length;
  const paused = tasks.filter((t) => t.status === 'paused').length;

  const currentTask = dialog && (tasks.find((task) => task.id === dialog.task.id) || dialog.task);
  const detailsOpen = dialog?.kind === 'details';
  const errorInDialog = detailsOpen && actionError?.id === currentTask.id;
  const summary = filtered.length
    ? `${currentPage * pageSize + 1}–${currentPage * pageSize + visible.length} trên ${filtered.length} tác vụ`
    : '0 tác vụ';

  function openDialog(kind, task) {
    setActionError(null);
    setDialog({ kind, task });
  }

  return (
    <section className="audio-queue" aria-label="Hàng đợi tác vụ audio">
      <header className="audio-panel-heading">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2>Hàng đợi tác vụ</h2>
            <p>{running} đang chạy · {queued} đang chờ · {paused} tạm dừng</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="audio-connection text-xs text-slate-600" role="status">
              <span className={connected ? 'is-connected' : ''} />
              {connected ? 'Đang cập nhật trực tiếp' : 'Đang kết nối lại'}
            </span>
            <button type="button" onClick={load} className="audio-action-icon" aria-label="Tải lại danh sách" title="Tải lại danh sách">
              <FiRefreshCw aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="audio-queue-toolbar">
          <div className="audio-queue-filters">
            <label className="audio-search">
              <FiSearch aria-hidden="true" />
              <input type="search" aria-label="Tìm quán trong hàng đợi" placeholder="Tìm tên quán…"
                value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} />
            </label>
            <label className="audio-filter">Trạng thái
              <select value={filter} onChange={(event) => { setFilter(event.target.value); setPage(0); }}>
                <option value="all">Tất cả trạng thái</option><option value="active">Đang xử lý</option>
                {Object.entries(STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          <div className="audio-filter">
            <label className="audio-filter">Hiển thị
              <select aria-label="Số tác vụ mỗi trang" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }}>
                {[5, 15, 25, 50].map((size) => <option key={size} value={size}>{size}</option>)}
              </select>
              tác vụ mỗi trang
            </label>
            <span className="text-slate-500">{filtered.length} tác vụ</span>
          </div>
        </div>
        <p>Tìm kiếm và lọc trong tối đa 50 tác vụ gần nhất.</p>
      </header>
      {error && <div role="alert" className="m-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {actionError && !errorInDialog && (
        <p role="alert" className="m-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{actionError.message}</p>
      )}
      <div className="audio-table-scroll">
        <table className="audio-task-table">
          <thead><tr><th scope="col">Quán</th><th scope="col">Tiến độ</th><th scope="col">Trạng thái</th><th scope="col">Thao tác</th></tr></thead>
          <tbody>
            {visible.map((task) => {
              const name = task.poi_name || task.poi_id;
              const percent = task.total ? Math.min(100, Math.max(0, Math.round(task.done / task.total * 100))) : 0;
              return (
                <tr key={task.id}>
                  <th scope="row">
                    <span className="font-semibold">{name}</span>
                    {task.current_language && task.status === 'running' && <small>Đang tạo {LANG_LABEL[task.current_language] || task.current_language}</small>}
                  </th>
                  <td>
                    <span className="audio-progress-label">{task.done || 0}/{task.total || 0} ngôn ngữ <span>{percent}%</span></span>
                    <progress aria-label={'Tiến độ ' + name} value={percent} max={100} />
                  </td>
                  <td><span className={'audio-status ' + (STATUS_STYLE[task.status] || '')}>{STATUS_LABEL[task.status] || task.status}</span>
                    {task.error && <small className="audio-error-summary" title={task.error}>{task.error}</small>}
                    {task.retry_at && task.status === 'queued' && <small>Đã lên lịch thử lại</small>}
                  </td>
                  <td><div className="audio-row-actions">
                    <button type="button" className="audio-action-icon" title="Chi tiết tác vụ" aria-label={'Chi tiết tác vụ ' + name}
                      aria-haspopup="dialog" onClick={() => openDialog('details', task)}><FiInfo aria-hidden="true" /></button>
                    {(task.done > 0 || task.status === 'completed') && (
                      <button type="button" className="audio-action-icon" title="Nghe thử" aria-label={'Nghe thử ' + name}
                        aria-haspopup="dialog" onClick={() => openDialog('preview', task)}><FiHeadphones aria-hidden="true" /></button>
                    )}
                    {(task.status === 'failed' || (task.status === 'queued' && task.retry_at)) && (
                      <button type="button" className="audio-action-icon" title="Thử lại" aria-label={'Thử lại ' + name}
                        disabled={busyId !== null} onClick={() => act(task.id, task.status === 'failed' ? 'resume' : 'retry')}>
                        <FiRefreshCw aria-hidden="true" />
                      </button>
                    )}
                  </div></td>
                </tr>
              );
            })}
            {!visible.length && <tr><td colSpan={4} className="audio-table-empty">
              {loading ? 'Đang tải tác vụ…' : 'Không có tác vụ phù hợp.'}
            </td></tr>}
          </tbody>
        </table>
      </div>
      <footer className="audio-pagination">
        <span>{summary}</span>
        <nav aria-label="Phân trang hàng đợi tác vụ">
          <button type="button" className="audio-page-button" aria-label="Trang trước" disabled={!currentPage} onClick={() => setPage(currentPage - 1)}>
            <FiChevronLeft aria-hidden="true" />
          </button>
          <span className="audio-page-current" aria-current="page" aria-label={`Trang ${currentPage + 1} trên ${pageCount}`}>{currentPage + 1}</span>
          <button type="button" className="audio-page-button" aria-label="Trang sau" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>
            <FiChevronRight aria-hidden="true" />
          </button>
        </nav>
      </footer>

      {detailsOpen && (
        <ReviewDialog title="Chi tiết tác vụ" description={currentTask.poi_name || currentTask.poi_id}
          busy={busyId === currentTask.id} onClose={() => setDialog(null)}>
          {errorInDialog && <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{actionError.message}</p>}
          <TaskDetails key={currentTask.id} task={currentTask} busy={busyId !== null}
            onAction={act} onManualSave={saveManual} clock={clock} />
        </ReviewDialog>
      )}
      {dialog?.kind === 'preview' && (
        <ReviewDialog widthClass="max-w-xl" title="Nghe thử audio" description={currentTask.poi_name || currentTask.poi_id} onClose={() => setDialog(null)}>
          <AudioPreviewPanel poiId={currentTask.poi_id} studio />
        </ReviewDialog>
      )}
    </section>
  );
}
