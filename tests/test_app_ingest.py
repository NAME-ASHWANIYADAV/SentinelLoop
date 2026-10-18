"""Ingestion against the data contract (tests written before the code)."""
import json

import pytest

from sentinelloop.app import db as dbmod, ingest, registry
from sentinelloop.app.timeutil import parse_ts
from test_app_foundation import KEY, pump, pump_type

NOW = parse_ts("2026-10-18T12:00:00Z")


@pytest.fixture
def plant(tmp_path):
    d = dbmod.Database(tmp_path / "plant.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "Asia/Kolkata", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    registry.create_asset(d, pump("P-102"), actor="admin")
    return d


def rec(asset="P-101", ts="2026-10-18T10:00:00Z", signal="bearing_temp", value=60.0, unit="degC"):
    return {"asset": asset, "timestamp": ts, "signal": signal, "value": value, "unit": unit}


def test_clean_batch_is_accepted_and_stored(plant):
    rows = [rec(ts=f"2026-10-18T10:0{i}:00Z", value=60 + i) for i in range(5)] + [rec(signal="vibration_rms", value=2.1, unit="mm/s")]
    r = ingest.ingest_records(plant, rows, source="test", actor="svc", now_ms=NOW)
    assert r.status == "accepted" and r.rows_accepted == 6 and r.rows_rejected == 0
    with plant.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 6
        st = c.execute("SELECT last_ts_ms FROM signal_status WHERE asset_id='P-101' AND signal='bearing_temp'").fetchone()[0]
    assert st == parse_ts("2026-10-18T10:04:00Z")


def test_each_contract_violation_is_rejected_with_a_reason(plant):
    rows = [rec(asset="NOPE"),                                   # unknown asset
            rec(signal="pressure"),                              # signal not in the asset type's contract
            rec(unit="degF"),                                    # unit mismatch
            rec(value="hot"),                                    # not numeric
            rec(value=float("nan")),                             # not finite
            rec(ts="2026-10-18 10:00"),                          # naive timestamp, no batch timezone
            rec(ts="2026-10-18T13:00:00Z"),                      # in the future beyond the allowed clock skew
            rec(ts="not a time")]
    r = ingest.ingest_records(plant, rows, source="test", actor="svc", now_ms=NOW)
    assert r.status == "rejected" and r.rows_accepted == 0 and r.rows_rejected == 8
    reasons = sorted(e["reason"] for e in r.errors)
    assert reasons == sorted(["unknown_asset", "unknown_signal", "unit_mismatch", "non_numeric_value", "non_finite_value",
                              "naive_timestamp", "future_timestamp", "unparseable_timestamp"])
    with plant.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM rejected_rows").fetchone()[0] == 8


def test_out_of_range_values_are_kept_but_marked_suspect(plant):
    r = ingest.ingest_records(plant, [rec(value=400.0)], source="test", actor="svc", now_ms=NOW)
    assert r.status == "accepted" and r.rows_suspect == 1
    with plant.connect() as c:
        assert c.execute("SELECT quality FROM readings").fetchone()[0] == "suspect_out_of_range"


def test_duplicates_are_idempotent_and_conflicts_are_rejected(plant):
    ingest.ingest_records(plant, [rec(value=60.0)], source="a", actor="svc", now_ms=NOW)
    r = ingest.ingest_records(plant, [rec(value=60.0), rec(value=61.0, ts="2026-10-18T10:00:00+00:00")], source="b", actor="svc", now_ms=NOW)
    assert r.rows_duplicate == 1 and r.rows_rejected == 1 and r.errors[0]["reason"] == "conflicting_value"
    with plant.connect() as c:
        assert [tuple(r) for r in c.execute("SELECT value FROM readings").fetchall()] == [(60.0,)]


def test_within_batch_conflict_and_exact_duplicate(plant):
    r = ingest.ingest_records(plant, [rec(value=60.0), rec(value=60.0), rec(value=70.0)], source="a", actor="svc", now_ms=NOW)
    assert r.rows_accepted == 1 and r.rows_duplicate == 1 and r.rows_rejected == 1


def test_resubmitting_the_same_batch_is_recognised(plant):
    rows = [rec(value=60.0)]
    r1 = ingest.ingest_records(plant, rows, source="a", actor="svc", now_ms=NOW)
    r2 = ingest.ingest_records(plant, rows, source="a", actor="svc", now_ms=NOW)
    assert r2.status == "duplicate_batch" and r2.batch_id == r1.batch_id


def test_out_of_order_and_late_rows_are_counted(plant):
    ingest.ingest_records(plant, [rec(ts="2026-10-18T11:00:00Z")], source="a", actor="svc", now_ms=NOW)
    rows = [rec(ts="2026-10-18T11:30:00Z"), rec(ts="2026-10-18T11:20:00Z"), rec(ts="2026-10-18T09:00:00Z")]
    r = ingest.ingest_records(plant, rows, source="b", actor="svc", now_ms=NOW, lateness_ms=30 * 60 * 1000)
    assert r.rows_accepted == 3 and r.rows_out_of_order == 2 and r.rows_late == 1


def test_naive_timestamps_use_the_declared_batch_timezone(plant):
    r = ingest.ingest_records(plant, [rec(ts="2026-10-18T15:30:00")], source="a", actor="svc", now_ms=NOW, default_tz="Asia/Kolkata")
    assert r.status == "accepted"
    with plant.connect() as c:
        assert c.execute("SELECT ts_ms FROM readings").fetchone()[0] == parse_ts("2026-10-18T10:00:00Z")


def test_csv_long_and_wide_formats(plant, tmp_path):
    long_csv = tmp_path / "long.csv"
    long_csv.write_text("asset,timestamp,signal,value,unit\nP-101,2026-10-18T10:00:00Z,bearing_temp,60,degC\nP-101,2026-10-18T10:00:00Z,vibration_rms,2.0,mm/s\n")
    r = ingest.ingest_csv(plant, long_csv, source="file", actor="svc", now_ms=NOW)
    assert r.rows_accepted == 2
    wide_csv = tmp_path / "wide.csv"
    wide_csv.write_text("asset,timestamp,bearing_temp,vibration_rms\nP-102,2026-10-18T10:00:00Z,55,1.5\nP-102,2026-10-18T10:01:00Z,56,\n")
    r = ingest.ingest_csv(plant, wide_csv, source="file", actor="svc", now_ms=NOW, wide_units={"bearing_temp": "degC", "vibration_rms": "mm/s"})
    assert r.rows_accepted == 3 and r.rows_missing == 1          # the empty cell is a missing value, not a zero


def test_missing_required_columns_reject_the_whole_batch(plant, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("asset,signal,value\nP-101,bearing_temp,60\n")
    r = ingest.ingest_csv(plant, bad, source="file", actor="svc", now_ms=NOW)
    assert r.status == "rejected" and r.errors[0]["reason"] == "missing_columns"


def test_staleness_report_flags_silent_signals(plant):
    ingest.ingest_records(plant, [rec(ts="2026-10-18T08:00:00Z"), rec(signal="vibration_rms", unit="mm/s", ts="2026-10-18T11:55:00Z")], source="a", actor="svc", now_ms=NOW)
    stale = ingest.staleness(plant, now_ms=NOW, max_age_ms=60 * 60 * 1000)
    keys = {(s["asset_id"], s["signal"]) for s in stale}
    assert ("P-101", "bearing_temp") in keys and ("P-101", "vibration_rms") not in keys
    assert ("P-102", "bearing_temp") in keys          # never seen at all counts as stale for a required signal


def test_ingestion_writes_an_audit_event(plant):
    r = ingest.ingest_records(plant, [rec()], source="a", actor="svc", now_ms=NOW)
    with plant.connect() as c:
        row = c.execute("SELECT payload_json FROM audit_events WHERE action='ingest.batch'").fetchone()
    assert json.loads(row[0])["batch_id"] == r.batch_id
