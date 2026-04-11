-- Phase 23 (D-10): Migrate telemetry table to flat-path architecture
-- This migration replaces the rigid instrument_id/channel/signal_type columns
-- with a single generic `path` column that supports arbitrary instrument paths.

-- Step 1: Truncate all existing telemetry data (D-10: start fresh)
TRUNCATE TABLE telemetry;

-- Step 2: Drop legacy columns
ALTER TABLE telemetry DROP COLUMN IF EXISTS signal_type;
ALTER TABLE telemetry DROP COLUMN IF EXISTS channel;

-- Step 3: Add the flat path column
-- The `path` column stores the full instrument path (e.g. "psu1.voltage", "scope1.vpp")
ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS path TEXT NOT NULL DEFAULT '';

-- Step 4: Drop legacy indexes that reference removed columns
DROP INDEX IF EXISTS idx_telemetry_signal_type;
DROP INDEX IF EXISTS idx_telemetry_instrument_signal;

-- Step 5: Create new index for path-based queries
CREATE INDEX IF NOT EXISTS idx_telemetry_path ON telemetry(path);
CREATE INDEX IF NOT EXISTS idx_telemetry_rig_path ON telemetry(rig_id, path);
