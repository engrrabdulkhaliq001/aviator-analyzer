const test = require('node:test');
const assert = require('node:assert/strict');
const { parseMultiplier, extractCandidates } = require('../src/parser');
const { dedupeRounds, fingerprint } = require('../src/dedupe');

test('parses valid multiplier strings', () => {
  assert.equal(parseMultiplier('1.23x'), 1.23);
  assert.equal(parseMultiplier(' 10x '), 10);
  assert.equal(parseMultiplier('2.0000 x'), 2);
});

test('rejects malformed or unsafe multiplier strings', () => {
  assert.equal(parseMultiplier('0x'), null);
  assert.equal(parseMultiplier('abc'), null);
  assert.equal(parseMultiplier('1.2xx'), null);
  assert.equal(parseMultiplier('1.2'), 1.2);
});

test('extracts candidates from visible text', () => {
  assert.deepEqual(extractCandidates('Round: 1.23x then 2x'), [
    { rawValue: '1.23x', multiplier: 1.23 },
    { rawValue: '2x', multiplier: 2 },
  ]);
});

test('deduplicates source keys and fallback fingerprints', () => {
  const base = { source: 'bet939', multiplier: 1.5, rawValue: '1.50x', observedAt: '2026-09-15T00:00:00.000Z' };
  const rounds = [
    { ...base, sourceRoundKey: 'r1' },
    { ...base, sourceRoundKey: 'r1', multiplier: 9 },
    { ...base, sourceRoundKey: 'r2' },
    { ...base, sourceRoundKey: null },
    { ...base, sourceRoundKey: null },
  ];
  assert.equal(typeof fingerprint(base), 'string');
  assert.equal(dedupeRounds(rounds).length, 3);
});
