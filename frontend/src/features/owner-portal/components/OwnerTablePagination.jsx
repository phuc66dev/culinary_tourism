import React from "react";
import { FiChevronLeft, FiChevronRight } from "react-icons/fi";

function pagination(current, total) {
  const pages = [...new Set([1, current - 1, current, current + 1, total])]
    .filter((page) => page >= 1 && page <= total).sort((a, b) => a - b);
  return pages.flatMap((page, index) => index && page - pages[index - 1] > 1 ? ["gap-" + page, page] : [page]);
}

export default function OwnerTablePagination({ current, pageCount, onPageChange, label, summary, busy }) {
  return (
      <footer className="owner-menu-pagination">
        <span>{summary}</span>
        <nav aria-label={label}>
          <button type="button" aria-label="Trang trước" disabled={busy || current === 1} onClick={() => onPageChange(current - 1)}>
            <FiChevronLeft size={15} aria-hidden="true" />
          </button>
          {pagination(current, pageCount).map((entry) => typeof entry === "number" ? (
            <button type="button" key={entry} aria-label={"Trang " + entry} aria-current={current === entry ? "page" : undefined}
              disabled={busy} onClick={() => onPageChange(entry)}>{entry}</button>
          ) : <span key={entry} aria-hidden="true">…</span>)}
          <button type="button" aria-label="Trang sau" disabled={busy || current === pageCount} onClick={() => onPageChange(current + 1)}>
            <FiChevronRight size={15} aria-hidden="true" />
          </button>
        </nav>
      </footer>
  );
}
