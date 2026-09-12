"""Frozen Z2 + XGBoost pairwise-ranking closure comparator."""

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .common import SEED, SupervisedEvent
from .xgb_ranker import XGB_CONFIG


Z2_XGB_CONFIG = dict(XGB_CONFIG)
Z2_XGB_CONFIG.update({
    "method": "z2_xgb_ranker",
    "input": "frozen Z2 68D only",
})

_MODEL_PARAMETER_KEYS = (
    "objective",
    "n_estimators",
    "max_depth",
    "learning_rate",
    "subsample",
    "colsample_bytree",
    "reg_lambda",
    "random_state",
    "n_jobs",
    "tree_method",
)


def scorer_parameters() -> Mapping[str, object]:
    """Return the exact Z1-XGB scorer parameters used by this comparator."""

    return {key: XGB_CONFIG[key] for key in _MODEL_PARAMETER_KEYS}


def build_grouped_training_matrix(
    train_events: Sequence[SupervisedEvent], train_roots: Mapping[str, str]
):
    """Build Z2 event groups without exposing test labels to prediction."""

    rows = []
    targets = []
    groups = []
    case_ids = []
    for event in train_events:
        if event.z2 is None:
            raise ValueError("Z2 input is missing from training event")
        root = train_roots[event.case_id]
        if root not in event.candidates:
            raise ValueError("training root absent from event candidates")
        rows.append(event.z2)
        targets.extend(int(candidate == root) for candidate in event.candidates)
        groups.append(len(event.candidates))
        case_ids.extend([event.case_id] * len(event.candidates))
    matrix = np.concatenate(rows, axis=0)
    target = np.asarray(targets, dtype=np.float32)
    group = np.asarray(groups, dtype=np.int32)
    if matrix.shape[1] != 68:
        raise ValueError("Z2 training matrix must have 68 columns")
    if int(group.sum()) != matrix.shape[0] or int(target.sum()) != len(train_events):
        raise ValueError("invalid Z2 XGBoost event groups")
    offset = 0
    for event, group_size in zip(train_events, group):
        if set(case_ids[offset:offset + int(group_size)]) != {event.case_id}:
            raise ValueError("Z2 XGBoost group crosses event boundary")
        offset += int(group_size)
    return matrix, target, group


def fit_score_and_save(
    train_events: Sequence[SupervisedEvent],
    train_roots: Mapping[str, str],
    test_events: Sequence[SupervisedEvent],
    run_dir: Path,
):
    """Fit the frozen scorer on Z2 and return label-free test scores."""

    import xgboost as xgb

    matrix, target, group = build_grouped_training_matrix(train_events, train_roots)
    model = xgb.XGBRanker(**scorer_parameters())
    model.fit(matrix, target, group=group, verbose=False)
    model.save_model(str(run_dir / "model_state.ubj"))
    scores = {}
    for event in test_events:
        if event.z2 is None:
            raise ValueError("Z2 input is missing from test event")
        scores[event.case_id] = np.asarray(model.predict(event.z2), dtype=np.float64)
    return scores
