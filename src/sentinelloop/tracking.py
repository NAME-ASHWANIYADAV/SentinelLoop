"""MLflow tracking and registry on a local SQLite backend with aliases (never stages, never the
file-store registry, which does not support the Model Registry)."""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import mlflow
import numpy as np
from mlflow.tracking import MlflowClient

from .models import ClippedRegressor

for _name in ("mlflow", "mlflow.tracking", "mlflow.models", "alembic", "alembic.runtime.migration"):
    logging.getLogger(_name).setLevel(logging.ERROR)   # keep the pipeline log readable (model-signature warnings, migration INFO lines)


class Tracker:
    def __init__(self, tracking_uri: str, artifact_root: str | Path, experiment: str = "sentinelloop"):
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_registry_uri(tracking_uri)
        self.client = MlflowClient(tracking_uri=tracking_uri, registry_uri=tracking_uri)
        art = Path(artifact_root).resolve()
        art.mkdir(parents=True, exist_ok=True)
        exp = self.client.get_experiment_by_name(experiment)
        if exp is None:
            self.experiment_id = self.client.create_experiment(experiment, artifact_location=art.as_uri())
        else:
            self.experiment_id = exp.experiment_id

    def log_run(self, params: dict, metrics: dict, model: ClippedRegressor | None = None, model_name: str | None = None,
                alias: str | None = None, tags: dict | None = None, artifacts: dict | None = None, run_name: str | None = None) -> str:
        with mlflow.start_run(experiment_id=self.experiment_id, run_name=run_name) as run:
            mlflow.log_params({k: str(v)[:250] for k, v in params.items()})
            mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool)})
            if tags:
                mlflow.set_tags({k: str(v) for k, v in tags.items()})
            if artifacts:
                with tempfile.TemporaryDirectory() as td:
                    for name, content in artifacts.items():
                        p = Path(td) / name
                        if isinstance(content, (str, bytes)) and not os.path.exists(str(content)):
                            p.write_text(content, encoding="utf-8") if isinstance(content, str) else p.write_bytes(content)
                            mlflow.log_artifact(str(p))
                        else:
                            mlflow.log_artifact(str(content))
            if model is not None:
                est = model.estimator if isinstance(model, ClippedRegressor) else model
                info = mlflow.sklearn.log_model(est, name="model", registered_model_name=model_name)
                if model_name and alias:
                    version = info.registered_model_version
                    self.client.set_registered_model_alias(model_name, alias, version)
            return run.info.run_id

    def log_metrics(self, run_id: str, metrics: dict) -> None:
        """Append numeric metrics to an existing run (post-agent metrics are known only after the model run was logged)."""
        for k, v in metrics.items():
            if isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool):
                self.client.log_metric(run_id, k, float(v))

    def set_tags(self, run_id: str, tags: dict) -> None:
        for k, v in tags.items():
            self.client.set_tag(run_id, k, str(v)[:250])

    def version_for_alias(self, model_name: str, alias: str) -> int | None:
        try:
            mv = self.client.get_model_version_by_alias(model_name, alias)
            return int(mv.version)
        except Exception:
            return None

    def promote(self, model_name: str, version: int, alias: str = "champion") -> None:
        self.client.set_registered_model_alias(model_name, alias, int(version))

    def load_model(self, model_name: str, alias: str) -> ClippedRegressor:
        est = mlflow.sklearn.load_model(f"models:/{model_name}@{alias}")
        return ClippedRegressor(est)

    def list_runs(self) -> list[dict]:
        runs = self.client.search_runs(experiment_ids=[self.experiment_id], order_by=["attributes.start_time DESC"], max_results=200)
        return [{"run_id": r.info.run_id, "run_name": r.info.run_name, "start_time": r.info.start_time, "status": r.info.status,
                 "metrics": dict(r.data.metrics), "params": dict(r.data.params), "tags": dict(r.data.tags)} for r in runs]

    def list_versions(self, model_name: str) -> list[dict]:
        out = []
        for mv in self.client.search_model_versions(f"name='{model_name}'"):
            out.append({"version": int(mv.version), "run_id": mv.run_id, "aliases": list(getattr(mv, "aliases", []) or []), "status": mv.status, "created": mv.creation_timestamp})
        return sorted(out, key=lambda x: x["version"])
