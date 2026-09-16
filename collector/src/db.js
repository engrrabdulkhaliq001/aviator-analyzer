const { Pool } = require('pg');
const { redactSensitive } = require('./parser');

function createDb(config) {
  if (!config.databaseUrl) return null;
  const pool = new Pool({ connectionString: config.databaseUrl, max: 3, idleTimeoutMillis: 10000 });
  return {
    async insertRound(round) {
      const payload = redactSensitive(round.rawPayload || {});
      const sql = `INSERT INTO rounds (source, multiplier, raw_value, observed_at, source_round_key, raw_fingerprint, raw_payload)
        VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING RETURNING id`;
      const result = await pool.query(sql, [round.source, round.multiplier, round.rawValue, round.observedAt, round.sourceRoundKey, round.rawFingerprint, payload]);
      return result.rows[0]?.id || null;
    },
    async updateStatus(status, fields = {}) {
      const sql = `UPDATE collector_status SET status=$1, last_round_at=COALESCE($2,last_round_at), rounds_today=COALESCE($3,(SELECT count(*) FROM rounds WHERE observed_at >= CURRENT_DATE)), parser_status=COALESCE($4,parser_status), browser_status=COALESCE($5,browser_status), error_message=$6, updated_at=NOW() WHERE id=1`;
      await pool.query(sql, [status, fields.lastRoundAt || null, fields.roundsToday ?? null, fields.parserStatus || null, fields.browserStatus || null, fields.errorMessage || null]);
    },
    async close() { await pool.end(); },
    pool,
  };
}

module.exports = { createDb };
