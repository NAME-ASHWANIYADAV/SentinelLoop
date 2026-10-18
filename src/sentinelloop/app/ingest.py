"""Ingestion of sensor readings against each asset type's data contract.

Contract v1 (long format, one reading per row): asset (id or tag), timestamp (ISO-8601 with UTC offset, or naive
with a declared batch time zone), signal (a name from the asset type), value (finite number; empty = missing),
unit (must equal the contract unit; no silent conversion). A wide CSV (one column per signal) is accepted when the
caller states the unit of every signal column.

Per row the importer rejects, with a reason code, anything it cannot store faithfully; it never guesses. Values
outside the contract's plausible range are stored but marked `suspect_out_of_range`. Exact duplicates are skipped
idempotently; a second, different value for the same asset/signal/instant is rejected as a conflict. Re-sending a
byte-identical batch returns the original batch. Every batch is recorded with its counts and an audit event.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from . import auditlog
from .auditlog import canonical
from .registry import list_asset_types
from .timeutil import NaiveTimestampError, iso, now_iso, now_ms as _now_ms, parse_ts

CONTRACT_VERSION = 1
MAX_RECORDS_PER_BATCH = 200_000          # same cap as the JSON route; a wide CSV expands to rows x signal columns


class IngestLimitError(ValueError):
    pass


class IngestInputError(ValueError):
    """A batch-level parameter (time zone, unit map) is invalid: the request is refused and nothing is recorded."""


LONG_COLUMNS = ("asset", "timestamp", "signal", "value", "unit")
MAX_STORED_ERRORS = 1000


def _check_params(default_tz, wide_units=None):
    if default_tz:
        try:
            ZoneInfo(default_tz)
        except (KeyError, ValueError, TypeError, OSError):      # ZoneInfoNotFoundError is a KeyError
            raise IngestInputError(f"default_tz {str(default_tz)[:64]!r} is not a known IANA time zone (e.g. 'Asia/Kolkata')") from None
    if wide_units is not None and not (isinstance(wide_units, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in wide_units.items())):
        raise IngestInputError('wide_units must map each signal column to its unit, e.g. {"bearing_temp": "degC"}')


@dataclass
class IngestResult:
    batch_id: str
    status: str
    rows_total: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    rows_duplicate: int = 0
    rows_out_of_order: int = 0
    rows_late: int = 0
    rows_suspect: int = 0
    rows_missing: int = 0
    errors: list = field(default_factory=list)
    new_batch: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _existing_batch(c, content_sha: str) -> IngestResult | None:
    r = c.execute("SELECT * FROM ingestion_batches WHERE content_sha256 = ?", (content_sha,)).fetchone()
    if r is None:
        return None
    import json
    return IngestResult(batch_id=r["batch_id"], status="duplicate_batch", rows_total=r["rows_total"], rows_accepted=0, rows_rejected=0,
                        rows_duplicate=r["rows_total"], errors=json.loads(r["errors_json"])[:20], new_batch=False)


def _registry_view(db):
    by_id, by_tag = {}, {}
    with db.connect() as c:
        for r in c.execute("SELECT asset_id, tag, asset_type_id, status FROM assets"):
            v = (r["asset_id"], r["asset_type_id"], r["status"])
            by_id[r["asset_id"]] = v
            by_tag[r["tag"]] = v
    assets = {}
    for k in set(by_id) | set(by_tag):
        a, b = by_id.get(k), by_tag.get(k)
        assets[k] = "AMBIGUOUS" if (a is not None and b is not None and a[0] != b[0]) else (a or b)
    types = {t.asset_type_id: {s.name: s for s in t.signals} for t in list_asset_types(db)}
    return assets, types


def _record_batch(db, actor, source, content_sha, res: IngestResult, valid_rows, rejected, now):
    import json
    with db.tx() as c:
        dup = _existing_batch(c, content_sha)
        if dup is not None:                                      # a concurrent identical upload won the race
            return dup
        c.execute("INSERT INTO ingestion_batches (batch_id, source, actor, received_at, content_sha256, rows_total, rows_accepted, rows_rejected, "
                  "rows_duplicate, rows_out_of_order, rows_late, rows_suspect, rows_missing, status, errors_json, contract_version) "
                  "VALUES (?,?,?,?,?,?,0,0,0,0,0,0,0,'rejected','[]',?)",
                  (res.batch_id, source, actor, iso(now), content_sha, res.rows_total, CONTRACT_VERSION))
        if valid_rows:
            c.execute("CREATE TEMP TABLE IF NOT EXISTS staging (asset_id TEXT, signal TEXT, ts_ms INTEGER, value REAL, quality TEXT, row_number INTEGER)")
            c.execute("DELETE FROM staging")
            c.executemany("INSERT INTO staging VALUES (?,?,?,?,?,?)", valid_rows)
            # rows already stored by an earlier batch: identical -> duplicate, different -> conflict
            for r in c.execute("SELECT s.row_number, s.asset_id, s.signal, s.ts_ms, s.value AS new, r.value AS old FROM staging s "
                               "JOIN readings r ON r.asset_id = s.asset_id AND r.signal = s.signal AND r.ts_ms = s.ts_ms").fetchall():
                if r["new"] == r["old"]:
                    res.rows_duplicate += 1
                else:
                    rejected.append((r["row_number"], "conflicting_value", f"stored value {r['old']} differs from {r['new']}",
                                     {"asset_id": r["asset_id"], "signal": r["signal"], "ts": iso(r["ts_ms"]), "value": r["new"]}))
            c.execute("DELETE FROM staging WHERE EXISTS (SELECT 1 FROM readings r WHERE r.asset_id = staging.asset_id AND r.signal = staging.signal "
                      "AND r.ts_ms = staging.ts_ms)")
            # late data: older than the last reading already stored for the signal by more than the lateness allowance
            res.rows_late = c.execute("SELECT COUNT(*) FROM staging s JOIN signal_status st ON st.asset_id = s.asset_id AND st.signal = s.signal "
                                      "WHERE s.ts_ms < st.last_ts_ms - ?", (res._lateness_ms,)).fetchone()[0]
            res.rows_suspect = c.execute("SELECT COUNT(*) FROM staging WHERE quality = 'suspect_out_of_range'").fetchone()[0]
            res.rows_accepted = c.execute("SELECT COUNT(*) FROM staging").fetchone()[0]
            c.execute("INSERT INTO readings (asset_id, signal, ts_ms, value, quality, batch_id) SELECT asset_id, signal, ts_ms, value, quality, ? FROM staging",
                      (res.batch_id,))
            c.execute("INSERT INTO signal_status (asset_id, signal, last_ts_ms, last_received_at, n_readings) "
                      "SELECT asset_id, signal, MAX(ts_ms), ?, COUNT(*) FROM staging GROUP BY asset_id, signal "
                      "ON CONFLICT(asset_id, signal) DO UPDATE SET last_ts_ms = MAX(last_ts_ms, excluded.last_ts_ms), "
                      "last_received_at = excluded.last_received_at, n_readings = n_readings + excluded.n_readings", (iso(now),))
            c.execute("DELETE FROM staging")
        res.rows_rejected = len(rejected)
        res.errors = [{"row": n, "reason": reason, "detail": detail} for n, reason, detail, _ in sorted(rejected, key=lambda x: x[0])]
        if rejected:
            c.executemany("INSERT INTO rejected_rows (batch_id, row_number, reason, detail, raw_json) VALUES (?,?,?,?,?)",
                          [(res.batch_id, n, reason, detail, canonical(raw)) for n, reason, detail, raw in rejected])
        res.status = "rejected" if res.rows_accepted == 0 and res.rows_rejected > 0 else ("partially_accepted" if res.rows_rejected else "accepted")
        c.execute("UPDATE ingestion_batches SET rows_accepted = ?, rows_rejected = ?, rows_duplicate = ?, rows_out_of_order = ?, rows_late = ?, "
                  "rows_suspect = ?, rows_missing = ?, status = ?, errors_json = ? WHERE batch_id = ?",
                  (res.rows_accepted, res.rows_rejected, res.rows_duplicate, res.rows_out_of_order, res.rows_late, res.rows_suspect, res.rows_missing,
                   res.status, json.dumps(res.errors[:MAX_STORED_ERRORS]), res.batch_id))
        summary = {k: v for k, v in res.to_dict().items() if k not in ("errors", "new_batch")}
        summary["source"] = source
        summary["reject_reasons"] = _reason_counts(rejected)
        auditlog.append(c, actor=actor, action="ingest.batch", entity="ingestion_batch", entity_id=res.batch_id, payload=summary,
                        key=db.audit_key, key_id=db.audit_key_id)
    return res


def _reason_counts(rejected) -> dict:
    out: dict[str, int] = {}
    for _, reason, _, _ in rejected:
        out[reason] = out.get(reason, 0) + 1
    return out


def _ingest(db, records: list[dict], source: str, actor: str, content_sha: str, *, default_tz=None, now_ms=None,
            max_future_skew_ms=5 * 60 * 1000, lateness_ms=60 * 60 * 1000, batch_errors=None) -> IngestResult:
    now = int(now_ms if now_ms is not None else _now_ms())
    with db.connect() as c:
        dup = _existing_batch(c, content_sha)
    if dup is not None:
        return dup
    res = IngestResult(batch_id=f"B{now}-{content_sha[:12]}", status="rejected", rows_total=len(records))
    res._lateness_ms = int(lateness_ms)
    rejected: list[tuple] = []
    if batch_errors:
        for reason, detail in batch_errors:
            rejected.append((0, reason, detail, {}))
        return _record_batch(db, actor, source, content_sha, res, [], rejected, now)

    assets, types = _registry_view(db)
    seen: dict[tuple, float] = {}
    batch_max: dict[tuple, int] = {}
    valid_rows = []
    for i, raw in enumerate(records, start=1):
        def bad(reason, detail=""):
            rejected.append((i, reason, detail, raw if isinstance(raw, dict) else {"raw": str(raw)}))
        if not isinstance(raw, dict) or any(k not in raw for k in LONG_COLUMNS):
            bad("missing_fields", f"required fields {LONG_COLUMNS}")
            continue
        value = raw["value"]
        if value is None or (isinstance(value, str) and value.strip() == ""):
            res.rows_missing += 1
            continue
        a = assets.get(str(raw["asset"]))
        if a is None:
            bad("unknown_asset", str(raw["asset"])); continue
        if a == "AMBIGUOUS":
            bad("ambiguous_asset", f"{raw['asset']} is the id of one asset and the tag of another"); continue
        asset_id, type_id, status = a
        if status == "retired":
            bad("inactive_asset", asset_id); continue
        spec = types.get(type_id, {}).get(str(raw["signal"]))
        if spec is None:
            bad("unknown_signal", f"{raw['signal']} is not in the {type_id} contract"); continue
        if str(raw["unit"]) != spec.unit:
            bad("unit_mismatch", f"got {raw['unit']!r}, contract unit is {spec.unit!r}"); continue
        if isinstance(value, bool):
            bad("non_numeric_value", repr(value)); continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            bad("non_numeric_value", repr(value)); continue
        if not math.isfinite(v):
            bad("non_finite_value", repr(value)); continue
        try:
            ts = parse_ts(raw["timestamp"], default_tz)
        except NaiveTimestampError:
            bad("naive_timestamp", str(raw["timestamp"])); continue
        except (TypeError, ValueError):
            bad("unparseable_timestamp", str(raw["timestamp"])); continue
        if ts > now + max_future_skew_ms:
            bad("future_timestamp", f"{iso(ts)} is later than now + {max_future_skew_ms} ms"); continue
        key = (asset_id, spec.name, ts)
        if key in seen:
            if seen[key] == v:
                res.rows_duplicate += 1
            else:
                bad("conflicting_value", f"same batch already has {seen[key]} for this instant")
            continue
        seen[key] = v
        sk = (asset_id, spec.name)
        if sk in batch_max and ts < batch_max[sk]:
            res.rows_out_of_order += 1
        batch_max[sk] = max(batch_max.get(sk, ts), ts)
        quality = "good"
        if (spec.min is not None and v < spec.min) or (spec.max is not None and v > spec.max):
            quality = "suspect_out_of_range"
        valid_rows.append((asset_id, spec.name, ts, v, quality, i))
    return _record_batch(db, actor, source, content_sha, res, valid_rows, rejected, now)


def ingest_records(db, records: list[dict], source: str, actor: str, *, default_tz: str | None = None, now_ms: int | None = None,
                   max_future_skew_ms: int = 5 * 60 * 1000, lateness_ms: int = 60 * 60 * 1000) -> IngestResult:
    _check_params(default_tz)
    sha = hashlib.sha256(canonical({"records": records, "default_tz": default_tz, "contract": CONTRACT_VERSION}).encode("utf-8")).hexdigest()
    return _ingest(db, records, source, actor, sha, default_tz=default_tz, now_ms=now_ms, max_future_skew_ms=max_future_skew_ms, lateness_ms=lateness_ms)


def ingest_csv(db, path, source: str, actor: str, *, wide_units: dict | None = None, default_tz: str | None = None, now_ms: int | None = None,
               max_future_skew_ms: int = 5 * 60 * 1000, lateness_ms: int = 60 * 60 * 1000) -> IngestResult:
    _check_params(default_tz, wide_units)
    data = Path(path).read_bytes() if not isinstance(path, (bytes, bytearray)) else bytes(path)
    sha = hashlib.sha256(data + canonical({"wide_units": wide_units, "default_tz": default_tz, "contract": CONTRACT_VERSION}).encode("utf-8")).hexdigest()
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    cols = [c.strip().lower() for c in (reader.fieldnames or [])]
    reader.fieldnames = cols
    rows = list(reader)
    errors = []
    records: list[dict] = []
    if "signal" in cols and "value" in cols:
        missing = [c for c in LONG_COLUMNS if c not in cols]
        if missing:
            errors.append(("missing_columns", f"long format needs {LONG_COLUMNS}; missing {missing}"))
        else:
            if len(rows) > MAX_RECORDS_PER_BATCH:
                raise IngestLimitError(f"{len(rows)} rows; at most {MAX_RECORDS_PER_BATCH} per batch: split the file")
            records = [{k: r.get(k) for k in LONG_COLUMNS} for r in rows]
    else:
        missing = [c for c in ("asset", "timestamp") if c not in cols]
        signals = [c for c in cols if c not in ("asset", "timestamp")]
        units = wide_units or {}
        if missing:
            errors.append(("missing_columns", f"wide format needs asset and timestamp; missing {missing}"))
        elif not signals:
            errors.append(("missing_columns", "no signal columns"))
        elif [s for s in signals if s not in units]:
            errors.append(("missing_units", f"no unit declared for {[s for s in signals if s not in units]}"))
        else:
            if len(rows) * len(signals) > MAX_RECORDS_PER_BATCH:
                raise IngestLimitError(f"{len(rows)} rows x {len(signals)} signals = {len(rows) * len(signals)} readings; at most "
                                       f"{MAX_RECORDS_PER_BATCH} per batch: split the file")
            for r in rows:
                for s in signals:
                    records.append({"asset": r.get("asset"), "timestamp": r.get("timestamp"), "signal": s, "value": r.get(s), "unit": units[s]})
    return _ingest(db, records if not errors else [{}] * len(rows), source, actor, sha, default_tz=default_tz, now_ms=now_ms,
                   max_future_skew_ms=max_future_skew_ms, lateness_ms=lateness_ms, batch_errors=errors or None)


def staleness(db, now_ms: int | None = None, max_age_ms: int = 60 * 60 * 1000, site_id: str | None = None) -> list[dict]:
    """Required signals of active assets with no reading newer than max_age_ms (or none at all)."""
    now = int(now_ms if now_ms is not None else _now_ms())
    types = {t.asset_type_id: t for t in list_asset_types(db)}
    out = []
    with db.connect() as c:
        q = "SELECT asset_id, asset_type_id FROM assets WHERE status = 'active'" + (" AND site_id = ?" if site_id else "")
        for a in c.execute(q, (site_id,) if site_id else ()).fetchall():
            status = {r["signal"]: r["last_ts_ms"] for r in c.execute("SELECT signal, last_ts_ms FROM signal_status WHERE asset_id = ?", (a["asset_id"],))}
            for s in types[a["asset_type_id"]].signals:
                if not s.required:
                    continue
                last = status.get(s.name)
                if last is None or now - last > max_age_ms:
                    out.append({"asset_id": a["asset_id"], "signal": s.name, "last_ts": iso(last), "age_ms": None if last is None else now - last})
    return out


def batch(db, batch_id: str) -> dict | None:
    import json
    with db.connect() as c:
        r = c.execute("SELECT * FROM ingestion_batches WHERE batch_id = ?", (batch_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["errors"] = json.loads(d.pop("errors_json"))
    return d
