import React, { useEffect, useState } from "react";
import { FiArrowDown, FiArrowUp, FiEye, FiSearch } from "react-icons/fi";
import { LuChevronsUpDown } from "react-icons/lu";
import axiosClient from "../../../api/axiosClient.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";
import { formatVietnamDateTime } from "../../admin-dashboard/utils/vietnamTime.js";
import OwnerDialog from "../components/OwnerDialog.jsx";
import OwnerTablePagination from "../components/OwnerTablePagination.jsx";

const states = {
  pending: { label: "Chờ duyệt", tone: "bg-amber-100 text-amber-900" },
  approved: { label: "Đã chấp thuận", tone: "bg-emerald-100 text-emerald-900" },
  rejected: { label: "Bị từ chối", tone: "bg-red-100 text-red-900" },
};
const filters = [{ key: "", label: "Tất cả" }, ...Object.entries(states).map(([key, state]) => ({ key, label: state.label }))];
const fieldNames = {
  name: "Tên quán",
  address: "Địa chỉ",
  ward: "Phường",
  category: "Loại hình",
  original_description: "Mô tả",
  images: "Ảnh quán",
  location: "Tọa độ",
};
const dateColumns = [
  { key: "created_at", label: "Ngày gửi" },
  { key: "reviewed_at", label: "Ngày xét duyệt" },
];

function shopName(item) {
  return item.poi_name || item.proposed_changes?.name || "Địa điểm của bạn";
}

function Status({ value }) {
  const state = states[value] || { label: "Chưa xác định", tone: "bg-slate-100 text-slate-700" };
  return <span className={"inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold " + state.tone}>{state.label}</span>;
}

function formatValue(value) {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.join("\n") || "—";
  if (Array.isArray(value?.coordinates)) return value.coordinates.join(", ");
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export default function OwnerSubmissionsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [filter, setFilter] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [sort, setSort] = useState({ key: "created_at", order: "desc" });
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      axiosClient.get("/owner/submissions", {
        signal: controller.signal,
        params: {
          limit: pageSize, skip: (page - 1) * pageSize, review_status: filter || undefined,
          q: query.trim() || undefined, sort_by: sort.key, order: sort.order,
        },
      }).then(({ data: result }) => {
        if (controller.signal.aborted) return;
        const lastPage = Math.max(1, Math.ceil(result.total / pageSize));
        if (page > lastPage) setPage(lastPage);
        else setData(result);
      }).catch((err) => {
        if (!controller.signal.aborted) setError(apiErrorMessage(err, "Không tải được đề xuất"));
      }).finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [filter, query, page, pageSize, sort, retry]);

  const total = data?.total ?? 0;
  const rows = loading || error ? [] : data?.items || [];
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const offset = (page - 1) * pageSize;

  function sortBy(key) {
    setSort((previous) => ({ key, order: previous.key === key && previous.order === "desc" ? "asc" : "desc" }));
    setPage(1);
  }

  return (
    <div className="space-y-5">
      <header className="admin-dashboard-heading">
        <div>
          <p className="admin-eyebrow">Quản lý quán</p>
          <h1>Đề xuất cập nhật</h1>
          <p>Theo dõi tiến độ xét duyệt các thay đổi thông tin quán.</p>
        </div>
      </header>
      <section aria-label="Danh sách đề xuất" className="rounded-xl border bg-white p-4 sm:p-5">
        <div className="owner-menu-data owner-submissions-data">
          <div className="owner-submission-filters" role="group" aria-label="Lọc theo trạng thái">
            {filters.map(({ key, label }) => (
              <button key={key} type="button" aria-pressed={filter === key}
                onClick={() => { setFilter(key); setPage(1); }}>
                {label}
                {key && !loading && !error && <span>{data?.counts?.[key] ?? 0}</span>}
              </button>
            ))}
          </div>
          <div className="owner-menu-toolbar">
            <label className="owner-menu-search">
              <FiSearch aria-hidden="true" size={16} />
              <input type="search" aria-label="Tìm theo tên quán" placeholder="Tìm theo tên quán" maxLength={120}
                value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} />
            </label>
            <div className="owner-menu-count">
              <label>Hiển thị <select value={pageSize} aria-label="Số đề xuất mỗi trang"
                onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }}>
                {[10, 15, 25, 50].map((size) => <option key={size}>{size}</option>)}
              </select> đề xuất mỗi trang</label>
              <span aria-live="polite">{loading || error ? "—" : total} kết quả</span>
            </div>
          </div>
          <div className="overflow-x-auto" aria-busy={loading}>
            <table className="owner-menu-table owner-submissions-table">
              <caption className="sr-only">Đề xuất cập nhật của chủ quán</caption>
              <colgroup><col /><col /><col /><col /><col /><col /></colgroup>
              <thead><tr>
                <th scope="col">Quán</th>
                <th scope="col">Nội dung thay đổi</th>
                <th scope="col">Trạng thái</th>
                {dateColumns.map(({ key, label }) => {
                  const active = sort.key === key;
                  const Icon = !active ? LuChevronsUpDown : sort.order === "asc" ? FiArrowUp : FiArrowDown;
                  return <th key={key} scope="col" aria-sort={active ? (sort.order === "asc" ? "ascending" : "descending") : undefined}>
                    <button type="button" className="owner-menu-sort" onClick={() => sortBy(key)}>
                      {label} <Icon size={12} aria-hidden="true" />
                    </button>
                  </th>;
                })}
                <th scope="col">Chi tiết</th>
              </tr></thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.id}>
                    <td className="font-semibold">{shopName(item)}</td>
                    <td>{Object.keys(item.proposed_changes || {}).map((key) => fieldNames[key] || key).join(", ") || "—"}</td>
                    <td><Status value={item.status} /></td>
                    <td className="tabular-nums">{formatVietnamDateTime(item.created_at)}</td>
                    <td className="tabular-nums">{formatVietnamDateTime(item.reviewed_at)}</td>
                    <td><button type="button" className="owner-header-action owner-menu-edit" title="Xem chi tiết"
                      aria-label={"Xem đề xuất của " + shopName(item) + ", gửi " + formatVietnamDateTime(item.created_at)}
                      onClick={() => setDetail(item)}><FiEye size={17} aria-hidden="true" /></button></td>
                  </tr>
                ))}
                {!rows.length && <tr><td colSpan={6} className="owner-menu-empty">
                  {loading ? <span role="status">Đang tải đề xuất…</span> : error ? (
                    <span role="alert">{error} <button type="button" className="ml-1 underline" onClick={() => setRetry((value) => value + 1)}>Thử lại</button></span>
                  ) : filter || query.trim() ? "Không có đề xuất phù hợp." : "Chưa có đề xuất cập nhật."}
                </td></tr>}
              </tbody>
            </table>
          </div>
          <OwnerTablePagination current={Math.min(page, pageCount)} pageCount={pageCount} busy={loading || !!error}
            onPageChange={setPage} label="Phân trang đề xuất"
            summary={loading || error ? "—" : (rows.length ? offset + 1 : 0) + "–" + (offset + rows.length) + " trên " + total + " đề xuất"} />
        </div>
      </section>
      <OwnerDialog open={!!detail} onClose={() => setDetail(null)} title="Chi tiết đề xuất"
        description={detail ? shopName(detail) : ""}>
        {detail && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Status value={detail.status} />
              <span>Gửi lúc {formatVietnamDateTime(detail.created_at)}</span>
              {detail.reviewed_at && <span>Duyệt lúc {formatVietnamDateTime(detail.reviewed_at)}</span>}
            </div>
            <dl className="divide-y rounded-lg border border-slate-200">
              {Object.entries(detail.proposed_changes || {}).map(([key, value]) => (
                <div key={key} className="grid gap-1 p-3 sm:grid-cols-[130px_minmax(0,1fr)]">
                  <dt className="text-sm font-semibold text-slate-700">{fieldNames[key] || key}</dt>
                  <dd className="whitespace-pre-wrap break-words text-sm">{formatValue(value)}</dd>
                </div>
              ))}
            </dl>
            {detail.admin_note && <section className="rounded-lg bg-slate-50 p-3">
              <h3 className="text-sm font-semibold">Ghi chú xét duyệt</h3>
              <p className="mt-1 whitespace-pre-wrap break-words text-sm">{detail.admin_note}</p>
            </section>}
          </div>
        )}
      </OwnerDialog>
    </div>
  );
}
