const fs = require('node:fs/promises');
const path = require('node:path');
const config = require('./config');
const { openBrowser } = require('./browser');
const { collectFrameSnapshot } = require('./frames');
const { parseCompletedRounds } = require('./parser');
const { dedupeRounds } = require('./dedupe');
const { writeHeartbeat, createLogger } = require('./health');
const { createDb } = require('./db');

let stopping = false;
let browserHandle = null;
let db = null;
let heartbeatTimer = null;

async function persistRounds(rounds, logger) {
  let inserted = 0;
  for (const round of dedupeRounds(rounds)) {
    if (db && await db.insertRound(round)) inserted += 1;
  }
  if (rounds.length) {
    const lastRoundAt = rounds[rounds.length - 1].observedAt;
    await writeHeartbeat(config.diagnosticDir, 'online', { lastRoundAt, roundsToday: inserted });
    if (db) await db.updateStatus('online', { lastRoundAt, parserStatus: 'ready', browserStatus: 'connected' });
  } else if (db) {
    await db.updateStatus('online', { parserStatus: 'ready', browserStatus: 'connected' });
  }
  await logger('info', 'round_batch_processed', { candidates: rounds.length, inserted });
  return inserted;
}

async function runReplay(file) {
  const logger = createLogger(config);
  const snapshot = await fs.readFile(path.resolve(file), 'utf8');
  const rounds = parseCompletedRounds(snapshot, '2026-09-15T00:00:00.000Z');
  const inserted = await persistRounds(rounds, logger);
  console.log(JSON.stringify({ mode: 'replay', fixture: path.resolve(file), roundsParsed: rounds.length, inserted }, null, 2));
  return { rounds, inserted };
}

async function runDiagnostic() {
  const logger = createLogger(config);
  const events = { console: [], failedRequests: [], pageErrors: [] };
  let page;
  try {
    await writeHeartbeat(config.diagnosticDir, 'starting');
    ({ browser: browserHandle, page, attached } = await openBrowser(config, events));
    if (!attached) { await page.goto(config.url, { waitUntil: 'domcontentloaded', timeout: config.navigationTimeoutMs }); await page.waitForTimeout(3000); }
    const snapshot = await collectFrameSnapshot(page);
    const rounds = parseCompletedRounds(snapshot.visibleText);
    await persistRounds(rounds, logger);
    const report = { diagnosticVersion: 'm2.0.0', completedAt: new Date().toISOString(), browserMode: attached ? 'attached-cdp' : 'isolated-headless', target: { url: page.url(), title: await page.title().catch(() => '') }, frameCount: snapshot.frameCount, frames: snapshot.frames, candidateValues: rounds, candidateCount: rounds.length, evidence: { visibleTextCharacters: snapshot.visibleText.length, visibleTextSample: snapshot.visibleText.slice(0, 5000), consoleErrorsOrWarnings: events.console, pageErrors: events.pageErrors, failedRequests: events.failedRequests }, safety: { automaticBetting: false, credentialsEntered: false, antiBotBypass: false } };
    await fs.writeFile(path.join(config.diagnosticDir, 'm2-report.json'), JSON.stringify(report, null, 2) + '\n', { mode: 0o600 });
    console.log(JSON.stringify({ report: path.join(config.diagnosticDir, 'm2-report.json'), candidateCount: rounds.length }, null, 2));
    return report;
  } finally { if (browserHandle && !config.cdpUrl) await browserHandle.close().catch(() => {}); }
}

async function connectAndCollect() {
  const logger = createLogger(config);
  let delay = config.reconnectBaseMs;
  while (!stopping) {
    try {
      const events = { console: [], failedRequests: [], pageErrors: [] };
      ({ browser: browserHandle, page } = await openBrowser(config, events));
      if (!config.cdpUrl) { await page.goto(config.url, { waitUntil: 'domcontentloaded', timeout: config.navigationTimeoutMs }); }
      await writeHeartbeat(config.diagnosticDir, 'online', { browserStatus: 'connected', parserStatus: 'ready' });
      if (db) await db.updateStatus('online', { parserStatus: 'ready', browserStatus: 'connected' });
      delay = config.reconnectBaseMs;
      while (!stopping) {
        const snapshot = await collectFrameSnapshot(page);
        await persistRounds(parseCompletedRounds(snapshot.visibleText), logger);
        await new Promise((resolve) => setTimeout(resolve, config.pollIntervalMs));
      }
    } catch (error) {
      await logger('error', 'collector_connection_error', { error: error.message.slice(0, 500) });
      await writeHeartbeat(config.diagnosticDir, 'offline', { browserStatus: 'disconnected', errorMessage: error.message.slice(0, 500) });
      if (db) await db.updateStatus('offline', { browserStatus: 'disconnected', errorMessage: error.message.slice(0, 500) });
      if (browserHandle && !config.cdpUrl) await browserHandle.close().catch(() => {});
      await new Promise((resolve) => setTimeout(resolve, delay));
      delay = Math.min(delay * 2, config.reconnectMaxMs);
    }
  }
}

async function shutdown(signal) {
  if (stopping) return;
  stopping = true;
  await writeHeartbeat(config.diagnosticDir, 'stopping');
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  if (browserHandle && !config.cdpUrl) await browserHandle.close().catch(() => {});
  if (db) await db.close().catch(() => {});
  process.exitCode = 0;
  console.log(`collector stopped (${signal})`);
}

async function main() {
  db = createDb(config);
  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  const args = process.argv.slice(2);
  if (args[0] === '--replay') return runReplay(args[1] || path.join(__dirname, '../fixtures/sample.html'));
  if (args[0] === '--diagnostic') return runDiagnostic();
  heartbeatTimer = setInterval(() => writeHeartbeat(config.diagnosticDir, 'online').catch(() => {}), config.heartbeatIntervalMs);
  return connectAndCollect();
}

if (require.main === module) main().catch(async (error) => { console.error(error.message.slice(0, 500)); await shutdown('ERROR'); process.exitCode = 1; });
module.exports = { main, runReplay, persistRounds };
