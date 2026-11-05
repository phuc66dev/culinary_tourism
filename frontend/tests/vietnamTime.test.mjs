import test from 'node:test';
import assert from 'node:assert/strict';
import { parseApiDate, vietnamDateParts, formatVietnamDateTime, vietnamLocalToUtcIso } from '../src/features/admin-dashboard/utils/vietnamTime.js';

test('naive Mongo UTC 12:59 displays 19:59 in Vietnam', () => {
  const values = [
    '2026-10-29T12:59:00',
    '2026-10-29T12:59:00Z',
    '2026-10-29T12:59:00+00:00',
    '2026-10-29T19:59:00+07:00',
  ];
  for (const value of values) {
    assert.deepEqual(vietnamDateParts(value), { time: '19:59:00', day: '29/10/2026' });
    assert.equal(formatVietnamDateTime(value), '19:59:00 29/10/2026');
  }
});

test('time works across midnight, no double 7-hour shift', () => {
  assert.deepEqual(vietnamDateParts('2026-10-29T18:30:00Z'), {time:'01:30:00', day:'30/10/2026'});
  assert.equal(parseApiDate('2026-10-29T19:59:00+07:00').toISOString(), '2026-10-29T12:59:00.000Z');
});

test('audit time filters are interpreted in Vietnam even on a UTC browser', () => {
  assert.equal(vietnamLocalToUtcIso('2026-10-29T19:59'), '2026-10-29T12:59:00.000Z');
  assert.equal(vietnamLocalToUtcIso('2026-10-30T01:30:00'), '2026-10-29T18:30:00.000Z');
  assert.equal(vietnamLocalToUtcIso(''), undefined);
  assert.equal(vietnamLocalToUtcIso('bad-date'), undefined);
  assert.equal(formatVietnamDateTime(null), '—');
});
