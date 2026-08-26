#!/usr/bin/env python3
"""Run one frozen P4-G0 deterministic OOF variant for one dataset."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import scipy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.p4 import CandidateEvent, fit_predict_oof
from src.rca.p4_stats import evaluate_predictions

VARIANTS = {"a0": ("z1", False), "a1": ("z1", True), "a2": ("z2", False), "a3": ("z2", True)}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_event(path):
    with np.load(path) as data:
        candidates = tuple(str(value) for value in data["candidates"])
        z1 = np.asarray(data["base"], dtype=np.float64).reshape(len(candidates), -1)
        z2 = np.concatenate((np.asarray(data["base"], dtype=np.float64), np.asarray(data["z2"], dtype=np.float64)), axis=2).reshape(len(candidates), -1)
        return candidates, z1, z2


def run(dataset, variant, output_root, overwrite=False):
    if dataset not in ("re2ob", "re2tt") or variant not in VARIANTS:
        raise ValueError("dataset must be re2ob/re2tt and variant must be a0/a1/a2/a3")
    source = PROJECT_ROOT / "artifacts" / "source" / dataset
    labels = {row["case_id"]: row for row in read_jsonl(source / "labels.jsonl")}
    assignments = {row["case_id"]: int(row["fold"]) for row in json.loads((PROJECT_ROOT / "artifacts" / "splits" / dataset / "assignments.json").read_text())}
    representation, relative = VARIANTS[variant]
    events, candidates_by_case = {}, {}
    for case_id in sorted(labels):
        candidates, z1, z2 = load_event(PROJECT_ROOT / "artifacts" / "features" / dataset / (case_id + ".npz"))
        events[case_id] = CandidateEvent(case_id, candidates, z1 if representation == "z1" else z2)
        candidates_by_case[case_id] = candidates
    roots = {case_id: row["root_service"] for case_id, row in labels.items()}
    started = time.time()
    predictions, fits = fit_predict_oof(events, roots, assignments, relative, l2_lambda=1.0, max_iter=1000, gradient_tolerance=1e-8)
    elapsed = time.time() - started
    for row in predictions:
        row["fault_type"] = labels[row["case_id"]]["fault_type"]
        row["root_service"] = roots[row["case_id"]]
    metrics = evaluate_predictions(predictions, candidates_by_case, roots)
    run_dir = PROJECT_ROOT / output_root / variant / dataset
    if run_dir.exists() and not overwrite:
        raise FileExistsError("formal run already exists: {}".format(run_dir))
    run_dir.mkdir(parents=True, exist_ok=overwrite)
    files = {
        "predictions.jsonl": "".join(json.dumps(row, sort_keys=True) + "\n" for row in predictions),
        "metrics.json": json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        "model_input_manifest.json": json.dumps({"label_free": True, "dataset": dataset, "variant": variant, "case_count": len(events), "feature_dimensions": sorted({event.features.shape[1] for event in events.values()})}, indent=2, sort_keys=True) + "\n",
        "fit_summary.json": json.dumps({str(fold): {"initial_loss": fit.initial_loss, "final_loss": fit.final_loss, "gradient_norm": fit.gradient_norm, "iterations": fit.iterations, "converged": fit.converged, "message": fit.message} for fold, fit in fits.items()}, indent=2, sort_keys=True) + "\n",
        "config.json": json.dumps({"variant": variant, "representation": representation, "relative": relative, "lambda": 1.0, "optimizer": "scipy.optimize.minimize:L-BFGS-B", "max_iter": 1000, "gradient_tolerance": 1e-8, "scaler": "StandardScaler train-fold candidate rows only", "split": "frozen P3 3-fold OOF", "seed": 20260826}, indent=2, sort_keys=True) + "\n",
        "runtime.json": json.dumps({"elapsed_seconds": elapsed, "cases": len(predictions), "candidate_rows": sum(len(row["ranking"]) for row in predictions)}, indent=2, sort_keys=True) + "\n",
        "environment.json": json.dumps({"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}, indent=2, sort_keys=True) + "\n",
    }
    for name, content in files.items():
        (run_dir / name).write_text(content, encoding="utf-8")
    manifest = {"schema_version": "p4_g0_run_v1", "dataset": dataset, "variant": variant, "git_commit": subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip(), "dataset_manifest_sha256": sha256(source / "manifest.json"), "split_manifest_sha256": sha256(PROJECT_ROOT / "artifacts" / "splits" / dataset / "split_manifest.json"), "feature_manifest_sha256": sha256(PROJECT_ROOT / "artifacts" / "features" / dataset / "manifest.json"), "timestamp": datetime.now(timezone.utc).isoformat()}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = {path.name: sha256(path) for path in run_dir.iterdir() if path.is_file() and path.name != "checksums.json"}
    (run_dir / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics["overall_cases"], indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--variant", required=True, choices=tuple(VARIANTS))
    parser.add_argument("--output-root", default="artifacts/p4_g0/predictions")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    run(args.dataset, args.variant, args.output_root, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
