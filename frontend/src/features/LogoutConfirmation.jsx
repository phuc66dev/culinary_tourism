import React from "react";
import OwnerDialog from "./owner-portal/components/OwnerDialog.jsx";
import "./owner-portal/owner.css";

function LogoutIllustration() {
  return (
    <svg className="logout-illustration" viewBox="0 0 210 160" aria-hidden="true" fill="none">
      <ellipse cx="102" cy="140" rx="86" ry="14" fill="#EDF3FC" />
      <path d="M65 140V32a6 6 0 0 1 6-6h66a6 6 0 0 1 6 6v108" fill="#DCE9FB" />
      <path d="M74 140V35h60v105" fill="#172C47" />
      <path d="M75 35 119 18v125L75 137z" fill="#2B588D" />
      <path d="m84 47 25-8v31l-25 5zm0 39 25-4v40l-25-3z" stroke="#80A5D1" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="111" cy="78" r="3" fill="#EDF3FC" />
      <circle cx="155" cy="76" r="24" fill="#EAF2FF" stroke="#C4D8F7" />
      <path d="M144 76h22m-9-8 9 8-9 8" stroke="#215DC4" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M48 124c-1-13 6-22 18-24-3 12-9 20-18 24Zm-2 1c0-13-8-21-19-23 2 12 9 20 19 23Z" fill="#5B809F" />
      <path d="M38 125h19l-4 15H42z" fill="#27496A" />
      <path d="M174 111v10m-5-5h10m-20-82v8m-4-4h8" stroke="#9CB9E2" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function LogoutConfirmation({ open, busy, onClose, onConfirm }) {
  return (
    <OwnerDialog open={open} busy={busy} onClose={onClose} className="logout-dialog"
      title="Bạn muốn đăng xuất?" illustration={<LogoutIllustration />}
      description="Bạn có thể đăng nhập lại bất cứ lúc nào để tiếp tục công việc."
      footer={
        <>
          <button type="button" className="owner-secondary" disabled={busy} onClick={onClose}>Hủy</button>
          <button type="button" className="admin-button-primary disabled:opacity-60" disabled={busy} onClick={onConfirm}>
            {busy ? "Đang đăng xuất…" : "Đăng xuất"}
          </button>
        </>
      } />
  );
}
