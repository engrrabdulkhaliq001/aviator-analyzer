# Aviator Analyzer — M1 Collector

M1 is a data-acquisition diagnostic only. It observes authorized, visible page data and reports whether multiplier rounds can be extracted. It does not log in, click game controls, bypass CAPTCHA or anti-bot protections, place bets, or claim prediction accuracy.

## Run

```bash
cd collector
npm install
npx playwright install chromium
npm test
npm run diagnostic
```

Diagnostic output is written under `collector/diagnostics/` and is ignored by Git. Secrets, cookies, authorization headers, and browser storage are never logged.

The target URL is configured through `BET939_URL`; use only a URL and session that you are authorized to access and that the source permits.
