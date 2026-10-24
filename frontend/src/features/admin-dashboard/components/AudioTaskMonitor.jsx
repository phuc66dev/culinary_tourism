import React from 'react';

/**
 * AudioTaskMonitor — Thanh giám sát tiến độ sinh Audio TTS thời gian thực qua Server-Sent Events (SSE).
 * Phụ trách: Vũ (Task 3.9)
 */
export default function AudioTaskMonitor() {
  return (
    <div className="flex items-center justify-between rounded-xl border border-purple-200 bg-purple-50 px-4 py-3 text-xs text-purple-900">
      <div>
        <span className="font-semibold">🎧 Audio Task Pipeline (SSE Stream):</span>{' '}
        <span>Không có tác vụ TTS đang chạy (Hàng đợi tối đa 3 luồng đồng thời)</span>
      </div>
      <div className="flex gap-2">
        <button className="rounded bg-purple-200 px-2 py-1 font-medium">Pause</button>
        <button className="rounded bg-purple-200 px-2 py-1 font-medium">Resume</button>
      </div>
    </div>
  );
}
