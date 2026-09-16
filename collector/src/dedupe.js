const crypto = require('node:crypto');

function fingerprint(round) {
  return crypto.createHash('sha256')
    .update([round.source || 'bet939', round.multiplier, round.rawValue, round.observedAt].join('|'))
    .digest('hex');
}

function dedupeRounds(rounds) {
  const seen = new Set();
  return rounds.filter((round) => {
    const key = round.sourceRoundKey ? `key:${round.source}:${round.sourceRoundKey}` : `fp:${fingerprint(round)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

module.exports = { dedupeRounds, fingerprint };
