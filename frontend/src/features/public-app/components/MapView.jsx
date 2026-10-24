import React from 'react';

/**
 * MapView — Bản đồ tương tác MapLibre GL + PMTiles (3 chế độ: Cloud, Offline Pack, Hybrid).
 * Phụ trách: Bảo (Task 1.2, Task 1.3)
 */
export default function MapView({ onOpenOfflinePacks }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-slate-200">
      <p className="text-sm font-medium text-slate-600">
        [Skeleton] MapLibre GL Canvas — Tâm điểm Quận 4 (10.7582, 106.7028)
      </p>
      <button
        onClick={onOpenOfflinePacks}
        className="mt-3 rounded-lg bg-teal-700 px-4 py-2 text-xs font-semibold text-white"
      >
        Quản lý Gói Offline (.pmtiles)
      </button>
    </div>
  );
}
