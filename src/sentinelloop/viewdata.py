"""Read-only access to pipeline artefacts for the dashboard (no computation beyond sorting)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .agent import SEVERITY_ORDER


@dataclass
class Bundle:
    subset: str
    metrics: dict = field(default_factory=dict)
    predictions: pd.DataFrame = field(default_factory=pd.DataFrame)
    decisions: pd.DataFrame = field(default_factory=pd.DataFrame)
    stream: pd.DataFrame = field(default_factory=pd.DataFrame)
    orders: list = field(default_factory=list)
    drift: dict = field(default_factory=dict)
    conformal: dict = field(default_factory=dict)
    anomaly: dict = field(default_factory=dict)
    audit: list = field(default_factory=list)
    retrain_log: list = field(default_factory=list)


def available_subsets(out_dir: str | Path) -> list[str]:
    out_dir = Path(out_dir)
    if not out_dir.exists():
        return []
    return sorted(p.name for p in out_dir.iterdir() if p.is_dir() and (p / "metrics.json").exists())


def _json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except json.JSONDecodeError:
        return default


def _csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_bundle(out_dir: str | Path, subset: str) -> Bundle:
    out_dir = Path(out_dir)
    d = out_dir / subset
    b = Bundle(subset=subset)
    if not d.exists():
        return b
    b.metrics = _json(d / "metrics.json", {})
    b.predictions = _csv(d / "predictions_test_all_cycles.csv")
    b.decisions = _csv(d / "decisions_test.csv")
    b.stream = _csv(d / "decisions_stream.csv")
    b.orders = _json(d / "work_orders.json", [])
    b.drift = _json(d / "drift_reference.json", {})
    b.conformal = _json(d / "conformal.json", {})
    b.anomaly = _json(d / "anomaly.json", {})
    b.retrain_log = _json(d / "retrain_log.json", [])
    for audit_path in (out_dir / "audit" / f"decisions_{subset}.jsonl", out_dir / "audit" / "decisions.jsonl"):
        if audit_path.exists():
            b.audit = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            break
    return b


def fleet_table(b: Bundle) -> pd.DataFrame:
    if b.decisions.empty:
        return pd.DataFrame(columns=["unit", "severity", "rul_lower", "rul_point"])
    cols = [c for c in ["unit", "severity", "rul_lower", "rul_point", "rul_upper", "action", "escalate", "reasons", "rules", "quality_flag", "imputed_frac", "drift_flag",
                        "anomaly_flag", "anomaly_score", "top_sensors", "order_event", "rul_true_capped", "cycle"] if c in b.decisions.columns]
    t = b.decisions[cols].copy()
    for c in ("reasons", "top_sensors"):
        if c in t.columns:
            t[c] = t[c].fillna("").astype(str)   # pandas reads an empty CSV field as NaN
    t["_rank"] = t["severity"].map(SEVERITY_ORDER).fillna(0)
    t = t.sort_values(["_rank", "rul_lower"], ascending=[False, True]).drop(columns="_rank").reset_index(drop=True)
    return t


def engine_trace(b: Bundle, unit: int) -> pd.DataFrame:
    if b.predictions.empty:
        return pd.DataFrame()
    return b.predictions[b.predictions["unit"] == unit].sort_values("cycle").reset_index(drop=True)


def load_experiment_summaries(root: str | Path) -> dict[str, dict]:
    root = Path(root)
    out: dict[str, dict] = {}
    if not root.exists():
        return out
    for p in sorted(root.iterdir()):
        s = p / "summary.json"
        if p.is_dir() and s.exists():
            out[p.name] = _json(s, {})
    return out
