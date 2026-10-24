import React from 'react';

/**
 * OwnerPOIPage — Quản lý thông tin quán, Thực đơn (`MenuItem`) & Nút gọi Trợ lý AI (Gemini 2.5 Flash).
 * Phụ trách: Phúc (Task 2.5, Task 2.6, Task 2.10)
 */
export default function OwnerPOIPage() {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-bold">Quản lý Quán Ăn & Thực Đơn</h2>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 2.5 & 2.10] CRUD món ăn, tích hợp AI Advisor viết mô tả 200-300 từ (tối đa 10 lượt/ngày).
      </p>
    </div>
  );
}
