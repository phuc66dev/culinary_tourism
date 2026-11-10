/**
 * Client-side drill-down for Admin's already-authorized aggregate report.
 * No individual visitor/session data is requested or exposed.
 */
export const INTERACTION_METRICS = [
  "views", "search_selections", "audio_starts", "audio_completions",
];

export const toNumber = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;

export function summarizeInteractionRows(rows = []) {
  const summary = Object.fromEntries(INTERACTION_METRICS.map((key) => [key, 0]));
  summary.listen_seconds = 0;
  for (const row of rows) {
    for (const key of INTERACTION_METRICS) summary[key] += toNumber(row[key]);
    summary.listen_seconds += toNumber(row.listen_seconds);
  }
  summary.total_events = INTERACTION_METRICS.reduce((sum, key) => sum + summary[key], 0);
  return summary;
}

/** Date strings are in YYYY-MM-DD format and use Asia/Ho_Chi_Minh days. */
export function selectInteractionRows(daily = [], range = null) {
  return daily
    .filter((row) => row && typeof row.date === "string" && (!range || (
      row.date >= range.from && row.date <= range.to
    )))
    .sort((a, b) => b.date.localeCompare(a.date));
}

export function makeInteractionBuckets(daily = [], days = 30) {
  const bucketSize = days === 7 ? 1 : days === 30 ? 7 : 14;
  const sorted = [...daily].sort((a, b) => a.date.localeCompare(b.date));
  const result = [];
  for (let i = 0; i < sorted.length; i += bucketSize) {
    const items = sorted.slice(i, i + bucketSize);
    if (!items.length) continue;
    const first = items[0].date;
    const last = items[items.length - 1].date;
    const label = (date) => `${date.slice(8, 10)}/${date.slice(5, 7)}`;
    const totals = summarizeInteractionRows(items);
    result.push({
      period: first === last ? label(first) : `${label(first)}–${label(last)}`,
      from: first,
      to: last,
      ...totals,
    });
  }
  return result;
}

/** Semicolon-delimited UTF-8 CSV for Vietnamese Excel; only dates and numbers. */
export function makeInteractionCsv(rows = []) {
  const header = ["Ngày", "Xem chi tiết", "Chọn từ tìm kiếm", "Bắt đầu nghe", "Nghe hoàn tất", "Tổng sự kiện", "Thời lượng nghe (giây)"];
  const lines = rows.map((row) => {
    const total = INTERACTION_METRICS.reduce((sum, key) => sum + toNumber(row[key]), 0);
    // A date must be ISO YYYY-MM-DD; never allow untrusted CSV formulas.
    const safeDate = /^\d{4}-\d{2}-\d{2}$/.test(row.date) ? row.date : "";
    return [safeDate, ...INTERACTION_METRICS.map((key) => toNumber(row[key])), total, toNumber(row.listen_seconds)].join(";");
  });
  return [header.join(";"), ...lines].join("\r\n") + "\r\n";
}
