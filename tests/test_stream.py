import numpy as np
import pandas as pd

from sentinelloop import clean, features, stream
from conftest import make_synthetic_raw


def test_incremental_features_match_batch_features():
    raw = make_synthetic_raw(n_units=2, cycles=(25, 30), degrade=True, seed=3)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    cleaned = state.transform(clean.impute(raw))
    cols = state.kept_sensors
    batch = features.build_features(cleaned, columns=cols, window=7)
    fs = stream.FeatureStream(columns=cols, window=7)
    rows = []
    for _, row in cleaned.sort_values(["cycle", "unit"]).iterrows():  # interleaved fleet order
        rows.append(fs.update(row))
    inc = pd.DataFrame(rows).sort_values(["unit", "cycle"]).reset_index(drop=True)
    fcols = [c for c in batch.columns if c.endswith(("_rm", "_rs", "_slope"))]
    assert np.allclose(inc[fcols].values, batch[fcols].values, atol=1e-9)


def test_batch_features_are_bit_identical_to_stream_features():
    """Tree models can flip a split on a 1e-12 difference, so batch and stream features must be the same bits."""
    raw = make_synthetic_raw(n_units=3, cycles=(25, 60, 9), degrade=True, seed=5)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    cleaned = state.transform(clean.impute(raw))
    cols = state.kept_sensors
    batch = features.build_features(cleaned, columns=cols, window=20)
    fs = stream.FeatureStream(columns=cols, window=20)
    rows = [fs.update(row) for _, row in cleaned.sort_values(["cycle", "unit"]).iterrows()]
    inc = pd.DataFrame(rows).sort_values(["unit", "cycle"]).reset_index(drop=True)
    fcols = [c for c in batch.columns if c.endswith(("_rm", "_rs", "_slope"))]
    assert np.array_equal(inc[fcols].to_numpy(), batch[fcols].to_numpy()), "features differ bitwise"
