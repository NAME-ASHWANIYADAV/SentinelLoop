"""Point RUL models. HistGradientBoosting is the primary model (CPU-fast, explainable, retrains in
minutes). RandomForest and a naive mean predictor are baselines."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor


class ClippedRegressor:
    """Wraps a regressor so predictions are never negative (RUL cannot be below zero)."""

    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, X, y):
        self.estimator.fit(X, y)
        return self

    def predict(self, X):
        return np.clip(self.estimator.predict(X), 0.0, None)


class NaiveMean:
    def fit(self, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(len(X), self.mean_)


def train_point_model(X, y, max_iter: int = 400, learning_rate: float = 0.05, max_leaf_nodes: int = 31, seed: int = 42) -> ClippedRegressor:
    est = HistGradientBoostingRegressor(max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=max_leaf_nodes, random_state=seed)
    return ClippedRegressor(est).fit(X, y)


def train_quantile_model(X, y, quantile: float, max_iter: int = 400, learning_rate: float = 0.05, max_leaf_nodes: int = 31, seed: int = 42) -> ClippedRegressor:
    est = HistGradientBoostingRegressor(loss="quantile", quantile=quantile, max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=max_leaf_nodes, random_state=seed)
    return ClippedRegressor(est).fit(X, y)


def train_random_forest(X, y, n_estimators: int = 200, seed: int = 42, n_jobs: int = 4) -> ClippedRegressor:
    est = RandomForestRegressor(n_estimators=n_estimators, min_samples_leaf=5, random_state=seed, n_jobs=n_jobs)
    return ClippedRegressor(est).fit(X, y)
