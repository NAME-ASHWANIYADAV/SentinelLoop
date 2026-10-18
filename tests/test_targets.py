import numpy as np
import pandas as pd

from sentinelloop import targets
from conftest import make_synthetic_raw


def test_train_rul_is_remaining_cycles_capped():
    df = make_synthetic_raw(n_units=1, cycles=(10,))
    out = targets.add_train_rul(df, cap=5)
    assert list(out["rul_raw"]) == [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    assert list(out["rul"]) == [5, 5, 5, 5, 5, 4, 3, 2, 1, 0]


def test_train_rul_is_per_unit():
    df = make_synthetic_raw(n_units=2, cycles=(3, 5))
    out = targets.add_train_rul(df, cap=125)
    assert list(out.loc[out.unit == 1, "rul_raw"]) == [2, 1, 0]
    assert list(out.loc[out.unit == 2, "rul_raw"]) == [4, 3, 2, 1, 0]


def test_test_truth_capped_and_raw():
    rul = np.array([130, 20, 125])
    capped, raw = targets.test_truth(rul, cap=125)
    assert list(capped) == [125, 20, 125]
    assert list(raw) == [130, 20, 125]
