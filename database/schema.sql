CREATE TABLE IF NOT EXISTS rounds (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'bet939',
  multiplier NUMERIC(12,4) NOT NULL CHECK (multiplier > 0),
  raw_value TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  source_round_key TEXT,
  raw_fingerprint TEXT NOT NULL,
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source, source_round_key),
  UNIQUE (source, raw_fingerprint)
);
CREATE INDEX IF NOT EXISTS rounds_observed_at_idx ON rounds (observed_at DESC);
CREATE TABLE IF NOT EXISTS collector_status (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  status TEXT NOT NULL,
  last_round_at TIMESTAMPTZ,
  rounds_today INTEGER NOT NULL DEFAULT 0,
  parser_status TEXT,
  browser_status TEXT,
  error_message TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO collector_status (id, status) VALUES (1, 'starting') ON CONFLICT (id) DO NOTHING;
