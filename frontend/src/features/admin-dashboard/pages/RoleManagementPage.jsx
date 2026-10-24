import React from 'react';

/**
 * RoleManagementPage — Quản trị phân quyền động (Dynamic RBAC — 32 permissions / 9 domains).
 * Phụ trách: Vũ (Task 3.3)
 */
export default function RoleManagementPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Quản lý Vai trò & Phân quyền (Dynamic RBAC)</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 3.3] Cấu hình ma trận 32 quyền cho `super_admin`, `admin`, `poi_owner`, `user`.
      </p>
    </div>
  );
}
