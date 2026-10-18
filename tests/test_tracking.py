import pytest

from sentinelloop import models, tracking


@pytest.mark.slow
def test_mlflow_sqlite_backend_logs_run_and_registers_alias(tmp_path):
    import numpy as np
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    tr = tracking.Tracker(uri, artifact_root=tmp_path / "mlruns", experiment="test-exp")
    X = np.random.default_rng(0).normal(size=(50, 3))
    y = X[:, 0] * 2 + 1
    m = models.train_point_model(X, y, max_iter=10, learning_rate=0.1, max_leaf_nodes=7, seed=0)
    run_id = tr.log_run(params={"a": 1}, metrics={"rmse": 1.23}, model=m, model_name="sentinelloop-test", alias="champion",
                        tags={"subset": "FD001"}, artifacts={"note.txt": "hello"})
    assert isinstance(run_id, str) and len(run_id) == 32
    v = tr.version_for_alias("sentinelloop-test", "champion")
    assert v is not None and tr.load_model("sentinelloop-test", "champion") is not None
    runs = tr.list_runs()
    assert any(r["run_id"] == run_id and r["metrics"].get("rmse") == 1.23 for r in runs)


@pytest.mark.slow
def test_alias_moves_to_the_newest_promoted_version(tmp_path):
    import numpy as np
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    tr = tracking.Tracker(uri, artifact_root=tmp_path / "mlruns", experiment="test-exp")
    X = np.random.default_rng(0).normal(size=(30, 2)); y = X[:, 0]
    m1 = models.train_point_model(X, y, max_iter=5, learning_rate=0.1, max_leaf_nodes=7, seed=0)
    m2 = models.train_point_model(X, y, max_iter=6, learning_rate=0.1, max_leaf_nodes=7, seed=0)
    tr.log_run(params={}, metrics={"rmse": 2.0}, model=m1, model_name="mdl", alias="champion")
    tr.log_run(params={}, metrics={"rmse": 1.0}, model=m2, model_name="mdl", alias="challenger")
    assert tr.version_for_alias("mdl", "champion") == 1 and tr.version_for_alias("mdl", "challenger") == 2
    tr.promote("mdl", 2)
    assert tr.version_for_alias("mdl", "champion") == 2


@pytest.mark.slow
def test_log_metrics_appends_metrics_to_an_existing_run(tmp_path):
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    tr = tracking.Tracker(uri, artifact_root=tmp_path / "mlruns", experiment="test-exp")
    run_id = tr.log_run(params={"a": 1}, metrics={"rmse": 1.0})
    tr.log_metrics(run_id, {"escalation_share_test": 0.15, "n_work_orders_batch": 37, "skipped": "text"})
    runs = {r["run_id"]: r for r in tr.list_runs()}
    assert runs[run_id]["metrics"]["escalation_share_test"] == 0.15 and runs[run_id]["metrics"]["n_work_orders_batch"] == 37
