import React, { useCallback, useEffect, useRef, useState } from 'react';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../utils/assetUrl.js';

const API_BASE = new URL(axiosClient.defaults.baseURL, window.location.origin).toString().replace(/\/$/, '');

/** Listen to current POI audio without knowing MD5 names; download via protected API. */
export default function AudioPreviewPanel({ poiId, compact = false, onlyLang = null }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [playbackError, setPlaybackError] = useState({});
  const players = useRef([]);

  const refresh = useCallback(async (signal) => {
    if (!poiId) return;
    setLoading(true);
    setError('');
    setPlaybackError({});
    try {
      const { data } = await axiosClient.get(`/admin/pois/${encodeURIComponent(poiId)}/audios`, { signal });
      if (!signal?.aborted) setResult(data);
    } catch (err) {
      if (!signal?.aborted) setError(apiErrorMessage(err, 'Không lấy được file âm thanh'));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [poiId]);

  useEffect(() => {
    setResult(null);
    players.current = [];
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  const visibleItems = result?.items?.filter((item) => !onlyLang || item.lang === onlyLang) || [];
  const ready = visibleItems.filter((item) => item.ready);
  const missing = visibleItems.filter((item) => !item.ready);

  return (
    <section className={`${compact ? 'mt-3' : 'mt-4'} rounded-lg border border-teal-200 bg-teal-50 p-3`} aria-label="Nghe và tải file âm thanh">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-teal-950">🎧 Nghe thử / Tải MP3</h3>
          <p className="text-xs text-teal-900">
            {result ? `${result.poi_name} · ${ready.length}/${visibleItems.length} ngôn ngữ có file` : 'Audio hiện tại của quán trong hệ thống'}
          </p>
        </div>
        <button type="button" onClick={() => refresh()} disabled={loading}
          className="rounded border border-teal-300 bg-white px-3 py-1.5 text-xs font-semibold text-teal-900 hover:bg-teal-100 disabled:opacity-50">
          {loading ? 'Đang tải…' : 'Làm mới audio'}
        </button>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
      {loading && !result && <p className="mt-2 text-sm text-slate-600">Đang lấy danh sách MP3…</p>}
      {result && ready.length === 0 && (
        <p className="mt-3 rounded bg-white p-3 text-sm text-slate-700">
          Chưa có MP3 hoàn chỉnh cho {onlyLang === 'en' ? 'tiếng Anh' : 'ngôn ngữ này'} trên server.
          Bấm <strong>Làm mới audio</strong> sau khi tác vụ hoàn tất;
        </p>
      )}
      {ready.length > 0 && (
        <div className="mt-3 space-y-3">
          {ready.map((item) => (
            <div key={item.lang} className="rounded-lg border border-teal-100 bg-white p-3">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{item.name} <span className="font-normal text-slate-500">({item.lang})</span></div>
                  <div className="text-xs text-slate-500">{item.voice} · {Math.round((item.size_bytes || 0) / 1024)} KB</div>
                </div>
                <a
                  href={`${API_BASE}/admin/pois/${encodeURIComponent(poiId)}/audios/${encodeURIComponent(item.lang)}/download`}
                  className="rounded bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                  aria-label={`Tải MP3 ${item.name}`}
                >Tải MP3</a>
              </div>
              <audio
                ref={(el) => { if (el) players.current[item.lang] = el; }}
                className="w-full"
                controls preload="metadata" crossOrigin="use-credentials"
                src={`${API_BASE}/admin/pois/${encodeURIComponent(poiId)}/audios/${encodeURIComponent(item.lang)}/play`}
                aria-label={`Nghe audio ${item.name}`}
                onPlay={() => {
                  Object.entries(players.current).forEach(([lang, player]) => {
                    if (lang !== item.lang && player && !player.paused) player.pause();
                  });
                }}
                onError={(event) => {
                  const mediaError = event.currentTarget.error;
                  const hint = mediaError?.code === 4
                    ? 'Trình duyệt không giải mã được MP3. Hãy tải file về và kiểm tra nội dung.'
                    : 'Không tải/phát được MP3. Kiểm tra backend :8000, quyền đăng nhập và file trên ổ đĩa.';
                  setPlaybackError((prev) => ({ ...prev, [item.lang]: hint }));
                }}
                onCanPlay={() => setPlaybackError((prev) => ({ ...prev, [item.lang]: null }))}
                onStalled={() => setPlaybackError((prev) => ({
                  ...prev,
                  [item.lang]: 'Kết nối âm thanh bị đứng. Hãy kiểm tra server, thử Làm mới audio hoặc Tải MP3 để kiểm tra file.',
                }))}
              >Trình duyệt không hỗ trợ phát MP3.</audio>
              {playbackError[item.lang] && <p role="alert" className="mt-2 text-xs text-red-700">{playbackError[item.lang]}</p>}
            </div>
          ))}
        </div>
      )}
      {result && missing.length > 0 && (
        <p className="mt-3 text-xs text-slate-600">
          Chưa có file: {missing.map((item) => item.name).join(', ')}.
          {ready.length > 0 ? ' Có thể tạo thêm các ngôn ngữ này ở form bên trên.' : ''}
        </p>
      )}
      <p className="mt-2 text-xs text-slate-500">Bạn nghe được MP3 đã lưu ngay cả khi tác vụ cũ không còn trong lịch sử. Không cần kích hoạt công khai quán.</p>
    </section>
  );
}
