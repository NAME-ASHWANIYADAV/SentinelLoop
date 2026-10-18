"""Feature drift (Population Stability Index per feature) and input-quality monitoring.

Only FEATURE drift can be computed live: residual drift needs true RUL, which is unknown for a
running engine until it fails, so it is evaluated retrospectively on completed engines.
Critical columns (the operating settings) raise the alarm on their own: a changed operating regime is
a known-cause shift that the model may not have seen, however small its share of all features.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def early_life_rows(df: pd.DataFrame, warmup: int, max_cycle: int) -> pd.DataFrame:
    """Age-matched window: rows with warmup <= cycle <= max_cycle. Every engine starts healthy, so the
    early-life distribution is comparable across fleets regardless of how far each engine has been
    observed; comparing whole populations would confound drift with the fleet's age mix."""
    return df[(df["cycle"] >= warmup) & (df["cycle"] <= max_cycle)]


def psi(ref: np.ndarray, cur: np.ndarray, bins: int = 10, eps: float = 1e-6) -> float:
    ref = np.asarray(ref, dtype=float)
    cur = np.asarray(cur, dtype=float)
    ref = ref[~np.isnan(ref)]
    cur = cur[~np.isnan(cur)]
    if len(ref) == 0 or len(cur) == 0:
        return 0.0
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        # constant reference: the share of current values that differ from it, scaled to the PSI range
        return float(np.mean(cur != edges[0]) * 10.0)
    edges[0], edges[-1] = -np.inf, np.inf
    p_ref = np.histogram(ref, bins=edges)[0] / len(ref)
    p_cur = np.histogram(cur, bins=edges)[0] / len(cur)
    p_ref = np.clip(p_ref, eps, None)
    p_cur = np.clip(p_cur, eps, None)
    return float(np.sum((p_cur - p_ref) * np.log(p_cur / p_ref)))


@dataclass
class DriftReport:
    drift_share: float
    per_feature: dict[str, float]
    drifted_features: list[str]
    alarm: bool
    n_rows: int
    critical_drift: list[str] = field(default_factory=list)
    severe_drift: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"drift_share": self.drift_share, "per_feature": self.per_feature, "drifted_features": self.drifted_features,
                "alarm": self.alarm, "n_rows": self.n_rows, "critical_drift": self.critical_drift, "severe_drift": self.severe_drift}

    @property
    def reasons(self) -> list[str]:
        out = []
        if self.drift_share > 0 and self.alarm and not self.critical_drift and not self.severe_drift:
            out.append("feature_share")
        if self.critical_drift:
            out.append("operating_setting")
        if self.severe_drift:
            out.append("severe_single_feature")
        return out


@dataclass
class DriftMonitor:
    columns: list[str]
    reference: dict[str, np.ndarray]
    ref_min: dict[str, float]
    ref_max: dict[str, float]
    psi_threshold: float
    share_threshold: float
    bins: int = 10
    range_margin: float = 0.25
    critical_columns: list[str] = field(default_factory=list)
    severe_psi_threshold: float = 1.0

    @classmethod
    def fit(cls, ref_df: pd.DataFrame, psi_threshold: float = 0.2, share_threshold: float = 0.3, bins: int = 10, max_ref_rows: int = 20000,
            seed: int = 42, critical_columns: list[str] | None = None, severe_psi_threshold: float = 1.0,
            range_ref: pd.DataFrame | None = None) -> "DriftMonitor":
        """`ref_df` is the PSI reference (e.g. age-matched early-life rows). `range_ref` (default: ref_df) is the
        reference for the out-of-range quality check and should cover the whole training distribution, so that
        a legitimately degraded engine is not flagged as out of range."""
        cols = list(ref_df.columns)
        if len(ref_df) > max_ref_rows:
            ref_df = ref_df.sample(max_ref_rows, random_state=seed)
        reference = {c: ref_df[c].to_numpy(dtype=float) for c in cols}
        rr = range_ref if range_ref is not None else ref_df
        return cls(columns=cols, reference=reference, ref_min={c: float(np.nanmin(rr[c].to_numpy(dtype=float))) for c in cols},
                   ref_max={c: float(np.nanmax(rr[c].to_numpy(dtype=float))) for c in cols}, psi_threshold=psi_threshold,
                   share_threshold=share_threshold, bins=bins, critical_columns=[c for c in (critical_columns or []) if c in cols],
                   severe_psi_threshold=severe_psi_threshold)

    def check(self, cur_df: pd.DataFrame) -> DriftReport:
        """Alarm when (a) the share of drifted features exceeds share_threshold, or (b) any critical
        column (operating setting) drifts, or (c) any single feature shows severe drift (PSI above
        severe_psi_threshold, e.g. a biased sensor)."""
        per = {c: psi(self.reference[c], cur_df[c].to_numpy(dtype=float), self.bins) for c in self.columns if c in cur_df.columns}
        drifted = [c for c, v in per.items() if v > self.psi_threshold]
        share = len(drifted) / max(1, len(per))
        critical = [c for c in self.critical_columns if per.get(c, 0.0) > self.psi_threshold]
        severe = [c for c, v in per.items() if v > self.severe_psi_threshold and c not in self.critical_columns]
        return DriftReport(drift_share=float(share), per_feature={c: float(v) for c, v in per.items()}, drifted_features=drifted,
                           alarm=bool(share > self.share_threshold or critical or severe), n_rows=int(len(cur_df)), critical_drift=critical, severe_drift=severe)

    def quality(self, cur_df: pd.DataFrame) -> dict:
        cols = [c for c in self.columns if c in cur_df.columns]
        vals = cur_df[cols].to_numpy(dtype=float)
        n_cells = vals.size
        missing = int(np.isnan(vals).sum())
        oor = 0
        crit_oor, crit_cells = 0, 0
        for j, c in enumerate(cols):
            span = self.ref_max[c] - self.ref_min[c]
            lo = self.ref_min[c] - self.range_margin * span
            hi = self.ref_max[c] + self.range_margin * span
            v = vals[:, j]
            bad = int(np.sum((v < lo) | (v > hi)))
            oor += bad
            if c in self.critical_columns:
                crit_oor += bad
                crit_cells += len(v)
        return {"missing_frac": missing / max(1, n_cells), "out_of_range_frac": oor / max(1, n_cells),
                "critical_out_of_range_frac": crit_oor / max(1, crit_cells), "n_rows": int(len(cur_df))}
