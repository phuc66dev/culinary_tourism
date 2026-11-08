/**
 * MongoDB/PyMongo stores UTC datetimes but may serialize them without an offset.
 * Assume UTC ONLY for an ISO date-time without zone information. Dates with an
 * explicit Z/+07:00/etc. keep their original instant. Never add 7 hours twice.
 */
const OFFSETLESS_ISO_DATE_TIME = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/;
const VIETNAM_TIME_ZONE = 'Asia/Ho_Chi_Minh';

export function parseApiDate(value) {
  if (!value) return null;
  const input = value instanceof Date ? value : String(value).trim();
  const normalized = typeof input === 'string' && OFFSETLESS_ISO_DATE_TIME.test(input)
    ? `${input.replace(' ', 'T')}Z`
    : input;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function vietnamDateParts(value) {
  const date = parseApiDate(value);
  if (!date) return { time: '—', day: '' };
  return {
    time: date.toLocaleTimeString('vi-VN', {
      timeZone: VIETNAM_TIME_ZONE, hour12: false, hourCycle: 'h23',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }),
    day: date.toLocaleDateString('vi-VN', {
      timeZone: VIETNAM_TIME_ZONE, day: '2-digit', month: '2-digit', year: 'numeric',
    }),
  };
}

export function formatVietnamDateTime(value) {
  const date = parseApiDate(value);
  if (!date) return '—';
  const { time, day } = vietnamDateParts(date);
  return `${time} ${day}`;
}

/** A datetime-local input represents Vietnam wall-clock time, not browser TZ. */
export function vietnamLocalToUtcIso(value) {
  if (!value) return undefined;
  const text = String(value).trim();
  const match = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(text);
  if (!match) return undefined;
  const date = new Date(`${text}${text.length === 16 ? ':00' : ''}+07:00`);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}
