-- Rows written before migration 0006 have no last applied instant or time, so on an upgraded database the first assessments
-- were applied whatever their instant (a back-dated one could clear a live data failure) and ASSESSMENT_OVERDUE never showed.
-- Backfill both from the asset's applied assessments: the latest instant assessed, and the time the latest one was stored.
-- Code before 0006 did not refuse future instants, so an instant counts at most up to the time it was stored plus the
-- 5-minute clock skew (health.MAX_FUTURE_SKEW_MS): a mistyped future instant must not turn every later assessment into a
-- replay and freeze the live state.
UPDATE asset_states
   SET last_applied_as_of_ms = (SELECT MAX(MIN(a.as_of_ms, COALESCE(CAST(ROUND((julianday(a.created_at) - 2440587.5) * 86400000.0) AS INTEGER),
                                                                    CAST(ROUND((julianday('now') - 2440587.5) * 86400000.0) AS INTEGER)) + 300000))
                                  FROM assessments a WHERE a.asset_id = asset_states.asset_id AND a.applied_to_state = 1)
 WHERE last_applied_as_of_ms IS NULL;
UPDATE asset_states
   SET last_applied_at_ms = (SELECT CAST(ROUND((MAX(julianday(a.created_at)) - 2440587.5) * 86400000.0) AS INTEGER) FROM assessments a
                              WHERE a.asset_id = asset_states.asset_id AND a.applied_to_state = 1)
 WHERE last_applied_at_ms IS NULL;
-- A row that shows an assessment result but has no assessment rows (a partial restore or a hand edit): every instant up to
-- the row's last write (at or after its last assessment; never later than this upgrade) counts as applied, so back-dated
-- assessments cannot clear what it shows (fail closed). When it was last assessed is unknown and stays empty: the asset is
-- shown ASSESSMENT_OVERDUE until an assessment is applied (health.asset_view).
UPDATE asset_states
   SET last_applied_as_of_ms = COALESCE(MIN(CAST(ROUND((julianday(updated_at) - 2440587.5) * 86400000.0) AS INTEGER),
                                            CAST(ROUND((julianday('now') - 2440587.5) * 86400000.0) AS INTEGER)),
                                        CAST(ROUND((julianday('now') - 2440587.5) * 86400000.0) AS INTEGER))
 WHERE last_applied_as_of_ms IS NULL AND last_health IS NOT NULL;
