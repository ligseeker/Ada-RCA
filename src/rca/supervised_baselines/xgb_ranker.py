"""Frozen Z1 + XGBoost pairwise-ranking supervised comparator."""

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .common import SEED, SupervisedEvent


XGB_CONFIG = {
    "method": "z1_xgb_ranker",
    "input": "frozen Z1 32D only",
    "learner": "xgboost.XGBRanker",
    "objective": "rank:pairwise",
    "n_estimators": 200,
    "max_depth": 3,
    "learning_rate": 0.05,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_lambda": 1.0,
    "random_state": SEED,
    "n_jobs": 1,
    "tree_method": "hist",
    "normalization": "none",
    "hyperparameter_search": False,
    "validation": None,
}


def build_grouped_training_matrix(
    train_events: Sequence[SupervisedEvent], train_roots: Mapping[str, str]
):
    """Build contiguous event groups without exposing labels to prediction code."""

    rows = []
    targets = []
    groups = []
    case_ids = []
    for event in train_events:
        root = train_roots[event.case_id]
        if root not in event.candidates:
            raise ValueError("training root absent from event candidates")
        rows.append(event.z1)
        targets.extend(int(candidate == root) for candidate in event.candidates)
        groups.append(len(event.candidates))
        case_ids.extend([event.case_id] * len(event.candidates))
    matrix = np.concatenate(rows, axis=0)
    target = np.asarray(targets, dtype=np.float32)
    group = np.asarray(groups, dtype=np.int32)
    if int(group.sum()) != matrix.shape[0] or int(target.sum()) != len(train_events):
        raise ValueError("invalid XGBoost event groups")
    offset = 0
    for event, group_size in zip(train_events, group):
        if set(case_ids[offset:offset + int(group_size)]) != {event.case_id}:
            raise ValueError("XGBoost group crosses event boundary")
        offset += int(group_size)
    return matrix, target, group


def fit_score_and_save(
    train_events: Sequence[SupervisedEvent],
    train_roots: Mapping[str, str],
    test_events: Sequence[SupervisedEvent],
    run_dir: Path,
):
    import xgboost as xgb

    matrix, target, group = build_grouped_training_matrix(train_events, train_roots)
    model = xgb.XGBRanker(
        objective="rank:pairwise",
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_lambda=1.0,
        random_state=SEED,
        n_jobs=1,
        tree_method="hist",
    )
    model.fit(matrix, target, group=group, verbose=False)
    model.save_model(str(run_dir / "model_state.ubj"))
    return {
        event.case_id: np.asarray(model.predict(event.z1), dtype=np.float64)
        for event in test_events
    }
