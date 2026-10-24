import React from 'react';

/**
 * AuditLogsPage — Nhật ký thao tác nhạy cảm của hệ thống (`audit_logs`).
 * Phụ trách: Vũ (Task 3.10)
 */
export default function AuditLogsPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Nhật ký Hệ thống (Audit Logs)</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 3.10] Truy vết hành động thêm/sửa/xóa POI, duyệt tài khoản kèm `user_id`, IP và timestamp.
      </p>
    </div>
  );
}
