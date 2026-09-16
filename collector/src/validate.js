const fs = require('node:fs/promises');
const path = require('node:path');
const { Pool } = require('pg');
const config = require('./validation-config');
const { validateRounds } = require('./validator');

async function loadRounds(pool) {
  const result = await pool.query('SELECT id, source, multiplier, raw_value, observed_at, source_round_key, raw_fingerprint FROM rounds ORDER BY observed_at ASC, id ASC');
  return result.rows;
}

async function persistEvents(pool, report) {
  await pool.query('BEGIN');
  try {
    for (const item of report.events) await pool.query('INSERT INTO validation_events (run_id, round_id, event_type, severity, details) VALUES ($1,$2,$3,$4,$5)', [report.runId, item.roundId, item.eventType, item.severity, item.details]);
    await pool.query('COMMIT');
  } catch (error) { await pool.query('ROLLBACK'); throw error; }
}

async function main() {
  const pool = new Pool({ connectionString: config.databaseUrl });
  try {
    const rounds = await loadRounds(pool);
    const report = validateRounds(rounds, config);
    await fs.mkdir(path.dirname(config.reportPath), { recursive: true });
    await fs.writeFile(config.reportPath, JSON.stringify(report, null, 2) + '\n', { mode: 0o600 });
    await persistEvents(pool, report);
    console.log(JSON.stringify({ report: config.reportPath, runId: report.runId, sampleCount: report.sampleCount, reliableForMl: report.reliableForMl, eventCount: report.events.length, reliabilityReasons: report.reliabilityReasons }, null, 2));
    process.exitCode = report.reliableForMl ? 0 : 2;
  } finally { await pool.end(); }
}

if (require.main === module) main().catch((error) => { console.error(`Validation failed: ${error.message}`); process.exitCode = 1; });
module.exports = { loadRounds, persistEvents, main };
