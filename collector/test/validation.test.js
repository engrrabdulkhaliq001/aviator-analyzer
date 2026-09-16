const test = require('node:test');
const assert = require('node:assert/strict');
const { validateRounds } = require('../src/validator');

function round(id, multiplier, at, key = `r${id}`, fingerprint = `f${id}`, raw = `${multiplier.toFixed(2)}x`) { return { id, source: 'fixture', multiplier, raw_value: raw, observed_at: at, source_round_key: key, raw_fingerprint: fingerprint }; }

test('clean chronological fixture produces valid statistics', () => {
  const rows = Array.from({ length: 30 }, (_, i) => round(i + 1, 1.2 + (i % 4) * 0.2, `2026-01-01T00:${String(i).padStart(2, '0')}:00Z`));
  const report = validateRounds(rows, { minimumSamples: 30, gapThresholdSeconds: 300 });
  assert.equal(report.reliableForMl, true);
  assert.equal(report.sampleCount, 30);
  assert.equal(report.checks.duplicateSourceKeys, 0);
  assert.equal(report.summary.daily['2026-01-01'].count, 30);
});

test('duplicate keys and fingerprints are errors', () => {
  const rows = [round(1, 1.2, '2026-01-01T00:00:00Z', 'same', 'same-f'), round(2, 1.3, '2026-01-01T00:01:00Z', 'same', 'other-f'), round(3, 1.4, '2026-01-01T00:02:00Z', 'other', 'same-f')];
  const report = validateRounds(rows, { minimumSamples: 1 });
  assert.equal(report.reliableForMl, false);
  assert.equal(report.checks.duplicateSourceKeys, 1);
  assert.equal(report.checks.duplicateFingerprints, 1);
});

test('malformed, impossible, regression, gap, and outlier values are labeled', () => {
  const rows = [round(1, 1.2, '2026-01-01T00:10:00Z'), round(2, -1, '2026-01-01T00:05:00Z', 'r2', 'f2', 'bad'), round(3, 1.3, '2026-01-01T00:11:00Z'), round(4, 1.4, '2026-01-01T00:12:00Z'), round(5, 1.2, '2026-01-01T01:00:00Z'), round(6, 100, '2026-01-01T01:01:00Z')];
  const report = validateRounds(rows, { minimumSamples: 1, gapThresholdSeconds: 300 });
  assert.equal(report.checks.impossibleValues, 1);
  assert.equal(report.checks.malformedValues, 1);
  assert.equal(report.checks.timestampRegressions, 1);
  assert.ok(report.checks.abnormalGaps >= 1);
  assert.ok(report.events.some((e) => e.eventType === 'outlier_multiplier'));
  assert.equal(report.reliableForMl, false);
});

test('insufficient sample size blocks ML', () => {
  const report = validateRounds([round(1, 1.2, '2026-01-01T00:00:00Z')], { minimumSamples: 30 });
  assert.equal(report.reliableForMl, false);
  assert.ok(report.reliabilityReasons.some((reason) => reason.startsWith('insufficient_samples')));
});
