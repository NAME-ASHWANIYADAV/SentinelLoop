import numpy as np
import pandas as pd
import pytest

from sentinelloop import data
from conftest import COLUMNS, DATA_RAW, make_synthetic_raw


def test_column_names_follow_cmapss_layout():
    assert data.COLUMNS == COLUMNS
    assert len(data.COLUMNS) == 26


def test_validate_schema_accepts_well_formed_frame():
    df = make_synthetic_raw()
    data.validate_schema(df)  # must not raise


def test_validate_schema_rejects_wrong_column_count():
    df = make_synthetic_raw().drop(columns=["s21"])
    with pytest.raises(ValueError, match="26 columns"):
        data.validate_schema(df)


def test_validate_schema_rejects_non_monotone_cycles():
    df = make_synthetic_raw()
    df.loc[(df.unit == 1) & (df.cycle == 5), "cycle"] = 3
    with pytest.raises(ValueError, match="monotone"):
        data.validate_schema(df)


def test_validate_schema_rejects_cycles_not_starting_at_one():
    df = make_synthetic_raw()
    df = df[~((df.unit == 2) & (df.cycle == 1))]
    with pytest.raises(ValueError, match="start at 1"):
        data.validate_schema(df)


@pytest.mark.slow
def test_load_subset_fd001_has_expected_shape():
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    ds = data.load_subset("FD001", DATA_RAW)
    assert list(ds.train.columns) == COLUMNS
    assert ds.train.unit.nunique() == 100 and ds.test.unit.nunique() == 100
    assert len(ds.rul) == 100 and ds.rul.dtype.kind in "iu"
    assert ds.train.shape == (20631, 26) and ds.test.shape == (13096, 26)


@pytest.mark.slow
def test_dataset_hashes_are_recorded_for_fd001():
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    h = data.file_hashes("FD001", DATA_RAW)
    assert set(h) == {"train", "test", "rul"}
    assert all(len(v) == 64 for v in h.values())  # sha256 hex
