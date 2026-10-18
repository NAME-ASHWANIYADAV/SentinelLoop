"""Loading, schema validation, hashing and download of the NASA C-MAPSS files.

Dataset: Saxena, Goebel, Simon, Eklund, "Damage Propagation Modeling for Aircraft Engine
Run-to-Failure Simulation", PHM08. Distributed by the NASA Prognostics Center of Excellence.
Terms: "License not specified" on data.nasa.gov; citation requested. We do not redistribute the
archive; this module downloads it and verifies the known checksum.
"""
from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SENSORS = [f"s{i}" for i in range(1, 22)]
OS_COLS = ["os1", "os2", "os3"]
COLUMNS = ["unit", "cycle"] + OS_COLS + SENSORS

S3_URL = "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
OUTER_ZIP_MD5 = "a83e8f128c59fc5614a4ca2e42a2e30c"   # equals the S3 ETag observed 2026-10-18
INNER_ZIP_MD5 = "79a22f36e80606c69d0e9e4da5bb2b7a"   # CMAPSSData.zip
OFFICIAL_PAGE = "https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data"


@dataclass
class Dataset:
    subset: str
    train: pd.DataFrame
    test: pd.DataFrame
    rul: np.ndarray  # true RUL at the last observed cycle of each test unit, in unit order


def read_cmapss_txt(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+", header=None)
    if df.shape[1] != 26:
        raise ValueError(f"{path}: expected 26 columns, found {df.shape[1]}")
    df.columns = COLUMNS
    df["unit"] = df["unit"].astype(int)
    df["cycle"] = df["cycle"].astype(int)
    return df


def validate_schema(df: pd.DataFrame) -> None:
    """Raise ValueError unless the frame has the C-MAPSS layout and consecutive cycles per unit."""
    if list(df.columns[: len(COLUMNS)]) != COLUMNS or df.shape[1] < 26:
        raise ValueError("expected the 26 columns unit, cycle, os1..os3, s1..s21 (26 columns)")
    for unit, g in df.groupby("unit", sort=True):
        cycles = g.sort_index()["cycle"].to_numpy()
        if cycles[0] != 1:
            raise ValueError(f"unit {unit}: cycles must start at 1")
        if not np.all(np.diff(cycles) > 0):
            raise ValueError(f"unit {unit}: cycles must be strictly monotone increasing")


def load_subset(subset: str, data_dir: str | Path = "data/raw") -> Dataset:
    data_dir = Path(data_dir)
    train = read_cmapss_txt(data_dir / f"train_{subset}.txt")
    test = read_cmapss_txt(data_dir / f"test_{subset}.txt")
    rul = pd.read_csv(data_dir / f"RUL_{subset}.txt", header=None)[0].to_numpy().astype(int)
    validate_schema(train)
    validate_schema(test)
    if len(rul) != test["unit"].nunique():
        raise ValueError(f"{subset}: RUL file has {len(rul)} rows but test has {test['unit'].nunique()} units")
    return Dataset(subset=subset, train=train, test=test, rul=rul)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def file_hashes(subset: str, data_dir: str | Path = "data/raw") -> dict[str, str]:
    data_dir = Path(data_dir)
    return {
        "train": _sha256(data_dir / f"train_{subset}.txt"),
        "test": _sha256(data_dir / f"test_{subset}.txt"),
        "rul": _sha256(data_dir / f"RUL_{subset}.txt"),
    }


def verify_archive(data_dir: str | Path = "data/raw") -> dict[str, bool]:
    """Check the archive checksums if the zips are present; return {name: ok}."""
    data_dir = Path(data_dir)
    out: dict[str, bool] = {}
    outer = data_dir / "pcoe_turbofan.zip"
    inner = data_dir / "CMAPSSData.zip"
    if outer.exists():
        out["pcoe_turbofan.zip"] = _md5(outer) == OUTER_ZIP_MD5
    if inner.exists():
        out["CMAPSSData.zip"] = _md5(inner) == INNER_ZIP_MD5
    return out


def download(data_dir: str | Path = "data/raw", url: str = S3_URL) -> Path:
    """Download the official archive, verify the checksum, extract the txt files. Returns data_dir."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    outer = data_dir / "pcoe_turbofan.zip"
    if not outer.exists() or _md5(outer) != OUTER_ZIP_MD5:
        with urllib.request.urlopen(url, timeout=120) as resp:
            outer.write_bytes(resp.read())
    if _md5(outer) != OUTER_ZIP_MD5:
        raise RuntimeError(f"checksum mismatch for {outer}: expected {OUTER_ZIP_MD5}")
    with zipfile.ZipFile(outer) as zf:
        inner_name = next(n for n in zf.namelist() if n.endswith("CMAPSSData.zip"))
        inner_bytes = zf.read(inner_name)
    inner = data_dir / "CMAPSSData.zip"
    inner.write_bytes(inner_bytes)
    if _md5(inner) != INNER_ZIP_MD5:
        raise RuntimeError(f"checksum mismatch for {inner}: expected {INNER_ZIP_MD5}")
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith(".txt") or name.endswith(".pdf"):
                (data_dir / Path(name).name).write_bytes(zf.read(name))
    return data_dir


def stream_rows(df: pd.DataFrame):
    """Yield rows cycle by cycle, interleaving units (a replayed fleet stream)."""
    df = df.sort_values(["cycle", "unit"]).reset_index(drop=True)
    for _, row in df.iterrows():
        yield row
