import React from 'react';

/**
 * OfflinePackModal — Trung tâm tải trọn gói Bản đồ Vector (.pmtiles) + Danh sách quán + Audio Quận 4.
 * Phụ trách: Bảo (Task 1.10)
 */
export default function OfflinePackModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-bold">Gói Dữ Liệu Ngoại Tuyến Quận 4</h2>
        <p className="mt-1 text-sm text-slate-600">
          Tải trước bản đồ PMTiles và thuyết minh âm thanh để sử dụng không cần 4G/Wi-Fi.
        </p>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}
