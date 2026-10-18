-- Integration with external systems (CMMS, webhooks). Targets start in read-only shadow mode.
CREATE TABLE integration_targets (
  target_id    TEXT PRIMARY KEY,
  kind         TEXT NOT NULL CHECK (kind IN ('odoo_json2', 'webhook')),
  base_url     TEXT NOT NULL,
  mode         TEXT NOT NULL DEFAULT 'shadow' CHECK (mode IN ('shadow', 'draft_requests')),
  config_json  TEXT NOT NULL DEFAULT '{}',      -- no secrets: names of environment variables only
  enabled      INTEGER NOT NULL DEFAULT 1,
  created_by   TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);

-- State-based sync: one row per (target, work order); a work order is (re)sent when its version differs from the
-- version last delivered (or recorded in shadow mode).
CREATE TABLE sync_items (
  target_id         TEXT NOT NULL REFERENCES integration_targets(target_id),
  wo_id             TEXT NOT NULL REFERENCES work_orders(wo_id),
  synced_version    INTEGER,
  pending_version   INTEGER,
  external_id       TEXT,
  status            TEXT NOT NULL CHECK (status IN ('shadow', 'synced', 'retry', 'dead')),
  attempts          INTEGER NOT NULL DEFAULT 0,
  next_attempt_ms   INTEGER,
  last_error        TEXT,
  payload_json      TEXT,
  payload_sha256    TEXT,
  updated_at        TEXT NOT NULL,
  PRIMARY KEY (target_id, wo_id)
);
CREATE INDEX sync_items_status ON sync_items (target_id, status, next_attempt_ms);

CREATE TABLE integration_log (
  id          INTEGER PRIMARY KEY,
  ts          TEXT NOT NULL,
  target_id   TEXT NOT NULL,
  wo_id       TEXT,
  action      TEXT NOT NULL,
  outcome     TEXT NOT NULL,
  detail_json TEXT NOT NULL DEFAULT '{}'
);
