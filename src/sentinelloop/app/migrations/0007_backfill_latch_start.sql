-- Assets that were already latched before migration 0006 have no recorded latch start. Use the time the state row was
-- last written: it is at or after the true start, so work ordered before it cannot clear the latch (fail closed).
UPDATE asset_states
   SET latched_since_ms = CAST(ROUND((julianday(updated_at) - 2440587.5) * 86400000.0) AS INTEGER)
 WHERE latched_risk != 'NONE' AND latched_since_ms IS NULL;
