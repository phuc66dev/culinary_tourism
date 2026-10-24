import React from 'react';

/**
 * LoginPage — Trang đăng nhập sử dụng httpOnly Cookie Auth (`/admin/login`).
 * Phụ trách: Vũ (Task 3.2)
 */
export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-bold text-slate-800">Đăng Nhập Hệ Thống</h1>
        <p className="mt-1 text-sm text-slate-600">
          [Skeleton - Task 3.2] Xác thực Admin & Chủ Quán qua httpOnly Cookie JWT (`SameSite=Lax`).
        </p>
      </div>
    </div>
  );
}
