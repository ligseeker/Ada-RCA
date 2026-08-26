#!/usr/bin/env python3
"""Run all frozen P3-A2 logistic-regression OOF variants."""

import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import sklearn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.evaluator import aggregate_case_metrics, evaluate_case
from src.rca.features import CaseFeatureSet
from src.rca.zero_model import VARIANTS, fit_predict_oof


FAULT_ORDER = ("cpu", "mem", "disk", "socket", "delay", "loss")
SEED = 20260826


def git_output(*args):
    return subprocess.check_output(("git",) + args, cwd=str(PROJECT_ROOT), text=True).strip()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_feature_case(path: Path) -> CaseFeatureSet:
    with np.load(path) as data:
        return CaseFeatureSet(
            case_id=str(data["case_id"][0]),
            candidates=tuple(str(value) for value in data["candidates"]),
            a=np.asarray(data["a"], dtype=float),
            base=np.asarray(data["base"], dtype=float),
            z=np.asarray(data["z"], dtype=float),
            q_mask=np.asarray(data["q_mask"], dtype=float),
            morphology_active=np.asarray(data["morphology_active"], dtype=float),
            z2=np.asarray(data["z2"], dtype=float),
            z3=np.asarray(data["z3"], dtype=float),
        )


def evaluate_predictions(predictions):
    per_case = []
    for row in predictions:
        candidates = tuple(row["candidate_scores"].keys())
        metrics = evaluate_case(tuple(row["ranking"]), row["root_service"], candidates)
        per_case.append({**metrics, "case_id": row["case_id"], "fault_type": row["fault_type"]})
    overall = aggregate_case_metrics(per_case)
    by_fault = {
        fault: aggregate_case_metrics([row for row in per_case if row["fault_type"] == fault])
        for fault in FAULT_ORDER
    }
    fault_average = {
        key: sum(by_fault[fault][key] for fault in FAULT_ORDER) / len(FAULT_ORDER)
        for key in ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")
    }
    return {"overall_cases": overall, "by_fault": by_fault, "average_across_faults": fault_average, "case_metrics": per_case}


def dataset_identity(key: str):
    p3 = json.loads((PROJECT_ROOT / "artifacts" / "source" / "p3_r0_audit.json").read_text(encoding="utf-8"))
    return {
        "dataset_version": "Zenodo record 14590730",
        "dataset_checksum": p3["datasets"][key]["tree_sha256"],
        "RCAEval_commit": p3["rcaeval_source"]["commit"],
        "RCAEval_dirty_diff_sha256": p3["rcaeval_source"]["working_tree_diff_sha256"],
    }


def run_dataset_variant(key: str, variant: str, output_root: Path, git_commit: str):
    source = PROJECT_ROOT / "artifacts" / "source" / key
    labels_raw = read_jsonl(source / "labels.jsonl")
    labels = {row["case_id"]: {**row, "dataset": key} for row in labels_raw}
    assignment_rows = json.loads((PROJECT_ROOT / "artifacts" / "splits" / key / "assignments.json").read_text(encoding="utf-8"))
    assignments = {row["case_id"]: int(row["fold"]) for row in assignment_rows}
    cases = {
        case_id: load_feature_case(PROJECT_ROOT / "artifacts" / "features" / key / (case_id + ".npz"))
        for case_id in sorted(labels)
    }
    started = time.time()
    predictions = fit_predict_oof(cases, labels, assignments, variant)
    elapsed = time.time() - started
    metrics = evaluate_predictions(predictions)
    run_dir = output_root / variant / key
    if run_dir.exists():
        raise FileExistsError("formal run directory already exists: {}".format(run_dir))
    run_dir.mkdir(parents=True)
    config = {
        "variant": variant,
        "learner": "sklearn.linear_model.LogisticRegression",
        "penalty": "l2",
        "C": 1.0,
        "max_iter": 5000,
        "solver": "lbfgs",
        "random_state": 0,
        "scaler": "StandardScaler fit on train-fold candidate rows only",
        "folds": 3,
        "seed": SEED,
        "shuffle_policy": "SHA256(Ada-RCA|P3-G1|20260826|opaque_case_id)" if variant == "z3_shuffle" else None,
    }
    write_json(run_dir / "config.json", config)
    write_jsonl(run_dir / "predictions.jsonl", predictions)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "runtime.json", {"elapsed_seconds": elapsed, "cases": len(predictions), "candidate_rows": sum(len(row["ranking"]) for row in predictions)})
    write_json(run_dir / "environment.json", {
        "python": platform.python_version(), "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
    })
    identity = dataset_identity(key)
    manifest = {
        "experiment_id": "p3-a2-{}-{}-seed{}".format(variant, key, SEED),
        "git_commit": git_commit,
        "dataset": key,
        **identity,
        "seed": SEED,
        "command": "PYTHONPATH=. python3 -u scripts/p3_a2_zero_models.py --output-root artifacts/runs",
        "python_version": platform.python_version(),
        "dependencies": {"numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "representation_commit": "7cd6d418a114978b33838e788346febbeae71818",
        "feature_artifact_commit": "4fdea9da691ca738ffb706d3cc2141c7cca6f796",
        "split_commit": "bc414e62687043d7e91b114a86d11d066e497e7b",
        "oof": True,
    }
    write_json(run_dir / "manifest.json", manifest)
    checksums = {
        name: sha256(run_dir / name)
        for name in ("config.json", "predictions.jsonl", "metrics.json", "runtime.json", "environment.json", "manifest.json")
    }
    write_json(run_dir / "checksums.json", checksums)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="artifacts/runs")
    args = parser.parse_args()
    if git_output("status", "--short"):
        raise RuntimeError("formal P3-A2 run requires a clean worktree")
    git_commit = git_output("rev-parse", "HEAD")
    output_root = PROJECT_ROOT / args.output_root
    summary = {}
    for variant in VARIANTS:
        summary[variant] = {}
        for key in ("re2ob", "re2tt"):
            print("running {} {}".format(variant, key), flush=True)
            metrics = run_dataset_variant(key, variant, output_root, git_commit)
            summary[variant][key] = metrics["average_across_faults"]
            print("completed {} {} Avg@5={:.6f}".format(variant, key, metrics["average_across_faults"]["Avg@5"]), flush=True)
    write_json(output_root / "p3_a2_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
