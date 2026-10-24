import React from 'react';

/**
 * SubmissionReviewPage — Màn hình so sánh trực quan (Diff View) và phê duyệt cập nhật POI (`poi_submissions`).
 * Phụ trách: Vũ (Task 3.6)
 */
export default function SubmissionReviewPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Phê duyệt Đề xuất Cập nhật Quán (Diff View)</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 3.6] So sánh nội dung hiện tại và nội dung đề xuất từ Chủ quán, merge và tăng `dataset_version`.
      </p>
    </div>
  );
}
