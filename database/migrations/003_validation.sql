CREATE TABLE IF NOT EXISTS validation_events (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL,
  round_id BIGINT REFERENCES rounds(id),
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('info','warning','error')),
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS validation_events_run_idx ON validation_events (run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS validation_events_round_idx ON validation_events (round_id, created_at DESC);
