const crypto = require('node:crypto');

const BUCKETS = [
  ['under_1_5', (v) => v < 1.5],
  ['1_5_to_2', (v) => v >= 1.5 && v < 2],
  ['2_to_5', (v) => v >= 2 && v < 5],
  ['5_to_10', (v) => v >= 5 && v < 10],
  ['10_plus', (v) => v >= 10],
];

function numeric(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function median(values) { if (!values.length) return null; const a = [...values].sort((x, y) => x - y); const m = Math.floor(a.length / 2); return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; }
function quantile(values, q) { if (!values.length) return null; const a = [...values].sort((x, y) => x - y); const pos = (a.length - 1) * q; const lo = Math.floor(pos); const hi = Math.ceil(pos); return a[lo] + (a[hi] - a[lo]) * (pos - lo); }
function validRawMultiplier(raw) { return typeof raw === 'string' && /^[1-9]\d{0,5}(?:\.\d{1,4})?\s*x$/i.test(raw.trim()); }
function event(type, severity, details, roundId = null) { return { roundId, eventType: type, severity, details }; }

function validateRounds(input, options = {}) {
  const ingestionRows = [...input];
  const rounds = [...input].sort((a, b) => new Date(a.observed_at || a.observedAt) - new Date(b.observed_at || b.observedAt) || Number(a.id || 0) - Number(b.id || 0));
  const gapThresholdSeconds = options.gapThresholdSeconds ?? 300;
  const minimumSamples = options.minimumSamples ?? 30;
  const events = [];
  const keyMap = new Map(); const fingerprintMap = new Map();
  const values = [];
  const daily = new Map();
  let timestampRegressionCount = 0;

  for (let i = 1; i < ingestionRows.length; i += 1) {
    const previous = new Date(ingestionRows[i - 1].observed_at || ingestionRows[i - 1].observedAt);
    const current = new Date(ingestionRows[i].observed_at || ingestionRows[i].observedAt);
    if (Number.isFinite(previous.getTime()) && Number.isFinite(current.getTime()) && current < previous) {
      timestampRegressionCount += 1;
      events.push(event('timestamp_regression', 'error', { previous: previous.toISOString(), current: current.toISOString(), deltaSeconds: (current - previous) / 1000 }, ingestionRows[i].id ?? null));
    }
  }

  for (let i = 0; i < rounds.length; i += 1) {
    const r = rounds[i]; const id = r.id ?? null; const value = numeric(r.multiplier); const observed = new Date(r.observed_at || r.observedAt);
    if (!r.source_round_key) events.push(event('missing_source_key', 'error', { source: r.source }, id));
    else { if (keyMap.has(`${r.source}|${r.source_round_key}`)) events.push(event('duplicate_source_key', 'error', { duplicateOf: keyMap.get(`${r.source}|${r.source_round_key}`), sourceRoundKey: r.source_round_key }, id)); else keyMap.set(`${r.source}|${r.source_round_key}`, id); }
    if (!r.raw_fingerprint) events.push(event('missing_fingerprint', 'error', {}, id));
    else if (fingerprintMap.has(`${r.source}|${r.raw_fingerprint}`)) events.push(event('duplicate_fingerprint', 'error', { duplicateOf: fingerprintMap.get(`${r.source}|${r.raw_fingerprint}`) }, id)); else fingerprintMap.set(`${r.source}|${r.raw_fingerprint}`, id);
    if (value === null || value <= 0) events.push(event('impossible_multiplier', 'error', { multiplier: r.multiplier }, id));
    if (!validRawMultiplier(r.raw_value)) events.push(event('malformed_raw_value', 'error', { rawValue: r.raw_value }, id));
    if (!Number.isFinite(observed.getTime())) events.push(event('invalid_timestamp', 'error', { observedAt: r.observed_at }, id));
    if (i > 0) { const previous = new Date(rounds[i - 1].observed_at || rounds[i - 1].observedAt); const delta = (observed - previous) / 1000; if (delta > gapThresholdSeconds) events.push(event('sequence_gap', 'warning', { from: previous.toISOString(), to: observed.toISOString(), gapSeconds: delta }, id)); }
    if (value !== null && value > 0) { values.push(value); const day = Number.isFinite(observed.getTime()) ? observed.toISOString().slice(0, 10) : 'invalid'; if (!daily.has(day)) daily.set(day, []); daily.get(day).push(value); }
  }
  const q1 = quantile(values, 0.25); const q3 = quantile(values, 0.75); const iqr = q1 === null ? null : q3 - q1; const upperOutlier = iqr === null ? null : q3 + 1.5 * iqr;
  for (const r of rounds) { const value = numeric(r.multiplier); if (value !== null && upperOutlier !== null && value > upperOutlier) events.push(event('outlier_multiplier', 'warning', { multiplier: value, upperFence: upperOutlier, method: 'Tukey-1.5-IQR' }, r.id ?? null)); }
  const bucketCounts = Object.fromEntries(BUCKETS.map(([name]) => [name, 0])); for (const value of values) { const bucket = BUCKETS.find(([, fn]) => fn(value)); if (bucket) bucketCounts[bucket[0]] += 1; }
  const dailySummary = Object.fromEntries([...daily.entries()].map(([day, vals]) => [day, { count: vals.length, min: Math.min(...vals), max: Math.max(...vals), median: median(vals), bucketCounts: Object.fromEntries(BUCKETS.map(([name, fn]) => [name, vals.filter(fn).length])) }]));
  const errors = events.filter((e) => e.severity === 'error'); const warnings = events.filter((e) => e.severity === 'warning');
  const reasons = []; if (values.length < minimumSamples) reasons.push(`insufficient_samples:${values.length}<${minimumSamples}`); if (errors.length) reasons.push(`validation_errors:${errors.length}`); if (timestampRegressionCount) reasons.push(`timestamp_regressions:${timestampRegressionCount}`);
  return { reportVersion: 'm3.0.0', generatedAt: new Date().toISOString(), sampleCount: values.length, minimumSamples, reliableForMl: reasons.length === 0, reliabilityReasons: reasons, checks: { duplicateSourceKeys: events.filter((e) => e.eventType === 'duplicate_source_key').length, duplicateFingerprints: events.filter((e) => e.eventType === 'duplicate_fingerprint').length, impossibleValues: events.filter((e) => e.eventType === 'impossible_multiplier').length, malformedValues: events.filter((e) => e.eventType === 'malformed_raw_value').length, timestampRegressions: timestampRegressionCount, abnormalGaps: events.filter((e) => e.eventType === 'sequence_gap').length, outliers: events.filter((e) => e.eventType === 'outlier_multiplier').length }, summary: { min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null, median: median(values), bucketCounts, daily: dailySummary }, events, runId: crypto.randomUUID() };
}

module.exports = { validateRounds, median, quantile, validRawMultiplier };
