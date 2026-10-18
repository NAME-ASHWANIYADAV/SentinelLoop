-- 0002 model registry, assessments and the per-asset health state.

CREATE TABLE models (
  model_id         TEXT PRIMARY KEY,
  family           TEXT NOT NULL,
  asset_type_id    TEXT NOT NULL REFERENCES asset_types(asset_type_id),
  scope_key        TEXT NOT NULL,
  version          TEXT NOT NULL,
  artifact_path    TEXT NOT NULL,
  artifact_sha256  TEXT NOT NULL,
  manifest_json    TEXT NOT NULL,
  status           TEXT NOT NULL CHECK (status IN ('candidate', 'approved', 'retired', 'rejected')),
  registered_by    TEXT NOT NULL,
  registered_at    TEXT NOT NULL,
  decided_by       TEXT,
  decided_at       TEXT,
  decision_reason  TEXT
);
CREATE INDEX ix_models_type ON models(asset_type_id, status);

CREATE TABLE assessments (
  assessment_id      TEXT PRIMARY KEY,
  asset_id           TEXT NOT NULL REFERENCES assets(asset_id),
  as_of_ms           INTEGER NOT NULL,
  created_at         TEXT NOT NULL,
  model_id           TEXT REFERENCES models(model_id),
  health_state       TEXT NOT NULL,
  reasons_json       TEXT NOT NULL,
  data_quality_json  TEXT NOT NULL,
  applicability_json TEXT NOT NULL,
  rul_unit           TEXT,
  rul_point          REAL,
  rul_lower          REAL,
  rul_upper          REAL,
  interval_level     REAL,
  rul_point_hours    REAL,
  rul_lower_hours    REAL,
  rul_upper_hours    REAL,
  risk_json          TEXT NOT NULL,
  anomaly_score      REAL,
  anomaly_flag       INTEGER,
  top_deviations_json TEXT NOT NULL DEFAULT '[]',
  inputs_json        TEXT NOT NULL,
  policy_json        TEXT NOT NULL
);
CREATE INDEX ix_assessments_asset ON assessments(asset_id, as_of_ms);

CREATE TABLE asset_states (
  asset_id            TEXT PRIMARY KEY REFERENCES assets(asset_id),
  effective           TEXT NOT NULL,
  latched_risk        TEXT NOT NULL CHECK (latched_risk IN ('NONE', 'INSPECTION', 'URGENT')),
  dq_failure_active   INTEGER NOT NULL,
  dq_ok_streak        INTEGER NOT NULL,
  last_health         TEXT,
  approval_pending    INTEGER NOT NULL,
  notes_json          TEXT NOT NULL,
  last_assessment_id  TEXT REFERENCES assessments(assessment_id),
  updated_at          TEXT NOT NULL
);
