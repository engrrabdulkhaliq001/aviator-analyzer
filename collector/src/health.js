const fs = require('node:fs/promises');
const path = require('node:path');

async function rotateIfNeeded(file, maxBytes) {
  try { const stat = await fs.stat(file); if (stat.size >= maxBytes) await fs.rename(file, `${file}.${Date.now()}`); } catch (error) { if (error.code !== 'ENOENT') throw error; }
}

function createLogger(config) {
  const file = path.join(config.logDir, 'collector.log');
  return async (level, message, extra = {}) => {
    await fs.mkdir(config.logDir, { recursive: true });
    await rotateIfNeeded(file, config.logMaxBytes);
    const line = JSON.stringify({ at: new Date().toISOString(), level, message, ...extra }) + '\n';
    await fs.appendFile(file, line, { mode: 0o600 });
    if (level === 'error') console.error(message);
  };
}

async function writeHeartbeat(dir, status, extra = {}) {
  await fs.mkdir(dir, { recursive: true });
  const payload = { status, updatedAt: new Date().toISOString(), ...extra };
  await fs.writeFile(path.join(dir, 'collector-status.json'), JSON.stringify(payload, null, 2) + '\n', { mode: 0o600 });
  return payload;
}

module.exports = { writeHeartbeat, createLogger };
