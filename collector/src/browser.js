const { chromium } = require('playwright');
const { redactUrl } = require('./frames');

async function openBrowser(config, events) {
  const attached = Boolean(config.cdpUrl);
  const browser = attached
    ? await chromium.connectOverCDP(config.cdpUrl)
    : await chromium.launch({ headless: config.headless });
  const context = attached ? browser.contexts()[0] : await browser.newContext();
  if (!context) throw new Error('No browser context available for CDP session');
  const page = context.pages()[0] || await context.newPage();
  page.on('console', (message) => {
    if (message.type() === 'error' || message.type() === 'warning') events.console.push({ type: message.type(), text: message.text().slice(0, 1000) });
  });
  page.on('requestfailed', (request) => {
    events.failedRequests.push({ method: request.method(), url: redactUrl(request.url()), failure: request.failure()?.errorText || 'unknown' });
  });
  page.on('pageerror', (error) => events.pageErrors.push(String(error.message || error).slice(0, 1000)));
  return { browser, context, page, attached };
}

module.exports = { openBrowser };
