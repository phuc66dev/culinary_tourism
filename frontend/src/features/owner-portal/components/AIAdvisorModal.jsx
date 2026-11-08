import toast from 'react-hot-toast';
import OwnerDialog from './OwnerDialog.jsx';
import React, { useEffect, useState } from "react";
import axiosClient from "../../../api/axiosClient.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";

const fieldClass =
  "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-orange-600 focus:ring-2 focus:ring-orange-100";

export default function AIAdvisorModal({ poi, onClose, onInsert }) {
  const [usage, setUsage] = useState(null);
  const [keywords, setKeywords] = useState("");
  const [rawNotes, setRawNotes] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    axiosClient
      .get("/ai/usage")
      .then(({ data }) => {
        if (alive) setUsage(data);
      })
      .catch((err) => {
        if (alive) setError(apiErrorMessage(err, "Không tải được hạn mức AI"));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => { alive = false; };
  }, []);

  async function generate(event) {
    event.preventDefault();
    const list = keywords
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (!list.length) {
      setError("Nhập ít nhất một từ khóa để tạo mô tả.");
      return;
    }
    if (list.length > 12) {
      setError("Tối đa 12 từ khóa mỗi lần tạo.");
      return;
    }
    setError("");
    setDescription("");
    setGenerating(true);
    setCopied(false);
    try {
      const { data } = await axiosClient.post("/ai/enhance-description", {
        poi_id: poi.id,
        poi_name: poi.name,
        keywords: list,
        raw_notes: rawNotes.trim(),
      });
      setDescription(data.enhanced_description || "");
      setUsage(data.usage || null);
    } catch (err) {
      setError(apiErrorMessage(err, "Không tạo được mô tả. Vui lòng thử lại."));
    } finally {
      setGenerating(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(description);
      setCopied(true);
      toast.success("Đã sao chép mô tả.");
    } catch {
      setError(
        "Trình duyệt không cho phép sao chép tự động. Hãy chọn và sao chép nội dung.",
      );
    }
  }

  return (
    <OwnerDialog open onClose={onClose} busy={generating} title="Viết gợi ý giới thiệu quán" description={poi.name}>
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg bg-amber-50 px-4 py-3 text-sm">
            <span className="font-medium text-slate-700">
              Lượt dùng hôm nay
            </span>
            <span className="font-bold text-orange-900">
              {loading
                ? "Đang tải…"
                : usage
                  ? usage.used_today +
                    "/" +
                    usage.daily_limit +
                    " · còn " +
                    usage.remaining
                  : "Không khả dụng"}
            </span>
          </div>
          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
            >
              {error}
            </div>
          )}
          <form onSubmit={generate} className="space-y-4">
            <label className="block text-sm font-semibold text-slate-700">
              Từ khóa{" "}
              <span className="font-normal text-slate-500">
                (phân cách bằng dấu phẩy, tối đa 12)
              </span>
              <input
                className={fieldClass}
                value={keywords}
                onChange={(event) => setKeywords(event.target.value)}
                maxLength={500}
                placeholder="món gia truyền, vị đậm đà, không gian thân thiện"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Ghi chú thực tế về quán{" "}
              <span className="font-normal text-slate-500">
                (không bắt buộc)
              </span>
              <textarea
                className={fieldClass + " resize-y"}
                rows="3"
                maxLength={2000}
                value={rawNotes}
                onChange={(event) => setRawNotes(event.target.value)}
                placeholder="Nguyên liệu, cách chế biến, câu chuyện do quán cung cấp…"
              />
            </label>
            <p className="text-xs leading-5 text-slate-500">
              AI chỉ nên dùng các thông tin bạn cung cấp. Hãy đọc lại mô tả và
              sửa mọi chi tiết chưa chính xác trước khi gửi.
            </p>
            <button
              type="submit"
              disabled={loading || generating || !usage?.remaining}
              className="w-full rounded-lg bg-orange-700 px-4 py-3 text-sm font-semibold text-white hover:bg-orange-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generating
                ? "Đang tạo mô tả…"
                : !usage?.remaining && !loading
                  ? "Đã hết lượt hôm nay"
                  : "Tạo mô tả tiếng Việt"}
            </button>
          </form>
          {description && (
            <section
              aria-live="polite"
              className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-bold text-slate-900">Mô tả gợi ý</h3>
                <button
                  type="button"
                  onClick={copy}
                  className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
                >
                  {copied ? "Đã sao chép" : "Sao chép"}
                </button>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {description}
              </p>
              <button
                type="button"
                onClick={() => onInsert(description)}
                className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
              >
                Chèn vào đề xuất quán
              </button>
            </section>
          )}
        </div>
    </OwnerDialog>
  );
}
