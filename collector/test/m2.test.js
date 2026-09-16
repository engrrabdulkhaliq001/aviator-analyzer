const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { parseCompletedRounds, redactSensitive } = require('../src/parser');

test('replay parser extracts completed history and excludes active betting values', () => {
  const fixture = fs.readFileSync(path.join(__dirname, '../fixtures/sample.html'), 'utf8');
  const rounds = parseCompletedRounds(fixture, '2026-09-15T00:00:00.000Z');
  assert.deepEqual(rounds.map((r) => r.multiplier), [366.12, 13.6, 12.69, 1.13, 1.39, 2.86, 1.54, 4.76, 66.18, 1.64]);
  assert.equal(rounds.length, 10);
  assert.equal(new Set(rounds.map((r) => r.sourceRoundKey)).size, rounds.length);
});

test('replay parse is deterministic for identical snapshots', () => {
  const fixture = '<section id="completed-history"><span>1.23x</span><span>2.00x</span></section>';
  const a = parseCompletedRounds(fixture, '2026-09-15T00:00:00.000Z');
  const b = parseCompletedRounds(fixture, '2026-09-15T00:00:00.000Z');
  assert.deepEqual(a, b);
  assert.notEqual(a[0].rawFingerprint, a[1].rawFingerprint);
});

test('sensitive payload fields are redacted', () => {
  const safe = redactSensitive({ token: 'abc', nested: { authorization: 'Bearer xyz' }, value: 'ok' });
  assert.deepEqual(safe, { token: '[redacted]', nested: { authorization: '[redacted]' }, value: 'ok' });
});
