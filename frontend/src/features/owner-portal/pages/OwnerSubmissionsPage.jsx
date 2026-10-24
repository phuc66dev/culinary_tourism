import React from 'react';

/**
 * OwnerSubmissionsPage — Danh sách các đề xuất cập nhật quán (`poi_submissions`) đã gửi.
 * Phụ trách: Phúc (Task 2.6)
 */
export default function OwnerSubmissionsPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Lịch sử Gửi duyệt Cập nhật</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 2.6] Theo dõi các bản ghi `poi_submissions` (pending / approved / rejected).
      </p>
    </div>
  );
}
