import React, { useMemo } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  makeInteractionCsv, selectInteractionRows, summarizeInteractionRows,
  toNumber,
} from "./interactionReport.js";

const nf = new Intl.NumberFormat("vi-VN");
const number = (value) => nf.format(toNumber(value));
const formatDate = (date) => date ? `${date.slice(8, 10)}/${date.slice(5, 7)}/${date.slice(0, 4)}` : "—";

function downloadCsv(rows, range) {
  const fileName = `tuong-tac-quan4-${range?.from || rows.at(-1)?.date || "all"}-${range?.to || rows[0]?.date || "all"}.csv`;
  const blob = new Blob(["\ufeff", makeInteractionCsv(rows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  // Allow the browser to start the download before revoking the object URL.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function AdminInteractionDetails({ daily = [], days, range, onClose }) {
  const rows = useMemo(() => selectInteractionRows(daily, range), [daily, range]);
  const totals = useMemo(() => summarizeInteractionRows(rows), [rows]);
  const title = range
    ? `${formatDate(range.from)} – ${formatDate(range.to)}`
    : `${days} ngày gần nhất`;

  return (
    <Dialog.Root open onOpenChange={(open) => { if (!open) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="ops-detail-overlay" />
        <Dialog.Content className="ops-detail-dialog">
          <header className="ops-detail-header">
            <div>
              <Dialog.Title className="ops-detail-title">Chi tiết tương tác theo kỳ</Dialog.Title>
              <Dialog.Description className="ops-detail-subtitle">
                {title} · {number(rows.length)} ngày · Giờ Việt Nam (UTC+7)
              </Dialog.Description>
            </div>
            <Dialog.Close type="button" className="ops-detail-close" aria-label="Đóng bảng chi tiết">×</Dialog.Close>
          </header>
          <div className="ops-detail-content">
            <div className="ops-detail-summary">
              <div><span>Xem chi tiết quán</span><strong>{number(totals.views)}</strong></div>
              <div><span>Chọn từ tìm kiếm</span><strong>{number(totals.search_selections)}</strong></div>
              <div><span>Bắt đầu nghe</span><strong>{number(totals.audio_starts)}</strong></div>
              <div><span>Nghe hoàn tất</span><strong>{number(totals.audio_completions)}</strong></div>
            </div>
            <div className="ops-detail-toolbar">
              <div>
                <h3>Thống kê từng ngày</h3>
                <p>{number(totals.total_events)} sự kiện được ghi nhận trong khoảng đã chọn</p>
              </div>
              <button type="button" className="ops-detail-export" disabled={!rows.length} onClick={() => downloadCsv(rows, range)}>
                Xuất CSV
              </button>
            </div>
            <div className="ops-detail-table-wrap">
              <table className="ops-detail-table">
                <thead>
                  <tr>
                    <th scope="col">Ngày</th>
                    <th scope="col">Xem quán</th>
                    <th scope="col">Chọn tìm kiếm</th>
                    <th scope="col">Bắt đầu nghe</th>
                    <th scope="col">Nghe hoàn tất</th>
                    <th scope="col">Tổng sự kiện</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const total = toNumber(row.views) + toNumber(row.search_selections) + toNumber(row.audio_starts) + toNumber(row.audio_completions);
                    return (
                      <tr key={row.date}>
                        <th scope="row">{formatDate(row.date)}</th>
                        <td>{number(row.views)}</td>
                        <td>{number(row.search_selections)}</td>
                        <td>{number(row.audio_starts)}</td>
                        <td>{number(row.audio_completions)}</td>
                        <td className="ops-detail-total">{number(total)}</td>
                      </tr>
                    );
                  })}
                  {!rows.length && <tr><td colSpan={6} className="ops-detail-empty">Không có dữ liệu trong khoảng được chọn.</td></tr>}
                </tbody>
                {rows.length > 0 && <tfoot>
                  <tr>
                    <th scope="row">Tổng cộng</th>
                    <td>{number(totals.views)}</td>
                    <td>{number(totals.search_selections)}</td>
                    <td>{number(totals.audio_starts)}</td>
                    <td>{number(totals.audio_completions)}</td>
                    <td>{number(totals.total_events)}</td>
                  </tr>
                </tfoot>}
              </table>
            </div>
            <p className="ops-detail-note">
              Đây là <strong>số sự kiện</strong>, không phải số người dùng duy nhất. Dữ liệu QA vẫn được tính nếu chưa dọn khỏi MongoDB; số lượt hoàn tất không phải tỷ lệ hoàn tất theo phiên nghe.
            </p>
          </div>
          <footer className="ops-detail-footer">
            <button type="button" className="ops-detail-done" onClick={onClose}>Đóng</button>
          </footer>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
