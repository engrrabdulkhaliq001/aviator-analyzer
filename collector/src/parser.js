const crypto = require('node:crypto');
const MULTIPLIER_RE = /(?:^|[^\d.])([1-9]\d{0,5}(?:\.\d{1,4})?)\s*x\b/gi;

function parseMultiplier(value) {
  if (typeof value !== 'string') return null;
  const match = value.trim().match(/^([1-9]\d{0,5}(?:\.\d{1,4})?)\s*x?$/i);
  if (!match) return null;
  const multiplier = Number(match[1]);
  return Number.isFinite(multiplier) && multiplier > 0 && multiplier <= 999999 ? multiplier : null;
}

function stripTags(html) {
  return String(html).replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/gi, ' ').replace(/&amp;/gi, '&');
}

function completedHistoryText(snapshot) {
  const text = String(snapshot || '');
  const marked = text.match(/(?:completed-history|round-history|history|previous)[^>]*>([\s\S]*?)(?:<\/section>|<\/div>|<\/article>)/i);
  if (marked) return stripTags(marked[1]);
  const fair = text.match(/Provably Fair Game([\s\S]*?)(?:\nBet\n|\nAuto\n|$)/i);
  if (fair) return fair[1];
  return text;
}

function extractCandidates(text) {
  if (typeof text !== 'string') return [];
  const candidates = [];
  for (const match of text.matchAll(MULTIPLIER_RE)) {
    const rawValue = match[1] + 'x';
    const multiplier = parseMultiplier(rawValue);
    if (multiplier !== null) candidates.push({ rawValue, multiplier });
  }
  return candidates;
}

function fingerprint(source, multiplier, rawValue, ordinal) {
  return crypto.createHash('sha256').update(`${source}|${ordinal}|${multiplier}|${rawValue}`).digest('hex');
}

function parseCompletedRounds(snapshot, observedAt = new Date().toISOString(), source = 'bet939') {
  const sourceText = completedHistoryText(snapshot);
  const candidates = extractCandidates(sourceText);
  return candidates.map((candidate, ordinal) => ({
    source, multiplier: candidate.multiplier, rawValue: candidate.rawValue, observedAt,
    sourceRoundKey: `visible-history:${ordinal}:${candidate.multiplier.toFixed(4)}`,
    rawFingerprint: fingerprint(source, candidate.multiplier, candidate.rawValue, ordinal),
    rawPayload: { parser: 'completed-history-v1', ordinal },
  }));
}

function redactSensitive(value) {
  if (value === null || value === undefined) return value;
  if (typeof value === 'string') return value.replace(/(authorization|cookie|token|password|secret)\s*[:=]\s*[^\s,;]+/gi, '$1:[redacted]');
  if (Array.isArray(value)) return value.map(redactSensitive);
  if (typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => /authorization|cookie|token|password|secret/i.test(k) ? [k, '[redacted]'] : [k, redactSensitive(v)]));
  return value;
}

module.exports = { parseMultiplier, extractCandidates, parseCompletedRounds, completedHistoryText, fingerprint, redactSensitive };
