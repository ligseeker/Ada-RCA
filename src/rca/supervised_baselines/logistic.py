"""Frozen Z1 + logistic-regression supervised comparator."""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .common import SEED, SupervisedEvent


LOGISTIC_CONFIG = {
    "method": "z1_logistic",
    "input": "frozen Z1 32D only",
    "learner": "sklearn.linear_model.LogisticRegression",
    "penalty": "l2",
    "C": 1.0,
    "solver": "lbfgs",
    "max_iter": 5000,
    "class_weight": None,
    "random_state": SEED,
    "normalization": "StandardScaler fit on outer-training candidate rows only",
    "hyperparameter_search": False,
}


@dataclass
class LogisticScorer:
    scaler: StandardScaler
    model: LogisticRegression

    def score(self, event: SupervisedEvent) -> np.ndarray:
        transformed = self.scaler.transform(event.z1)
        positive_index = int(np.flatnonzero(self.model.classes_ == 1)[0])
        return self.model.predict_proba(transformed)[:, positive_index]


def fit_logistic(
    train_events: Sequence[SupervisedEvent], train_roots: Mapping[str, str]
) -> LogisticScorer:
    train_rows = np.concatenate([event.z1 for event in train_events], axis=0)
    targets = np.concatenate([
        np.asarray([int(candidate == train_roots[event.case_id]) for candidate in event.candidates])
        for event in train_events
    ])
    scaler = StandardScaler().fit(train_rows)
    model = LogisticRegression(
        penalty="l2",
        C=1.0,
        solver="lbfgs",
        max_iter=5000,
        class_weight=None,
        random_state=SEED,
    )
    model.fit(scaler.transform(train_rows), targets)
    return LogisticScorer(scaler, model)


def fit_score_and_save(
    train_events: Sequence[SupervisedEvent],
    train_roots: Mapping[str, str],
    test_events: Sequence[SupervisedEvent],
    run_dir: Path,
):
    scorer = fit_logistic(train_events, train_roots)
    np.savez(
        run_dir / "model_state.npz",
        scaler_mean=np.asarray(scorer.scaler.mean_, dtype=np.float64),
        scaler_scale=np.asarray(scorer.scaler.scale_, dtype=np.float64),
        classes=np.asarray(scorer.model.classes_),
        coefficient=np.asarray(scorer.model.coef_, dtype=np.float64),
        intercept=np.asarray(scorer.model.intercept_, dtype=np.float64),
        iterations=np.asarray(scorer.model.n_iter_),
    )
    return {event.case_id: scorer.score(event) for event in test_events}
