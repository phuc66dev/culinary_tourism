import React from 'react';

/**
 * PublicOwnerRegisterPage — Trang đăng ký Chủ quán công khai (`/register/owner`).
 * Phụ trách: Phúc (Task 2.1)
 */
export default function PublicOwnerRegisterPage() {
  return (
    <div className="mx-auto max-w-lg p-6">
      <h1 className="text-xl font-bold text-slate-800">Đăng Ký Chủ Quán Ẩm Thực Quận 4</h1>
      <p className="mt-1 text-sm text-slate-600">
        [Skeleton - Task 2.1] Form nhập: Họ tên, SĐT, Tên quán, Địa chỉ hẻm Quận 4, Số CCCD (mã hóa Fernet), Ảnh mặt tiền.
      </p>
    </div>
  );
}
