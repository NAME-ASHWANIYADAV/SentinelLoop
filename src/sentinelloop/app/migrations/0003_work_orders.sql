-- 0003 work orders: lifecycle, events, outcomes.

CREATE TABLE work_orders (
  wo_id               TEXT PRIMARY KEY,
  asset_id            TEXT NOT NULL REFERENCES assets(asset_id),
  origin              TEXT NOT NULL CHECK (origin IN ('system', 'manual', 'external')),
  assessment_id       TEXT REFERENCES assessments(assessment_id),
  job_type            TEXT NOT NULL,
  title               TEXT NOT NULL,
  description         TEXT NOT NULL DEFAULT '',
  priority_class      TEXT NOT NULL CHECK (priority_class IN ('P1', 'P2', 'P3')),
  priority_score      REAL,
  explanation_json    TEXT NOT NULL DEFAULT '{}',
  due_by_ms           INTEGER,
  duration_h          REAL NOT NULL,
  crew_size           INTEGER NOT NULL,
  required_skill      TEXT NOT NULL,
  parts_json          TEXT NOT NULL,
  state               TEXT NOT NULL CHECK (state IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED',
                                                     'REJECTED', 'DEFERRED', 'CANCELLED')),
  version             INTEGER NOT NULL,
  scheduled_start_ms  INTEGER,
  scheduled_end_ms    INTEGER,
  assigned_json       TEXT NOT NULL DEFAULT '[]',
  deferred_until_ms   INTEGER,
  external_ref        TEXT,
  idempotency_key     TEXT NOT NULL UNIQUE,
  payload_sha256      TEXT NOT NULL,
  created_by          TEXT NOT NULL,
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL
);
CREATE INDEX ix_wo_asset ON work_orders(asset_id, state);
CREATE INDEX ix_wo_state ON work_orders(state);

CREATE TABLE work_order_events (
  event_id         INTEGER PRIMARY KEY,
  wo_id            TEXT NOT NULL REFERENCES work_orders(wo_id),
  ts               TEXT NOT NULL,
  actor            TEXT NOT NULL,
  role             TEXT NOT NULL,
  action           TEXT NOT NULL,
  from_state       TEXT,
  to_state         TEXT NOT NULL,
  reason           TEXT NOT NULL DEFAULT '',
  data_json        TEXT NOT NULL DEFAULT '{}',
  idempotency_key  TEXT,
  UNIQUE (wo_id, idempotency_key)
);

CREATE TABLE outcomes (
  wo_id                   TEXT PRIMARY KEY REFERENCES work_orders(wo_id),
  recorded_by             TEXT NOT NULL,
  recorded_at             TEXT NOT NULL,
  findings_code           TEXT NOT NULL,
  failure_confirmed       TEXT NOT NULL CHECK (failure_confirmed IN ('yes', 'no', 'unknown')),
  root_cause              TEXT NOT NULL DEFAULT '',
  actions_taken           TEXT NOT NULL,
  parts_used_json         TEXT NOT NULL,
  downtime_hours          REAL NOT NULL,
  returned_to_service_at  TEXT,
  notes                   TEXT NOT NULL DEFAULT '',
  flags_json              TEXT NOT NULL
);
