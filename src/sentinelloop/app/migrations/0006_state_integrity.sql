-- State integrity (Phase 9 adversarial-review fixes, ADVERSARIAL_REVIEW.md).
-- latched_since_ms: wall-clock time the current latch began or escalated; only work ordered after it can clear it.
-- awaiting_assessment: set when a latch is cleared, so the asset is not shown as healthy until it is assessed again.
-- last_applied_as_of_ms / last_applied_at_ms: the assessment instant and wall-clock time of the last assessment applied
--   to the live state; assessments for earlier instants are stored as historical replays and never move the state.
ALTER TABLE asset_states ADD COLUMN latched_since_ms INTEGER;
ALTER TABLE asset_states ADD COLUMN awaiting_assessment INTEGER NOT NULL DEFAULT 0;
ALTER TABLE asset_states ADD COLUMN last_applied_as_of_ms INTEGER;
ALTER TABLE asset_states ADD COLUMN last_applied_at_ms INTEGER;
ALTER TABLE assessments ADD COLUMN applied_to_state INTEGER NOT NULL DEFAULT 1;
CREATE INDEX ix_assessments_applied ON assessments (asset_id, applied_to_state, as_of_ms);
