import React, { useEffect, useState } from "react";
import { FiBell, FiClipboard, FiUserCheck } from "react-icons/fi";
import { Link } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import { parseApiDate } from "../../admin-dashboard/utils/vietnamTime.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";

const filters = [
  { value: "all", label: "Tất cả" },
  { value: "unread", label: "Chưa đọc" },
  { value: "read", label: "Đã đọc" },
];
const dateFormat = new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeZone: "Asia/Ho_Chi_Minh" });
const timeFormat = new Intl.DateTimeFormat("vi-VN", { timeStyle: "short", timeZone: "Asia/Ho_Chi_Minh" });

function groupByDate(items) {
  const today = dateFormat.format(new Date());
  const yesterday = dateFormat.format(new Date(Date.now() - 86400000));
  const groups = new Map();
  for (const item of items) {
    const date = parseApiDate(item.created_at);
    const day = date ? dateFormat.format(date) : "Không rõ ngày";
    const label = day === today ? "Hôm nay" : day === yesterday ? "Hôm qua" : day;
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push({ ...item, time: day === "Không rõ ngày" ? "" : timeFormat.format(date) });
  }
  return [...groups];
}

export default function OwnerNotificationsPage({ compact = false, onSelect }) {
  const [data, setData] = useState({ items: [], unread_count: 0, total: 0 });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [skip, setSkip] = useState(0);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    axiosClient
      .get("/owner/notifications", { params: { skip, limit: 50, is_read: filter === "all" ? undefined : filter === "read" } })
      .then(({ data: result }) => {
        if (!alive) return;
        setData((previous) => ({
          ...result,
          items: skip ? [...new Map([...previous.items, ...result.items].map((item) => [item.id, item])).values()] : result.items,
        }));
      })
      .catch((e) => {
        if (alive) setError(apiErrorMessage(e, "Không lấy được thông báo"));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [filter, skip, retry]);
  function selectFilter(next) {
    if (next === filter) return;
    setData((previous) => ({ ...previous, items: [], total: 0 }));
    setError("");
    setLoading(true);
    setSkip(0);
    setFilter(next);
  }

  return (
    <section className={compact ? "" : "rounded-xl border bg-white p-5"}>
      {!compact && <h1>Thông báo kiểm duyệt</h1>}
      <div className="owner-inbox-filters" role="group" aria-label="Lọc thông báo">
        {filters.map(({ value, label }) => (
          <button key={value} type="button" aria-pressed={filter === value}
            onClick={() => selectFilter(value)}>{label}</button>
        ))}
      </div>
      <div className={compact ? "owner-inbox-scroll" : ""}>
        {error && (
          <p role="alert" className="owner-inbox-message text-red-700">
            {error}{" "}
            <button type="button" className="underline"
              onClick={() => { setError(""); setLoading(true); setRetry((value) => value + 1); }}>
              Thử lại
            </button>
          </p>
        )}
        {!loading && !error && !data.items.length && (
          <p className="owner-inbox-message">Không có thông báo {filter === "unread" ? "chưa đọc" : filter === "read" ? "đã đọc" : "nào"}.</p>
        )}
        {groupByDate(data.items).map(([day, items]) => (
          <div key={day}>
            <h3 className="owner-inbox-date">{day}</h3>
            <ul>
              {items.map((item) => {
                const Icon = item.type === "registration_review" ? FiUserCheck :
                  item.type === "submission_review" ? FiClipboard : FiBell;
                return (
                  <li key={item.id}>
                    <Link to={"/owner/notifications/" + item.id} onClick={onSelect}
                      className="owner-inbox-entry" data-unread={!item.is_read}>
                      <Icon className="owner-inbox-icon" size={18} aria-hidden="true" />
                      <div className="owner-inbox-copy">
                        <strong>{item.title || "Thông báo"}</strong>
                        <p>{item.message}</p>
                      </div>
                      <div className="owner-inbox-meta">
                        {!item.is_read && <span className="owner-entry-dot"><span className="sr-only">Chưa đọc</span></span>}
                        {item.time && <time dateTime={item.created_at}>{item.time}</time>}
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        {loading && <p role="status" className="owner-inbox-message">Đang tải thông báo…</p>}
        {!error && data.total > skip + 50 && (
          <button type="button" disabled={loading} className="owner-secondary m-3"
            onClick={() => { setLoading(true); setSkip((value) => value + 50); }}>
            Tải thêm thông báo
          </button>
        )}
      </div>
    </section>
  );
}
