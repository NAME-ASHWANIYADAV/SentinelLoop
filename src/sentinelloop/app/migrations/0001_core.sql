-- 0001 core: sites, asset types (data contracts), assets, ingestion, readings, signal status, audit events, users.
-- Conventions: *_ms columns are integer milliseconds since the Unix epoch, UTC. *_at columns are ISO-8601 UTC text ending in Z.

CREATE TABLE sites (
  site_id     TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  timezone    TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE TABLE asset_types (
  asset_type_id          TEXT PRIMARY KEY,
  name                   TEXT NOT NULL,
  description            TEXT NOT NULL DEFAULT '',
  time_basis             TEXT NOT NULL CHECK (time_basis IN ('timestamp', 'cycle_index')),
  usage_hours_per_cycle  REAL,
  signals_json           TEXT NOT NULL,
  jobs_json              TEXT NOT NULL,
  contract_version       INTEGER NOT NULL DEFAULT 1,
  created_at             TEXT NOT NULL
);

CREATE TABLE assets (
  asset_id                  TEXT PRIMARY KEY,
  tag                       TEXT NOT NULL UNIQUE,
  name                      TEXT NOT NULL,
  asset_type_id             TEXT NOT NULL REFERENCES asset_types(asset_type_id),
  site_id                   TEXT NOT NULL REFERENCES sites(site_id),
  location                  TEXT NOT NULL DEFAULT '',
  criticality               TEXT NOT NULL CHECK (criticality IN ('A', 'B', 'C')),
  failure_consequence_json  TEXT NOT NULL,
  config_json               TEXT NOT NULL DEFAULT '{}',
  operating_context_json    TEXT NOT NULL DEFAULT '{}',
  maintenance_windows_json  TEXT NOT NULL DEFAULT '[]',
  status                    TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'out_of_service', 'retired')),
  installed_at              TEXT,
  last_maintenance_at       TEXT,
  created_at                TEXT NOT NULL,
  updated_at                TEXT NOT NULL
);
CREATE INDEX ix_assets_site ON assets(site_id);
CREATE INDEX ix_assets_type ON assets(asset_type_id);

CREATE TABLE ingestion_batches (
  batch_id            TEXT PRIMARY KEY,
  source              TEXT NOT NULL,
  actor               TEXT NOT NULL,
  received_at         TEXT NOT NULL,
  content_sha256      TEXT NOT NULL UNIQUE,
  rows_total          INTEGER NOT NULL,
  rows_accepted       INTEGER NOT NULL,
  rows_rejected       INTEGER NOT NULL,
  rows_duplicate      INTEGER NOT NULL,
  rows_out_of_order   INTEGER NOT NULL,
  rows_late           INTEGER NOT NULL,
  rows_suspect        INTEGER NOT NULL,
  rows_missing        INTEGER NOT NULL,
  status              TEXT NOT NULL CHECK (status IN ('accepted', 'partially_accepted', 'rejected')),
  errors_json         TEXT NOT NULL,
  contract_version    INTEGER NOT NULL
);

CREATE TABLE readings (
  asset_id  TEXT NOT NULL REFERENCES assets(asset_id),
  signal    TEXT NOT NULL,
  ts_ms     INTEGER NOT NULL,
  value     REAL NOT NULL,
  quality   TEXT NOT NULL DEFAULT 'good' CHECK (quality IN ('good', 'suspect_out_of_range')),
  batch_id  TEXT NOT NULL REFERENCES ingestion_batches(batch_id),
  PRIMARY KEY (asset_id, signal, ts_ms)
) WITHOUT ROWID;
CREATE INDEX ix_readings_asset_ts ON readings(asset_id, ts_ms);

CREATE TABLE rejected_rows (
  batch_id    TEXT NOT NULL REFERENCES ingestion_batches(batch_id),
  row_number  INTEGER NOT NULL,
  reason      TEXT NOT NULL,
  detail      TEXT NOT NULL DEFAULT '',
  raw_json    TEXT NOT NULL
);
CREATE INDEX ix_rejected_batch ON rejected_rows(batch_id);

CREATE TABLE signal_status (
  asset_id          TEXT NOT NULL REFERENCES assets(asset_id),
  signal            TEXT NOT NULL,
  last_ts_ms        INTEGER NOT NULL,
  last_received_at  TEXT NOT NULL,
  n_readings        INTEGER NOT NULL,
  PRIMARY KEY (asset_id, signal)
);

CREATE TABLE audit_events (
  seq             INTEGER PRIMARY KEY,
  ts              TEXT NOT NULL,
  actor           TEXT NOT NULL,
  action          TEXT NOT NULL,
  entity          TEXT NOT NULL,
  entity_id       TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  payload_sha256  TEXT NOT NULL,
  prev_hash       TEXT NOT NULL,
  key_id          TEXT NOT NULL,
  hash            TEXT NOT NULL
);
CREATE INDEX ix_audit_entity ON audit_events(entity, entity_id);

CREATE TABLE users (
  user_id        TEXT PRIMARY KEY,
  display_name   TEXT NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('viewer', 'technician', 'planner', 'reliability_engineer', 'admin', 'integration')),
  password_hash  TEXT,
  api_key_hash   TEXT UNIQUE,
  active         INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT NOT NULL
);
