const path = require('node:path');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });
module.exports = {
  databaseUrl: process.env.DATABASE_URL || '',
  reportPath: path.resolve(__dirname, '../../diagnostics/validation-report.json'),
  gapThresholdSeconds: Number(process.env.VALIDATION_GAP_SECONDS || 300),
  minimumSamples: Number(process.env.VALIDATION_MIN_SAMPLES || 30),
};
