#!/usr/bin/env python3
"""Run frozen S0/S1/S2 controls and paired scientific comparisons."""

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

from src.rca.final_audit import (
    S1_FEATURE_NAMES,
    S2_FEATURE_NAMES,
    aggregate_expected,
    attach_labels,
    comparison_bootstrap,
    fit_control_oof,
    observability_event,
    pre_event_only_event,
    s0_rankings,
)
from src.rca.final_method import load_dataset, read_jsonl, sha256_file
from src.rca.p4 import verify_complete_prediction
from src.rca.p4_stats import evaluate_predictions


def read_rows(path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def persist_fit_states(path, fits, feature_names):
    path.mkdir(parents=True, exist_ok=True)
    summary = {}
    for fold, fit in fits.items():
        np.savez(path / ("fold_{}.npz".format(fold)), weights=fit.weights, scaler_mean=fit.scaler_mean, scaler_scale=fit.scaler_scale)
        summary[str(fold)] = {
            "feature_dimension": len(feature_names),
            "feature_names": list(feature_names),
            "lambda": 1.0,
            "converged": fit.converged,
            "gradient_norm": fit.gradient_norm,
            "initial_loss": fit.initial_loss,
            "final_loss": fit.final_loss,
            "iterations": fit.iterations,
            "message": fit.message,
        }
    write_json(path / "manifest.json", summary)


def main():
    source_commit = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip()
    if subprocess.check_output(("git", "status", "--porcelain"), cwd=PROJECT_ROOT, text=True).strip():
        raise RuntimeError("controls must be generated from a clean source commit")
    output = PROJECT_ROOT / "artifacts" / "final_audit"
    if output.exists():
        raise FileExistsError(str(output))
    started = time.time()
    dataset_results = {}
    final_case_metrics = {}
    control_case_metrics = {name: {} for name in ("s0_deterministic", "s0_tie_neutral", "s1", "s2")}

    for dataset in ("re2ob", "re2tt"):
        events, labels, roots, assignments = load_dataset(PROJECT_ROOT, dataset)
        candidates_by_case = {case_id: event.candidates for case_id, event in events.items()}
        final_metrics = json.loads((PROJECT_ROOT / "artifacts" / "final_method" / dataset / "metrics.json").read_text(encoding="utf-8"))
        final_case_metrics[dataset] = final_metrics["case_metrics"]

        deterministic, tie_neutral, seen_sizes = s0_rankings(events, roots, assignments)
        deterministic = attach_labels(deterministic, labels)
        for row in deterministic:
            verify_complete_prediction(row, candidates_by_case[row["case_id"]], roots[row["case_id"]])
        s0_det_metrics = evaluate_predictions(deterministic, candidates_by_case, roots)
        s0_tie_metrics = aggregate_expected(tie_neutral, labels)

        s1_events = {}
        for case_id in sorted(events):
            with np.load(PROJECT_ROOT / "artifacts" / "features" / dataset / (case_id + ".npz")) as data:
                s1_events[case_id] = observability_event(case_id, events[case_id].candidates, data["base"])
        s1_predictions, s1_fits = fit_control_oof(s1_events, roots, assignments)
        s1_predictions = attach_labels(s1_predictions, labels)
        s1_metrics = evaluate_predictions(s1_predictions, candidates_by_case, roots)

        input_rows = {str(row["case_id"]): row for row in read_rows(PROJECT_ROOT / "artifacts" / "source" / dataset / "inputs.jsonl")}
        source_rows = {str(row["case_id"]): row for row in read_rows(PROJECT_ROOT / "artifacts" / "source" / dataset / "sources.jsonl")}
        s2_events = {}
        feature_dir = output / "pre_event_features" / dataset
        feature_dir.mkdir(parents=True, exist_ok=True)
        for index, case_id in enumerate(sorted(events), start=1):
            s2_events[case_id] = pre_event_only_event(
                case_id,
                events[case_id].candidates,
                float(input_rows[case_id]["anchor_time"]),
                source_rows[case_id],
            )
            np.savez_compressed(
                feature_dir / (case_id + ".npz"),
                case_id=np.asarray([case_id]),
                candidates=np.asarray(s2_events[case_id].candidates),
                features=s2_events[case_id].features,
            )
            if index % 30 == 0:
                print("{} S2 extraction {}/90".format(dataset, index), flush=True)
        s2_predictions, s2_fits = fit_control_oof(s2_events, roots, assignments)
        s2_predictions = attach_labels(s2_predictions, labels)
        s2_metrics = evaluate_predictions(s2_predictions, candidates_by_case, roots)

        for name, metrics in (
            ("s0_deterministic", s0_det_metrics),
            ("s0_tie_neutral", s0_tie_metrics),
            ("s1", s1_metrics),
            ("s2", s2_metrics),
        ):
            control_case_metrics[name][dataset] = metrics["case_metrics"]

        dataset_dir = output / "controls" / dataset
        write_jsonl(dataset_dir / "s0_deterministic_predictions.jsonl", deterministic)
        write_json(dataset_dir / "s0_deterministic_metrics.json", s0_det_metrics)
        write_json(dataset_dir / "s0_tie_neutral_metrics.json", s0_tie_metrics)
        write_json(dataset_dir / "s0_seen_roots.json", seen_sizes)
        write_jsonl(dataset_dir / "s1_predictions.jsonl", s1_predictions)
        write_json(dataset_dir / "s1_metrics.json", s1_metrics)
        persist_fit_states(dataset_dir / "s1_model_state", s1_fits, S1_FEATURE_NAMES)
        write_jsonl(dataset_dir / "s2_predictions.jsonl", s2_predictions)
        write_json(dataset_dir / "s2_metrics.json", s2_metrics)
        persist_fit_states(dataset_dir / "s2_model_state", s2_fits, S2_FEATURE_NAMES)
        write_json(feature_dir / "manifest.json", {
            "dataset": dataset,
            "case_count": len(s2_events),
            "feature_dimension": 16,
            "feature_names": list(S2_FEATURE_NAMES),
            "window": "[t0-600,t0)",
            "post_event_information_used": False,
            "source_files": ["simple_metrics.csv", "logts.csv", "tracets_err.csv", "tracets_lat.csv"],
            "normalization": "frozen pre-event robust indicator normalization",
            "aggregation": "frozen service/channel Q90",
        })
        dataset_results[dataset] = {
            "final": final_metrics["overall_cases"],
            "s0_deterministic": s0_det_metrics["overall_cases"],
            "s0_tie_neutral": s0_tie_metrics["overall_cases"],
            "s1": s1_metrics["overall_cases"],
            "s2": s2_metrics["overall_cases"],
            "s0_seen_root_sizes": {fold: row["size"] for fold, row in seen_sizes.items()},
            "s1_max_gradient_norm": max(float(fit.gradient_norm) for fit in s1_fits.values()),
            "s2_max_gradient_norm": max(float(fit.gradient_norm) for fit in s2_fits.values()),
        }

    comparisons = {}
    for control in control_case_metrics:
        avg = comparison_bootstrap(final_case_metrics, control_case_metrics[control], "Avg@5")
        ac1 = comparison_bootstrap(final_case_metrics, control_case_metrics[control], "AC@1")
        comparisons[control] = {"Avg@5": avg, "AC@1": ac1, "state": avg["state"]}
    write_json(output / "control_comparisons.json", comparisons)
    write_json(output / "summary.json", {"datasets": dataset_results, "comparisons": comparisons})
    write_json(output / "provenance.json", {
        "schema_version": "ada_rca_final_controls_v1",
        "source_commit": source_commit,
        "protocol": "docs/RCA_FINAL_METHOD_FREEZE_V1.0.md",
        "seed": 20260827,
        "resamples": 10000,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feature_manifests": {dataset: sha256_file(PROJECT_ROOT / "artifacts" / "features" / dataset / "manifest.json") for dataset in ("re2ob", "re2tt")},
        "split_manifests": {dataset: sha256_file(PROJECT_ROOT / "artifacts" / "splits" / dataset / "split_manifest.json") for dataset in ("re2ob", "re2tt")},
    })
    write_json(output / "environment.json", {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "platform": platform.platform(),
    })
    write_json(output / "runtime.json", {"elapsed_seconds": time.time() - started})
    checksums = {
        str(path.relative_to(output)): sha256_file(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }
    write_json(output / "checksums.json", checksums)
    print(json.dumps({
        "metrics": dataset_results,
        "states": {control: report["state"] for control, report in comparisons.items()},
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

