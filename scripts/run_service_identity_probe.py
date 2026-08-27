#!/usr/bin/env python3
"""Run the frozen S3 service-identity diagnostic probe on exact S2 rows."""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.final_method import load_dataset, sha256_file
from src.rca.final_audit import S2_FEATURE_NAMES


def read_s2(path):
    with np.load(path) as data:
        candidates = tuple(str(value) for value in data["candidates"])
        features = np.asarray(data["features"], dtype=np.float64)
    if features.shape != (len(candidates), 16) or not np.isfinite(features).all():
        raise ValueError("S2 feature artifact must be finite N x 16")
    return candidates, features


def run_dataset(dataset, output_root):
    events, labels, roots, assignments = load_dataset(PROJECT_ROOT, dataset)
    feature_root = PROJECT_ROOT / "artifacts" / "final_audit" / "pre_event_features" / dataset
    all_rows = []
    fold_results = {}
    classes = sorted({candidate for event in events.values() for candidate in event.candidates})
    for fold in (0, 1, 2):
        train_x, train_y, test_x, test_y = [], [], [], []
        for case_id in sorted(events):
            candidates, features = read_s2(feature_root / (case_id + ".npz"))
            target = fold == assignments[case_id]
            x_out, y_out = (test_x, test_y) if target else (train_x, train_y)
            x_out.extend(features.tolist())
            y_out.extend(candidates)
        scaler = StandardScaler().fit(np.asarray(train_x, dtype=np.float64))
        model = LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=5000,
            class_weight=None, fit_intercept=True,
        )
        model.fit(scaler.transform(np.asarray(train_x)), np.asarray(train_y))
        pred = model.predict(scaler.transform(np.asarray(test_x)))
        fold_results[str(fold)] = {
            "top1_accuracy": float(accuracy_score(test_y, pred)),
            "macro_f1": float(f1_score(test_y, pred, labels=classes, average="macro", zero_division=0)),
            "train_rows": len(train_y),
            "test_rows": len(test_y),
            "train_event_count": sum(assignments[case_id] != fold for case_id in events),
            "test_event_count": sum(assignments[case_id] == fold for case_id in events),
            "classes_seen_train": sorted(set(train_y)),
            "classes_seen_test": sorted(set(test_y)),
        }
        all_rows.extend((y, p, fold) for y, p in zip(test_y, pred))
    y_true = [row[0] for row in all_rows]
    y_pred = [row[1] for row in all_rows]
    counts = {service: int(sum(label == service for label in y_true)) for service in classes}
    majority = max(counts.values()) / float(len(y_true))
    result = {
        "dataset": dataset,
        "input": "exact frozen S2 16D representation",
        "feature_dimension": 16,
        "feature_names": list(S2_FEATURE_NAMES),
        "top1_accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)),
        "number_of_classes": len(classes),
        "classes": classes,
        "empirical_class_distribution": counts,
        "uniform_reference_accuracy": 1.0 / float(len(classes)),
        "empirical_majority_class_accuracy": float(majority),
        "folds": fold_results,
        "model": {
            "class": "sklearn.linear_model.LogisticRegression",
            "penalty": "l2", "C": 1.0, "solver": "lbfgs", "max_iter": 5000,
            "class_weight": None, "fit_intercept": True,
            "sklearn_version": sklearn.__version__, "train_only_scaler": True,
        },
    }
    write_json(output_root / (dataset + ".json"), result)
    return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if subprocess.check_output(("git", "status", "--porcelain"), cwd=PROJECT_ROOT, text=True).strip():
        raise RuntimeError("S3 must be generated from a clean source commit")
    output = PROJECT_ROOT / "artifacts" / "final_audit" / "s3_service_identity"
    if output.exists():
        raise FileExistsError(str(output))
    source_commit = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip()
    results = {dataset: run_dataset(dataset, output) for dataset in ("re2ob", "re2tt")}
    write_json(output / "provenance.json", {
        "schema_version": "ada_rca_s3_service_identity_v1",
        "source_commit": source_commit,
        "protocol": "docs/RCA_FINAL_METHOD_FREEZE_V1.0.md",
        "s2_feature_manifests": {
            dataset: sha256_file(PROJECT_ROOT / "artifacts" / "final_audit" / "pre_event_features" / dataset / "manifest.json")
            for dataset in ("re2ob", "re2tt")
        },
        "split_manifests": {
            dataset: sha256_file(PROJECT_ROOT / "artifacts" / "splits" / dataset / "split_manifest.json")
            for dataset in ("re2ob", "re2tt")
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
    })
    write_json(output / "summary.json", results)
    checksums = {
        str(path.relative_to(output)): sha256_file(path)
        for path in sorted(output.rglob("*")) if path.is_file() and path.name != "checksums.json"
    }
    write_json(output / "checksums.json", checksums)
    print(json.dumps({dataset: {"top1_accuracy": result["top1_accuracy"], "macro_f1": result["macro_f1"], "majority": result["empirical_majority_class_accuracy"]} for dataset, result in results.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

