import React from 'react';

/**
 * SplashScreen — Màn hình chào mừng & Chọn nhanh 5 ngôn ngữ ưu tiên (`vi`, `en`, `zh`, `ja`, `ko`).
 * Phụ trách: Bảo (Task 1.1)
 */
export default function SplashScreen({ onComplete }) {
  const languages = [
    { code: 'vi', label: 'Tiếng Việt' },
    { code: 'en', label: 'English' },
    { code: 'zh', label: '中文' },
    { code: 'ja', label: '日本語' },
    { code: 'ko', label: '한국어' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-orange-600 p-6 text-white">
      <h1 className="mb-2 text-2xl font-bold">Ẩm Thực Quận 4</h1>
      <p className="mb-6 text-center text-sm opacity-90">
        Pocket Audio Tour Guide — Chọn ngôn ngữ thuyết minh của bạn
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        {languages.map((lang) => (
          <button
            key={lang.code}
            onClick={() => onComplete?.(lang.code)}
            className="rounded-xl bg-white px-4 py-2 font-semibold text-orange-700 shadow"
          >
            {lang.label}
          </button>
        ))}
      </div>
    </div>
  );
}
