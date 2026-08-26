#!/usr/bin/env python3
"""Run the preregistered paired, fault-balanced bootstrap for P3-G1."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAULTS = ("cpu", "mem", "disk", "socket", "delay", "loss")
SEED = 20260826
RESAMPLES = 10000


def git_output(*args):
    return subprocess.check_output(("git",) + args, cwd=str(PROJECT_ROOT), text=True).strip()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_avg5(variant: str, dataset: str):
    rows = read_jsonl(PROJECT_ROOT / "artifacts" / "runs" / variant / dataset / "predictions.jsonl")
    values = {}
    for row in rows:
        root = row["root_service"]
        ranking = row["ranking"]
        rank = ranking.index(root) + 1
        values[row["case_id"]] = {
            "fault_type": row["fault_type"],
            "avg5": sum(float(rank <= k) for k in range(1, 6)) / 5.0,
        }
    if len(values) != 90:
        raise ValueError("{} {} does not contain 90 predictions".format(variant, dataset))
    return values


def paired_bootstrap(dataset: str, left: str, right: str, rng: np.random.RandomState):
    left_values = load_avg5(left, dataset)
    right_values = load_avg5(right, dataset)
    if set(left_values) != set(right_values):
        raise ValueError("paired case IDs differ for {} and {}".format(left, right))
    deltas_by_fault = {
        fault: np.asarray(
            [left_values[case_id]["avg5"] - right_values[case_id]["avg5"] for case_id in sorted(left_values) if left_values[case_id]["fault_type"] == fault],
            dtype=float,
        )
        for fault in FAULTS
    }
    if any(values.size != 15 for values in deltas_by_fault.values()):
        raise ValueError("fault strata are not 15 cases each")
    point = float(np.mean(np.concatenate(tuple(deltas_by_fault.values()))))
    samples = np.empty(RESAMPLES, dtype=float)
    for index in range(RESAMPLES):
        sampled = [values[rng.randint(0, values.size, size=values.size)] for values in deltas_by_fault.values()]
        samples[index] = float(np.mean(np.concatenate(sampled)))
    summary = {
        "dataset": dataset,
        "left": left,
        "right": right,
        "point_delta_avg5": point,
        "ci95": [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))],
        "resamples": RESAMPLES,
        "seed": SEED,
        "fault_case_counts": {fault: int(values.size) for fault, values in deltas_by_fault.items()},
        "delta_by_fault": {fault: float(np.mean(values)) for fault, values in deltas_by_fault.items()},
    }
    return summary, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/bootstrap/p3_g1_bootstrap.json")
    args = parser.parse_args()
    if git_output("status", "--short"):
        raise RuntimeError("formal bootstrap requires a clean worktree")
    rng = np.random.RandomState(SEED)
    comparisons = {}
    for left, right, name in (("z3", "z1", "z3_minus_z1"), ("z3", "z3_shuffle", "z3_minus_z3_shuffle")):
        dataset_results = {}
        dataset_samples = {}
        for dataset in ("re2ob", "re2tt"):
            dataset_results[dataset], dataset_samples[dataset] = paired_bootstrap(dataset, left, right, rng)
        comparisons[name] = dataset_results
        comparisons[name]["mean_ob_tt"] = {
            "point_delta_avg5": float(np.mean([dataset_results[dataset]["point_delta_avg5"] for dataset in ("re2ob", "re2tt")])),
            "ci95": [
                float(np.percentile((dataset_samples["re2ob"] + dataset_samples["re2tt"]) / 2.0, 2.5)),
                float(np.percentile((dataset_samples["re2ob"] + dataset_samples["re2tt"]) / 2.0, 97.5)),
            ],
            "resamples": RESAMPLES,
            "seed": SEED,
        }
    report = {
        "schema_version": "p3_g1_bootstrap_v1",
        "git_commit": git_output("rev-parse", "HEAD"),
        "python": platform.python_version(),
        "seed": SEED,
        "resamples": RESAMPLES,
        "sampling": "fault-stratified paired case bootstrap; 15 cases per fault sampled with replacement",
        "comparisons": comparisons,
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
