import React from 'react';

const paths = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  pin: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  audio: <><rect x="4" y="9" width="3" height="6" rx="1"/><rect x="10" y="4" width="3" height="16" rx="1"/><rect x="16" y="7" width="3" height="10" rx="1"/></>,
  registrations: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 10.7-3.7M16 18l2 2 4-4"/></>,
  submissions: <><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/></>,
  users: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M17 14a6 6 0 0 1 4 6"/></>,
  shield: <><path d="M12 2 20 6v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4Z"/><path d="m9 12 2 2 4-4"/></>,
  history: <><path d="M3 12a9 9 0 1 0 2.8-6.5M3 4v4h4"/><path d="M12 7v5l3 2"/></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
  close: <><path d="M5 5 19 19M19 5 5 19"/></>,
  logout: <><path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4M13 7l5 5-5 5M8 12h10"/></>,
  chevron: <><path d="m9 18 6-6-6-6"/></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.4 9A7 7 0 0 1 19 8l1 4M4 12l1 4a7 7 0 0 0 12.5-.9"/></>,
  arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
  check: <><path d="m4 12 5 5L20 6"/></>,
  alert: <><path d="M12 3 2 21h20L12 3ZM12 9v5m0 3h.01"/></>,
};

export default function AdminIcon({ name, size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>
      {paths[name] || paths.dashboard}
    </svg>
  );
}
