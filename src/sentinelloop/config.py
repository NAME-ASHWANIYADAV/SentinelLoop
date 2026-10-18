"""Configuration loading: configs/default.yaml deep-merged with configs/<subset>.yaml."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

SUBSETS = ("FD001", "FD002", "FD003", "FD004")


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load(subset: str, config_dir: str | Path = "configs") -> dict[str, Any]:
    """Return the merged configuration dictionary for a subset."""
    if subset not in SUBSETS:
        raise ValueError(f"unknown subset {subset!r}; expected one of {SUBSETS}")
    config_dir = Path(config_dir)
    with open(config_dir / "default.yaml", encoding="utf-8") as fh:
        base = yaml.safe_load(fh) or {}
    sub_path = config_dir / f"{subset}.yaml"
    override: dict = {}
    if sub_path.exists():
        with open(sub_path, encoding="utf-8") as fh:
            override = yaml.safe_load(fh) or {}
    cfg = _deep_merge(base, override)
    cfg["subset"] = subset
    return cfg


def config_hash(cfg: dict) -> str:
    """Stable short hash of a configuration, recorded with every artefact."""
    blob = json.dumps(cfg, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]
