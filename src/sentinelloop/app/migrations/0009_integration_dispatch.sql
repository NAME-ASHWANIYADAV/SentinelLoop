-- A create whose answer was lost may still commit after a later attempt searched for it by marker and created again (a
-- slow transaction, or a dispatcher whose lease lapsed). While this is set, every send of the order first searches the
-- CMMS by marker even though its request is known, and the order is due again at this time even if unchanged; a second
-- request carrying the marker makes a dead letter. Cleared by a search made at or after this time.
ALTER TABLE sync_items ADD COLUMN verify_after_ms INTEGER;
