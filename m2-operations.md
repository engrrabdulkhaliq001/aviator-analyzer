# M2 Collector Operations

The collector runs as a systemd service under the unprivileged `ubuntu` account. It reads `/opt/aviator-analyzer/.env`, writes validated rounds to localhost PostgreSQL with parameterized queries, and uses both a deterministic visible-history key and a SHA-256 fingerprint for idempotency.

Replay verification uses `collector/fixtures/sample.html`:

```bash
cd /opt/aviator-analyzer/collector
npm run replay
```

The replay parser only accepts the completed-history region or the visible `Provably Fair Game` history region. It excludes active betting controls and redacts sensitive payload fields. The service reconnects with exponential backoff, writes a bounded JSONL log under `/opt/aviator-analyzer/logs`, updates `collector_status`, and handles SIGINT/SIGTERM.

The service never enters credentials, clicks game controls, bypasses CAPTCHA or anti-bot protections, places bets, or performs account actions. A CDP URL should be set only when a manually authorized browser session and private SSH tunnel are active.
