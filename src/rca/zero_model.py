"""Fixed-capacity zero-model OOF learner for P3-A2."""

from typing import Mapping, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .features import CaseFeatureSet, deterministic_shuffle, flatten_features


VARIANTS = ("z0", "z1", "z2", "z3", "z3_shuffle")


def fit_predict_oof(
    cases: Mapping[str, CaseFeatureSet],
    labels: Mapping[str, Mapping[str, str]],
    fold_assignments: Mapping[str, int],
    variant: str,
) -> Tuple[Mapping[str, object], ...]:
    if variant not in VARIANTS:
        raise ValueError("unknown variant {!r}".format(variant))
    case_ids = sorted(cases)
    predictions = []
    for fold in range(3):
        train_rows = []
        train_targets = []
        for case_id in case_ids:
            if fold_assignments[case_id] == fold:
                continue
            feature_set = deterministic_shuffle(cases[case_id]) if variant == "z3_shuffle" else cases[case_id]
            values = flatten_features(feature_set, "z3" if variant == "z3_shuffle" else variant)
            root = labels[case_id]["root_service"]
            train_rows.append(values)
            train_targets.extend([1 if service == root else 0 for service in feature_set.candidates])
        x_train = np.concatenate(train_rows, axis=0)
        y_train = np.asarray(train_targets, dtype=int)
        scaler = StandardScaler().fit(x_train)
        model = LogisticRegression(C=1.0, max_iter=5000, solver="lbfgs", random_state=0)
        model.fit(scaler.transform(x_train), y_train)
        for case_id in case_ids:
            if fold_assignments[case_id] != fold:
                continue
            feature_set = deterministic_shuffle(cases[case_id]) if variant == "z3_shuffle" else cases[case_id]
            values = flatten_features(feature_set, "z3" if variant == "z3_shuffle" else variant)
            scores = model.decision_function(scaler.transform(values))
            order = sorted(range(len(feature_set.candidates)), key=lambda index: (-float(scores[index]), index))
            predictions.append({
                "case_id": case_id,
                "dataset": labels[case_id]["dataset"],
                "fault_type": labels[case_id]["fault_type"],
                "fold": fold,
                "root_service": labels[case_id]["root_service"],
                "candidate_scores": {service: float(scores[index]) for index, service in enumerate(feature_set.candidates)},
                "ranking": [feature_set.candidates[index] for index in order],
            })
    return tuple(sorted(predictions, key=lambda row: row["case_id"]))
