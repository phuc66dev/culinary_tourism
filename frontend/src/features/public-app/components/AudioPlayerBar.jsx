import React from 'react';

/**
 * AudioPlayerBar — Thanh trình phát âm thanh nổi dưới đáy màn hình (Play, Pause, Replay, Tiến trình).
 * Phụ trách: Bảo (Task 1.7)
 */
export default function AudioPlayerBar() {
  return (
    <div className="fixed right-4 bottom-4 left-4 z-30 flex items-center justify-between rounded-2xl bg-slate-900/95 px-4 py-3 text-white shadow-lg">
      <div className="text-xs">
        <span className="font-semibold">🎧 Audio Tour Sẵn Sàng</span>
        <p className="text-slate-400">Đi bộ vào bán kính 30m quanh quán để nghe thuyết minh tự động</p>
      </div>
    </div>
  );
}
