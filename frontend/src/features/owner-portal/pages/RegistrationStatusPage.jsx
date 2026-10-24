import React from 'react';

/**
 * RegistrationStatusPage — Màn hình chờ Admin xác minh định danh (`pending_verification`).
 * Phụ trách: Phúc (Task 2.3)
 */
export default function RegistrationStatusPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Trạng thái Hồ sơ Chủ quán</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 2.3] Hiển thị tiến độ xét duyệt hồ sơ đăng ký và phản hồi `admin_note` (nếu có).
      </p>
    </div>
  );
}
