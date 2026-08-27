#!/usr/bin/env python3
"""Fit, persist, and exact-replay the frozen final Ada-RCA method."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import scipy
import sklearn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.final_method import (
    FINAL_Z2_DIMENSION,
    FINAL_Z2_FEATURE_NAMES,
    FINAL_Z2_FEATURE_ORDER_SHA256,
    PersistedFoldState,
    compare_predictions,
    fit_final_oof,
    load_dataset,
    load_fold_state,
    predict_with_persisted_states,
    read_jsonl,
    save_fold_state,
    sha256_file,
)
from src.rca.p4 import verify_complete_prediction
from src.rca.p4_stats import evaluate_predictions


DATASET_TREE_DIGESTS = {
    "re2ob": "ce48691243bcf4871abaedc49d5c7ffe45d51f66dcf669fec3da54e0aa60df8a",
    "re2tt": "84b26bcd083cea2db5c7d46330974c23d9ef963ed586ec9325c663baa5dd0958",
}
EXPECTED_METRICS = {
    "re2ob": {"AC@1": 0.8777777777777778, "AC@3": 0.9888888888888889, "AC@5": 0.9888888888888889, "Avg@5": 0.9622222222222222, "MRR": 0.9314814814814815},
    "re2tt": {"AC@1": 0.7111111111111111, "AC@3": 0.8666666666666667, "AC@5": 0.9333333333333333, "Avg@5": 0.8511111111111111, "MRR": 0.8034718882},
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def run(dataset, output_root):
    source_commit = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip()
    if subprocess.check_output(("git", "status", "--porcelain"), cwd=PROJECT_ROOT, text=True).strip():
        raise RuntimeError("final method must be generated from a clean source commit")
    events, labels, roots, assignments = load_dataset(PROJECT_ROOT, dataset)
    started = time.time()
    predictions, fits = fit_final_oof(events, roots, assignments)
    for row in predictions:
        row["fault_type"] = labels[row["case_id"]]["fault_type"]
        row["root_service"] = roots[row["case_id"]]
        verify_complete_prediction(row, events[row["case_id"]].candidates, roots[row["case_id"]])
    candidates_by_case = {case_id: event.candidates for case_id, event in events.items()}
    metrics = evaluate_predictions(predictions, candidates_by_case, roots)
    run_dir = PROJECT_ROOT / output_root / dataset
    if run_dir.exists():
        raise FileExistsError("final method artifact directory already exists: {}".format(run_dir))
    run_dir.mkdir(parents=True)

    state_metadata = {}
    for fold in (0, 1, 2):
        state = PersistedFoldState(
            fold=fold,
            fit=fits[fold],
            feature_names=FINAL_Z2_FEATURE_NAMES,
            l2_lambda=1.0,
            gradient_tolerance=1e-8,
            source_commit=source_commit,
            representation_provenance="docs/REPRESENTATION_FREEZE.md; artifacts/features/{}/manifest.json".format(dataset),
            split_provenance="artifacts/splits/{}/split_manifest.json".format(dataset),
            dataset_tree_sha256=DATASET_TREE_DIGESTS[dataset],
        )
        state_metadata[str(fold)] = save_fold_state(run_dir / "model_state" / ("fold_{}.npz".format(fold)), state)

    persisted_states = {
        fold: load_fold_state(run_dir / "model_state" / ("fold_{}.npz".format(fold)))
        for fold in (0, 1, 2)
    }
    persisted_predictions = predict_with_persisted_states(events, assignments, persisted_states)
    replay = compare_predictions(predictions, persisted_predictions)
    committed_p4 = read_jsonl(PROJECT_ROOT / "artifacts" / "p4_g0" / "predictions" / "a2" / dataset / "predictions.jsonl")
    p4_identity = compare_predictions(predictions, committed_p4)
    persisted_identity = compare_predictions(persisted_predictions, committed_p4)
    for row in persisted_predictions:
        row["fault_type"] = labels[row["case_id"]]["fault_type"]
        row["root_service"] = roots[row["case_id"]]
    persisted_metrics = evaluate_predictions(persisted_predictions, candidates_by_case, roots)
    metric_errors = {
        name: abs(float(persisted_metrics["overall_cases"][name]) - float(EXPECTED_METRICS[dataset][name]))
        for name in EXPECTED_METRICS[dataset]
    }
    integrity_valid = (
        len(predictions) == 90
        and all(fit.converged and fit.gradient_norm <= 1e-8 for fit in fits.values())
        and replay["ranking_identical"]
        and p4_identity["ranking_identical"]
        and persisted_identity["ranking_identical"]
        and persisted_identity["max_abs_score_difference"] <= 1e-12
        and max(metric_errors.values()) <= 1e-10
        and metrics["overall_cases"] == persisted_metrics["overall_cases"]
    )

    write_jsonl(run_dir / "predictions.jsonl", persisted_predictions)
    write_json(run_dir / "metrics.json", persisted_metrics)
    write_json(run_dir / "model_state_manifest.json", state_metadata)
    write_json(run_dir / "config.json", {
        "method": "Ada-RCA: Event-Relative Multimodal Morphology Ranking",
        "representation": "frozen Z2",
        "feature_dimension": FINAL_Z2_DIMENSION,
        "feature_names": list(FINAL_Z2_FEATURE_NAMES),
        "feature_order_sha256": FINAL_Z2_FEATURE_ORDER_SHA256,
        "lambda": 1.0,
        "optimizer": "scipy.optimize.minimize:L-BFGS-B with deterministic Newton polish",
        "max_iter": 1000,
        "gradient_tolerance": 1e-8,
        "scaler": "StandardScaler fitted on train-fold candidate rows only",
        "split": "frozen P3 repetition 3-fold OOF",
        "post_selection_disclosure": "Exact replay is identity/integrity verification, not fresh performance evidence.",
    })
    write_json(run_dir / "replay_audit.json", {
        "integrity_status": "INTEGRITY_VALID" if integrity_valid else "INTEGRITY_INVALID",
        "case_count": len(predictions),
        "complete_legal_rankings": True,
        "root_present_all_cases": True,
        "fit_to_persisted_replay": replay,
        "fresh_fit_to_committed_p4_a2": p4_identity,
        "persisted_state_to_committed_p4_a2": persisted_identity,
        "expected_metric_absolute_errors": metric_errors,
        "metrics_exact_between_fit_and_persisted_replay": metrics["overall_cases"] == persisted_metrics["overall_cases"],
        "all_folds_converged": all(fit.converged for fit in fits.values()),
        "max_gradient_norm": max(float(fit.gradient_norm) for fit in fits.values()),
        "score_tolerance": 1e-12,
    })
    write_json(run_dir / "provenance.json", {
        "schema_version": "ada_rca_final_method_v1",
        "dataset": dataset,
        "source_commit": source_commit,
        "representation_provenance": "docs/REPRESENTATION_FREEZE.md",
        "feature_manifest_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "features" / dataset / "manifest.json"),
        "split_manifest_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "splits" / dataset / "split_manifest.json"),
        "source_manifest_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "source" / dataset / "manifest.json"),
        "dataset_tree_sha256": DATASET_TREE_DIGESTS[dataset],
        "p4_a2_source_commit": json.loads((PROJECT_ROOT / "artifacts" / "p4_g0" / "predictions" / "a2" / dataset / "manifest.json").read_text(encoding="utf-8"))["git_commit"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    write_json(run_dir / "environment.json", {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "platform": platform.platform(),
    })
    write_json(run_dir / "runtime.json", {
        "elapsed_seconds": time.time() - started,
        "case_count": len(predictions),
        "candidate_row_count": sum(len(event.candidates) for event in events.values()),
    })
    checksums = {
        str(path.relative_to(run_dir)): sha256_file(path)
        for path in sorted(run_dir.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }
    write_json(run_dir / "checksums.json", checksums)
    print(json.dumps({"dataset": dataset, "metrics": persisted_metrics["overall_cases"], "replay": persisted_identity, "integrity_valid": integrity_valid}, indent=2, sort_keys=True))
    if not integrity_valid:
        raise RuntimeError("STOP: FINAL METHOD REPLAY INVALID")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, choices=("re2ob", "re2tt"))
    parser.add_argument("--output-root", default="artifacts/final_method")
    args = parser.parse_args()
    run(args.dataset, args.output_root)


if __name__ == "__main__":
    main()

