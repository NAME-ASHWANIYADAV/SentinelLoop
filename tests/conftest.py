"""Shared fixtures: small synthetic C-MAPSS-like frames and paths to the real data."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"

SENSORS = [f"s{i}" for i in range(1, 22)]
COLUMNS = ["unit", "cycle", "os1", "os2", "os3"] + SENSORS


def make_synthetic_raw(n_units: int = 3, cycles=(30, 40, 25), seed: int = 0, degrade: bool = True) -> pd.DataFrame:
    """Synthetic run-to-failure data: sensor s2 degrades linearly with cycle; s1 constant; others noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(1, n_units + 1):
        n = cycles[(u - 1) % len(cycles)]
        for c in range(1, n + 1):
            row = {"unit": u, "cycle": c, "os1": rng.normal(0, 0.001), "os2": rng.normal(0, 0.0003), "os3": 100.0}
            for s in SENSORS:
                row[s] = rng.normal(500, 1.0)
            row["s1"] = 518.67  # constant sensor
            if degrade:
                row["s2"] = 640.0 + 0.5 * c + rng.normal(0, 0.2)  # degrades with age
                row["s3"] = 1580.0 - 0.3 * c + rng.normal(0, 0.2)
            rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNS)


@pytest.fixture
def synthetic_raw() -> pd.DataFrame:
    return make_synthetic_raw()


@pytest.fixture
def real_data_available() -> bool:
    return (DATA_RAW / "train_FD001.txt").exists()
