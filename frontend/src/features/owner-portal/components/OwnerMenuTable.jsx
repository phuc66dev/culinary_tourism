import React, { useEffect, useRef, useState } from "react";
import {
  FiArrowDown, FiArrowUp, 
  FiEdit2, FiImage, FiSearch, FiTrash2,
} from "react-icons/fi";
import { LuChevronsUpDown } from "react-icons/lu";
import OwnerTablePagination from "./OwnerTablePagination.jsx";
import { assetUrl } from "../../admin-dashboard/utils/assetUrl.js";

const sizes = [10, 15, 25, 50];
const collator = new Intl.Collator("vi", { numeric: true, sensitivity: "base" });
const money = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" });
const sortable = [
  { key: "name", label: "Tên món" },
  { key: "price_vnd", label: "Giá tiền" },
  { key: "tags", label: "Nhãn" },
];

function searchable(value) {
  return String(value ?? "").toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").replaceAll("đ", "d");
}

export default function OwnerMenuTable({ items, shopName, busy, loading, error, onEdit, onDelete }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: "name", ascending: true });
  const [pageSize, setPageSize] = useState(15);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(new Set());
  const selectPage = useRef(null);
  const term = searchable(query.trim());
  const results = items.filter((item) =>
    [item.name, item.price_vnd, money.format(item.price_vnd ?? 0), ...(item.tags || [])]
      .some((value) => searchable(value).includes(term)),
  ).sort((a, b) => {
    let order;
    if (sort.key === "price_vnd") order = (a.price_vnd ?? 0) - (b.price_vnd ?? 0);
    else if (sort.key === "tags") order = collator.compare((a.tags || []).join(", "), (b.tags || []).join(", "));
    else order = collator.compare(a.name ?? "", b.name ?? "");
    return (sort.ascending ? order : -order) || collator.compare(a.name ?? "", b.name ?? "") || a.id.localeCompare(b.id);
  });
  const pageCount = Math.max(1, Math.ceil(results.length / pageSize));
  const current = Math.min(page, pageCount);
  const offset = (current - 1) * pageSize;
  const rows = results.slice(offset, offset + pageSize);
  const chosen = items.filter((item) => selected.has(item.id));
  const pageSelected = rows.filter((item) => selected.has(item.id)).length;
  const allChecked = rows.length > 0 && pageSelected === rows.length;
  const partial = pageSelected > 0 && !allChecked;

  useEffect(() => {
    if (selectPage.current) selectPage.current.indeterminate = partial;
  }, [partial]);

  useEffect(() => {
    setPage((value) => Math.min(value, pageCount));
  }, [pageCount]);

  function updateSelection(records, checked) {
    setSelected((previous) => {
      const next = new Set(previous);
      for (const item of records) {
        if (checked) next.add(item.id);
        else next.delete(item.id);
      }
      return next;
    });
  }

  function changeSort(key) {
    setSort((previous) => ({ key, ascending: previous.key === key ? !previous.ascending : true }));
    setPage(1);
  }

  return (
    <div className="owner-menu-data">
      <div className="owner-menu-toolbar">
        <div className="owner-menu-tools">
          <div className="owner-menu-search-actions">
            <label className="owner-menu-search">
              <FiSearch aria-hidden="true" size={16} />
              <input type="search" aria-label="Tìm trong thực đơn" placeholder="Tìm tên món, giá hoặc nhãn"
                value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} />
            </label>
            {chosen.length > 0 && (
              <button type="button" className="owner-menu-bulk-delete" disabled={busy} onClick={() => onDelete(chosen)}>
                <FiTrash2 aria-hidden="true" /> Xóa đã chọn ({chosen.length})
              </button>
            )}
          </div>
          {chosen.length > 0 && (
            <button type="button" className="owner-secondary" disabled={busy} onClick={() => setSelected(new Set())}>
              Bỏ chọn
            </button>
          )}
        </div>
        <div className="owner-menu-count">
          <label>Hiển thị <select aria-label="Số món mỗi trang" value={pageSize} onChange={(event) => {
            setPageSize(Number(event.target.value));
            setPage(1);
          }}>
            {sizes.map((size) => <option key={size}>{size}</option>)}
          </select> món mỗi trang</label>
          <span aria-live="polite">{results.length} món{term ? " / " + items.length + " tổng số" : ""}</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="owner-menu-table">
          <caption className="sr-only">Danh sách món ăn của {shopName}</caption>
          <colgroup><col className="owner-menu-select-col" /><col className="owner-menu-image-col" />
            <col className="owner-menu-name-col" /><col className="owner-menu-price-col" /><col /><col className="owner-menu-actions-col" /></colgroup>
          <thead><tr>
            <th scope="col">
              <input ref={selectPage} type="checkbox" aria-label="Chọn tất cả món trên trang này"
                checked={allChecked} disabled={busy || !rows.length} onChange={(event) => updateSelection(rows, event.target.checked)} />
            </th>
            <th scope="col">Hình ảnh</th>
            {sortable.map(({ key, label }) => {
              const active = sort.key === key;
              const Icon = !active ? LuChevronsUpDown : sort.ascending ? FiArrowUp : FiArrowDown;
              return (
                <th key={key} scope="col" aria-sort={active ? (sort.ascending ? "ascending" : "descending") : undefined}>
                  <button type="button" onClick={() => changeSort(key)} className="owner-menu-sort">
                    {label} <Icon size={12} aria-hidden="true" />
                  </button>
                </th>
              );
            })}
            <th scope="col">Hành động</th>
          </tr></thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id} data-selected={selected.has(item.id)}>
                <td><input type="checkbox" aria-label={"Chọn " + item.name} checked={selected.has(item.id)}
                  disabled={busy} onChange={(event) => updateSelection([item], event.target.checked)} /></td>
                <td><div className="owner-menu-image">
                  {item.image_url ? <img src={assetUrl(item.image_url)} alt="" loading="lazy" /> : <FiImage aria-hidden="true" size={18} />}
                  {item.image_urls?.length > 1 && <span aria-label={item.image_urls.length + " ảnh"}>{item.image_urls.length}</span>}
                </div></td>
                <td className="font-semibold">{item.name}</td>
                <td className="whitespace-nowrap tabular-nums">{money.format(item.price_vnd ?? 0)}</td>
                <td>{item.tags?.length ? (
                  <ul className="flex flex-wrap gap-1">
                    {item.tags.map((tag) => <li key={tag} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-800">{tag}</li>)}
                  </ul>
                ) : <span className="text-slate-500">—</span>}</td>
                <td><div className="flex gap-1">
                  <button type="button" title="Sửa" aria-label={"Sửa " + item.name} disabled={busy}
                    onClick={() => onEdit(item)} className="owner-header-action owner-menu-edit"><FiEdit2 aria-hidden="true" size={16} /></button>
                  <button type="button" title="Xóa" aria-label={"Xóa " + item.name} disabled={busy}
                    onClick={() => onDelete([item])} className="owner-header-action owner-menu-delete"><FiTrash2 aria-hidden="true" size={16} /></button>
                </div></td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={6} className="owner-menu-empty">
              {loading ? "Đang tải thực đơn…" : error ? "Không tải được danh sách món." :
                term ? "Không tìm thấy món phù hợp." : "Chưa có món ăn trong thực đơn."}
            </td></tr>}
          </tbody>
        </table>
      </div>
      <OwnerTablePagination current={current} pageCount={pageCount} onPageChange={setPage}
        label="Phân trang thực đơn" summary={(results.length ? offset + 1 : 0) + "–" + (offset + rows.length) + " trên " + results.length + " món"} />
    </div>
  );
}
