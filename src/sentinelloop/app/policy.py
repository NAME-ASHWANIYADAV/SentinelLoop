"""Platform policy (configs/platform.yaml): defaults merged with per-asset-type overrides, versioned by hash."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from .states import Thresholds


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@dataclass(frozen=True)
class Policy:
    asset_type_id: str
    assessment: dict
    risk: dict
    states: Thresholds
    version: int
    sha256: str

    def to_record(self) -> dict:
        return {"asset_type_id": self.asset_type_id, "version": self.version, "sha256": self.sha256, "assessment": self.assessment,
                "risk": self.risk, "states": {"p_inspect": self.states.p_inspect, "p_urgent": self.states.p_urgent,
                                              "dq_clear_after": self.states.dq_clear_after}}


class PolicySet:
    def __init__(self, raw: dict, source: str = ""):
        self.raw, self.source = raw, source
        self.version = int(raw.get("policy_version", 0))

    def for_type(self, asset_type_id: str) -> Policy:
        resolved = _merge(self.raw["defaults"], (self.raw.get("asset_types") or {}).get(asset_type_id, {}))
        sha = hashlib.sha256(json.dumps({"v": self.version, "type": asset_type_id, "p": resolved}, sort_keys=True).encode()).hexdigest()
        st = resolved["states"]
        return Policy(asset_type_id, resolved["assessment"], resolved["risk"],
                      Thresholds(p_inspect=float(st["p_inspect"]), p_urgent=float(st["p_urgent"]), dq_clear_after=int(st["dq_clear_after"])),
                      self.version, sha)


def load(path) -> PolicySet:
    p = Path(path)
    return PolicySet(yaml.safe_load(p.read_text(encoding="utf-8")), source=str(p))
