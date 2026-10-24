import React from 'react';

/**
 * RegistrationsPage — Kiểm duyệt đơn đăng ký Chủ quán (`poi_owner_registrations`) & Giải mã CCCD Fernet.
 * Phụ trách: Vũ (Task 3.5)
 */
export default function RegistrationsPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Kiểm duyệt Đơn Đăng ký Chủ quán</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 3.5] Đối chiếu CCCD đã giải mã, ảnh mặt tiền quán, nút Approve / Reject kèm `admin_note`.
      </p>
    </div>
  );
}
