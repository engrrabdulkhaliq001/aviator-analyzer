const path = require('node:path');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

function bool(value, fallback) {
  if (value === undefined) return fallback;
  return String(value).toLowerCase() !== 'false';
}

module.exports = {
  databaseUrl: process.env.DATABASE_URL || '',
  url: process.env.BET939_URL || 'https://bet939.co/home/embedded?dl=6rz403',
  cdpUrl: process.env.BROWSER_CDP_URL || '',
  headless: bool(process.env.COLLECTOR_HEADLESS, true),
  pollIntervalMs: Number(process.env.POLL_INTERVAL_MS || 1000),
  diagnosticDir: path.resolve(__dirname, '../../', process.env.DIAGNOSTIC_DIR || 'diagnostics'),
  logDir: path.resolve(__dirname, '../../', process.env.LOG_DIR || 'logs'),
  logMaxBytes: Number(process.env.LOG_MAX_BYTES || 5242880),
  reconnectBaseMs: Number(process.env.RECONNECT_BASE_MS || 1000),
  reconnectMaxMs: Number(process.env.RECONNECT_MAX_MS || 60000),
  heartbeatIntervalMs: Number(process.env.HEARTBEAT_INTERVAL_MS || 10000),
  navigationTimeoutMs: Number(process.env.NAVIGATION_TIMEOUT_MS || 30000),
};
