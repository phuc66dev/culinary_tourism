import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { FiBell, FiX } from "react-icons/fi";
import axiosClient from "../../../api/axiosClient.js";
import OwnerNotificationsPage from "../pages/OwnerNotificationsPage.jsx";

export default function OwnerInbox({ readVersion }) {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const root = useRef(null);
  const trigger = useRef(null);
  const closeButton = useRef(null);
  const { pathname } = useLocation();

  useEffect(() => {
    let controller;
    function refreshUnread() {
      if (document.hidden) return;
      controller?.abort();
      const request = new AbortController();
      controller = request;
      axiosClient.get("/owner/notifications", { params: { limit: 1 }, signal: request.signal })
        .then(({ data }) => { if (!request.signal.aborted) setUnread(data.unread_count); })
        .catch(() => { /* Retry when the inbox opens or the window regains focus. */ });
    }
    refreshUnread();
    const timer = window.setInterval(refreshUnread, 60_000);
    window.addEventListener("focus", refreshUnread);
    return () => {
      controller?.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshUnread);
    };
  }, [open, readVersion]);

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    closeButton.current?.focus();
    function onPointerDown(event) {
      if (!root.current?.contains(event.target)) setOpen(false);
    }
    function onKeyDown(event) {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={root} className="owner-inbox">
      <button ref={trigger} type="button" className="owner-header-action owner-bell cursor-pointer"
        title="Thông báo" aria-label={unread ? "Thông báo, có thông báo chưa đọc" : "Thông báo"}
        aria-expanded={open} aria-controls={open ? "owner-inbox-panel" : undefined}
        onClick={() => setOpen((value) => !value)}>
        <FiBell size={18} aria-hidden="true" />
        {unread > 0 && <span className="owner-unread-dot" aria-hidden="true" />}
      </button>
      {open && (
        <section id="owner-inbox-panel" className="owner-inbox-panel" aria-labelledby="owner-inbox-title">
          <div className="owner-inbox-heading">
            <h2 id="owner-inbox-title">Thông báo</h2>
            <button ref={closeButton} type="button" className="owner-header-action cursor-pointer"
              aria-label="Đóng bảng thông báo" onClick={() => { setOpen(false); trigger.current?.focus(); }}>
              <FiX size={18} aria-hidden="true" />
            </button>
          </div>
          <OwnerNotificationsPage compact onSelect={() => setOpen(false)} />
        </section>
      )}
    </div>
  );
}
