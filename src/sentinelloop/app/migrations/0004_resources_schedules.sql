-- 0004 maintenance resources (technicians, shifts, parts, deliveries) and schedule proposals.

CREATE TABLE technicians (
  tech_id       TEXT PRIMARY KEY,
  display_name  TEXT NOT NULL,
  site_id       TEXT NOT NULL REFERENCES sites(site_id),
  skills_json   TEXT NOT NULL,
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL
);

CREATE TABLE shifts (
  tech_id   TEXT NOT NULL REFERENCES technicians(tech_id),
  start_ms  INTEGER NOT NULL,
  end_ms    INTEGER NOT NULL,
  CHECK (end_ms > start_ms),
  PRIMARY KEY (tech_id, start_ms)
);

CREATE TABLE parts (
  part_id      TEXT NOT NULL,
  site_id      TEXT NOT NULL REFERENCES sites(site_id),
  name         TEXT NOT NULL,
  on_hand      INTEGER NOT NULL CHECK (on_hand >= 0),
  lead_time_h  REAL NOT NULL CHECK (lead_time_h >= 0),
  orderable    INTEGER NOT NULL DEFAULT 1,
  unit_cost    REAL,
  updated_at   TEXT NOT NULL,
  PRIMARY KEY (part_id, site_id)
);

CREATE TABLE part_deliveries (
  delivery_id  INTEGER PRIMARY KEY,
  part_id      TEXT NOT NULL,
  site_id      TEXT NOT NULL,
  qty          INTEGER NOT NULL CHECK (qty > 0),
  eta_ms       INTEGER NOT NULL,
  reference    TEXT NOT NULL DEFAULT '',
  FOREIGN KEY (part_id, site_id) REFERENCES parts(part_id, site_id)
);

CREATE TABLE schedule_runs (
  run_id          TEXT PRIMARY KEY,
  site_id         TEXT NOT NULL REFERENCES sites(site_id),
  policy          TEXT NOT NULL,
  t0_ms           INTEGER NOT NULL,
  horizon_h       REAL NOT NULL,
  slot_h          REAL NOT NULL,
  created_by      TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  assignments_json TEXT NOT NULL,
  unscheduled_json TEXT NOT NULL,
  objective       REAL NOT NULL,
  stats_json      TEXT NOT NULL,
  solver_json     TEXT NOT NULL,
  violations_json TEXT NOT NULL,
  inputs_sha256   TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('proposed', 'applied', 'superseded')),
  applied_by      TEXT,
  applied_at      TEXT
);
