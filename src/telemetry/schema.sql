-- SQL schema for telemetry table in Supabase Postgres
-- Phase 23 (D-10): Flat-path architecture — replaces legacy signal_type/channel columns

CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL,
    rig_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    instrument_name TEXT NOT NULL,
    path TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    execution_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_recorded_at ON telemetry(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_rig_id ON telemetry(rig_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_instrument_id ON telemetry(instrument_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_path ON telemetry(path);
CREATE INDEX IF NOT EXISTS idx_telemetry_rig_instrument ON telemetry(rig_id, instrument_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_rig_path ON telemetry(rig_id, path);
CREATE INDEX IF NOT EXISTS idx_telemetry_execution_id ON telemetry(execution_id);

-- Optional: Enable Row Level Security (RLS) if needed
-- ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

-- Optional: Create a policy for authenticated users
-- CREATE POLICY "Allow authenticated users to read telemetry"
--     ON telemetry FOR SELECT
--     TO authenticated
--     USING (true);
