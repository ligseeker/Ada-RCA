#!/usr/bin/env python3
"""Run frozen P4-G0 bootstrap, LOSO, context, and subgroup diagnostics."""

import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import scipy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_p4_g0 import load_event
from src.rca.evaluator import aggregate_case_metrics, evaluate_case
from src.rca.p4 import CandidateEvent, build_candidate_representation, fit_conditional_logit, fit_predict_oof, foreign_context_percentiles, rank_candidates

DATASETS = ("re2ob", "re2tt")
VARIANTS = ("a0", "a1", "a2", "a3")
FAULTS = ("cpu", "mem", "disk", "socket", "delay", "loss")
REPRESENTATIONS = {"a0": ("z1", False), "a1": ("z1", True), "a2": ("z2", False), "a3": ("z2", True)}
COMPARISONS = {"A1-A0": ("a1", "a0"), "A3-A2": ("a3", "a2"), "A2-A0": ("a2", "a0"), "A3-A1": ("a3", "a1")}
SEED = 20260826
RESAMPLES = 10000


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def load_dataset(dataset):
    labels = {row["case_id"]: row for row in read_jsonl(PROJECT_ROOT / "artifacts" / "source" / dataset / "labels.jsonl")}
    assignments = {row["case_id"]: int(row["fold"]) for row in json.loads((PROJECT_ROOT / "artifacts" / "splits" / dataset / "assignments.json").read_text())}
    raw = {"z1": {}, "z2": {}}
    for case_id in sorted(labels):
        candidates, z1, z2 = load_event(PROJECT_ROOT / "artifacts" / "features" / dataset / (case_id + ".npz"))
        raw["z1"][case_id] = CandidateEvent(case_id, candidates, z1)
        raw["z2"][case_id] = CandidateEvent(case_id, candidates, z2)
    roots = {case_id: row["root_service"] for case_id, row in labels.items()}
    predictions = {variant: {row["case_id"]: row for row in read_jsonl(PROJECT_ROOT / "artifacts" / "p4_g0" / "predictions" / variant / dataset / "predictions.jsonl")} for variant in VARIANTS}
    return labels, assignments, raw, roots, predictions


def metric_row(prediction, candidates, root):
    return {**evaluate_case(tuple(prediction["ranking"]), root, candidates), "root_rank": prediction["ranking"].index(root) + 1}


def case_metric_maps(dataset_data):
    labels, _, raw, roots, predictions = dataset_data
    result = {}
    for variant in VARIANTS:
        representation = REPRESENTATIONS[variant][0]
        result[variant] = {}
        for case_id, prediction in predictions[variant].items():
            result[variant][case_id] = {**metric_row(prediction, raw[representation][case_id].candidates, roots[case_id]), "fault_type": labels[case_id]["fault_type"], "root_service": roots[case_id], "fold": prediction["fold"]}
    return result


def bootstrap_comparison(all_metrics, left, right, metric):
    rng = np.random.RandomState(SEED)
    samples = {dataset: np.empty(RESAMPLES, dtype=float) for dataset in DATASETS}
    deltas = {}
    for dataset in DATASETS:
        deltas[dataset] = {fault: np.asarray([all_metrics[dataset][left][case_id][metric] - all_metrics[dataset][right][case_id][metric] for case_id in sorted(all_metrics[dataset][left]) if all_metrics[dataset][left][case_id]["fault_type"] == fault], dtype=float) for fault in FAULTS}
        if any(values.size != 15 for values in deltas[dataset].values()):
            raise ValueError("bootstrap requires 15 cases in each fault stratum")
    for index in range(RESAMPLES):
        for dataset in DATASETS:
            samples[dataset][index] = float(np.mean(np.concatenate([values[rng.randint(0, 15, 15)] for values in deltas[dataset].values()])))
    mean_samples = (samples["re2ob"] + samples["re2tt"]) / 2.0
    result = {dataset: {"point_delta": float(np.mean(np.concatenate(list(deltas[dataset].values())))), "ci95": [float(np.percentile(samples[dataset], 2.5)), float(np.percentile(samples[dataset], 97.5))]} for dataset in DATASETS}
    result["mean_ob_tt"] = {"point_delta": float(np.mean([result[dataset]["point_delta"] for dataset in DATASETS])), "ci95": [float(np.percentile(mean_samples, 2.5)), float(np.percentile(mean_samples, 97.5))]}
    return result


def aggregate_delta(case_ids, left, right):
    case_ids = list(case_ids)
    if not case_ids:
        return {"cases": 0, "Avg@5": None, "AC@1": None, "root_rank": None}
    return {"cases": len(case_ids), "Avg@5": float(np.mean([left[case_id]["Avg@5"] - right[case_id]["Avg@5"] for case_id in case_ids])), "AC@1": float(np.mean([left[case_id]["AC@1"] - right[case_id]["AC@1"] for case_id in case_ids])), "root_rank": float(np.mean([left[case_id]["root_rank"] - right[case_id]["root_rank"] for case_id in case_ids]))}


def subgroup_diagnostics(all_metrics):
    mi = json.loads((PROJECT_ROOT / "artifacts" / "audits" / "magnitude_inversion.json").read_text())
    report = {}
    for dataset in DATASETS:
        membership = {row["case_id"]: row for row in mi[dataset]["cases"]}
        base = all_metrics[dataset]["a0"]
        report[dataset] = {"MI": {}, "fault": {}, "root": {}, "fold": {}}
        for name, key, expected in (("MI-1", "mi_1", True), ("non-MI-1", "mi_1", False), ("MI-3", "mi_3", True), ("non-MI-3", "mi_3", False)):
            ids = [case_id for case_id, row in membership.items() if bool(row[key]) == expected]
            report[dataset]["MI"][name] = {"A1-A0": aggregate_delta(ids, all_metrics[dataset]["a1"], all_metrics[dataset]["a0"]), "A3-A2": aggregate_delta(ids, all_metrics[dataset]["a3"], all_metrics[dataset]["a2"])}
        for group, field in (("fault", "fault_type"), ("root", "root_service"), ("fold", "fold")):
            for value in sorted({row[field] for row in base.values()}, key=str):
                ids = [case_id for case_id, row in base.items() if row[field] == value]
                report[dataset][group][str(value)] = {"A1-A0": aggregate_delta(ids, all_metrics[dataset]["a1"], all_metrics[dataset]["a0"]), "A3-A2": aggregate_delta(ids, all_metrics[dataset]["a3"], all_metrics[dataset]["a2"])}
    return report


def loso(dataset, dataset_data):
    labels, _, raw, roots, _ = dataset_data
    report = {"dataset": dataset, "variants": {}}
    for variant in ("a0", "a1"):
        representation, relative = REPRESENTATIONS[variant]
        represented = {case_id: CandidateEvent(event.case_id, event.candidates, build_candidate_representation(event.features, relative)) for case_id, event in raw[representation].items()}
        per_root, prediction_rows = {}, []
        for held_root in sorted(set(roots.values())):
            train = [represented[case_id] for case_id in sorted(represented) if roots[case_id] != held_root]
            test = [represented[case_id] for case_id in sorted(represented) if roots[case_id] == held_root]
            fit = fit_conditional_logit(train, roots, 1.0, 1000, 1e-8)
            rows = []
            for event in test:
                scores = fit.scores(event.features)
                ranking = list(rank_candidates(event.candidates, scores))
                row = {"case_id": event.case_id, "held_out_root": held_root, "fault_type": labels[event.case_id]["fault_type"], "root_service": roots[event.case_id], "candidate_scores": {candidate: float(scores[index]) for index, candidate in enumerate(event.candidates)}, "ranking": ranking}
                prediction_rows.append(row)
                rows.append(evaluate_case(ranking, roots[event.case_id], event.candidates))
            per_root[held_root] = aggregate_case_metrics(rows)
        report["variants"][variant] = {"per_root": per_root, "root_macro": {metric: float(np.mean([row[metric] for row in per_root.values()])) for metric in ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")}, "predictions": prediction_rows}
    report["A1-A0"] = {metric: report["variants"]["a1"]["root_macro"][metric] - report["variants"]["a0"]["root_macro"][metric] for metric in ("AC@1", "Avg@5")}
    report["per_root_delta"] = {root: {metric: report["variants"]["a1"]["per_root"][root][metric] - report["variants"]["a0"]["per_root"][root][metric] for metric in ("AC@1", "Avg@5")} for root in report["variants"]["a0"]["per_root"]}
    return report


def foreign_context(dataset, dataset_data):
    labels, assignments, raw, roots, persisted = dataset_data
    ordered = sorted(labels, key=lambda case_id: hashlib.sha256(case_id.encode("utf-8")).hexdigest())
    pairing = {case_id: ordered[(index + 1) % len(ordered)] for index, case_id in enumerate(ordered)}
    report = {"dataset": dataset, "pairing": pairing, "variants": {}}
    for variant in ("a1", "a3"):
        representation, _ = REPRESENTATIONS[variant]
        reconstructed, fits = fit_predict_oof(raw[representation], roots, assignments, True, 1.0, 1000, 1e-8)
        max_error = 0.0
        for row in reconstructed:
            saved = persisted[variant][row["case_id"]]
            if row["ranking"] != saved["ranking"]:
                raise ValueError("foreign replay ranking mismatch for {} {}".format(dataset, variant))
            for candidate, score in row["candidate_scores"].items():
                max_error = max(max_error, abs(float(score) - float(saved["candidate_scores"][candidate])))
        if max_error > 1e-12:
            raise ValueError("foreign replay score error exceeds tolerance: {}".format(max_error))
        foreign_rows, normal_metrics, foreign_metrics = [], [], []
        for case_id in sorted(labels):
            current = raw[representation][case_id]
            context = raw[representation][pairing[case_id]]
            values = np.concatenate((current.features, foreign_context_percentiles(current.features, context.features)), axis=1)
            scores = fits[assignments[case_id]].scores(values)
            ranking = list(rank_candidates(current.candidates, scores))
            foreign_rows.append({"case_id": case_id, "foreign_case_id": pairing[case_id], "fault_type": labels[case_id]["fault_type"], "root_service": roots[case_id], "candidate_scores": {candidate: float(scores[index]) for index, candidate in enumerate(current.candidates)}, "ranking": ranking})
            normal_metrics.append(evaluate_case(persisted[variant][case_id]["ranking"], roots[case_id], current.candidates))
            foreign_metrics.append(evaluate_case(ranking, roots[case_id], current.candidates))
        normal = aggregate_case_metrics(normal_metrics); foreign = aggregate_case_metrics(foreign_metrics)
        report["variants"][variant] = {"replay_max_abs_score_error": max_error, "replay_ranking_equal": True, "normal": normal, "foreign": foreign, "normal_minus_foreign": {metric: normal[metric] - foreign[metric] for metric in ("AC@1", "Avg@5")}, "predictions": foreign_rows}
    return report


def case_transitions(all_metrics):
    rows = []
    for dataset in DATASETS:
        for case_id in sorted(all_metrics[dataset]["a0"]):
            row = {"dataset": dataset, "case_id": case_id, "fault_type": all_metrics[dataset]["a0"][case_id]["fault_type"], "root_service": all_metrics[dataset]["a0"][case_id]["root_service"], "fold": all_metrics[dataset]["a0"][case_id]["fold"]}
            for comparison, (left, right) in COMPARISONS.items():
                row[comparison + "_rank_delta"] = all_metrics[dataset][left][case_id]["root_rank"] - all_metrics[dataset][right][case_id]["root_rank"]
                row[comparison + "_Avg5_delta"] = all_metrics[dataset][left][case_id]["Avg@5"] - all_metrics[dataset][right][case_id]["Avg@5"]
                row[comparison + "_AC1_delta"] = all_metrics[dataset][left][case_id]["AC@1"] - all_metrics[dataset][right][case_id]["AC@1"]
            rows.append(row)
    return rows


def main():
    started = time.time()
    data = {dataset: load_dataset(dataset) for dataset in DATASETS}
    all_metrics = {dataset: case_metric_maps(data[dataset]) for dataset in DATASETS}
    bootstrap = {"schema_version": "p4_g0_bootstrap_v1", "seed": SEED, "resamples": RESAMPLES, "sampling": "paired fault-stratified failure-case bootstrap; OB and TT independently resampled within each iteration", "comparisons": {}}
    for comparison, (left, right) in COMPARISONS.items():
        bootstrap["comparisons"][comparison] = {metric: bootstrap_comparison(all_metrics, left, right, metric) for metric in ("Avg@5", "AC@1")}
    subgroups = subgroup_diagnostics(all_metrics)
    loso_reports = {dataset: loso(dataset, data[dataset]) for dataset in DATASETS}
    foreign_reports = {dataset: foreign_context(dataset, data[dataset]) for dataset in DATASETS}
    transitions = case_transitions(all_metrics)
    metrics_summary = {dataset: {variant.upper(): json.loads((PROJECT_ROOT / "artifacts" / "p4_g0" / "predictions" / variant / dataset / "metrics.json").read_text())["overall_cases"] for variant in VARIANTS} for dataset in DATASETS}
    for dataset in DATASETS:
        metrics_summary[dataset]["effects"] = {comparison: {metric: metrics_summary[dataset][left.upper()][metric] - metrics_summary[dataset][right.upper()][metric] for metric in ("Avg@5", "AC@1")} for comparison, (left, right) in COMPARISONS.items()}
        metrics_summary[dataset]["interaction"] = {metric: metrics_summary[dataset]["effects"]["A3-A2"][metric] - metrics_summary[dataset]["effects"]["A1-A0"][metric] for metric in ("Avg@5", "AC@1")}
    output = PROJECT_ROOT / "artifacts" / "p4_g0"
    write_json(output / "bootstrap" / "p4_g0_bootstrap.json", bootstrap)
    write_json(output / "metrics" / "summary.json", metrics_summary)
    write_json(output / "metrics" / "subgroup_diagnostics.json", subgroups)
    with (output / "metrics" / "case_transitions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(transitions[0])); writer.writeheader(); writer.writerows(transitions)
    for dataset, report in loso_reports.items():
        write_json(output / "loso" / (dataset + ".json"), report)
    for dataset, report in foreign_reports.items():
        write_json(output / "foreign_context" / (dataset + ".json"), report)
    bindings = {dataset: {"feature_manifest": str(PROJECT_ROOT / "artifacts" / "features" / dataset / "manifest.json"), "split_manifest": str(PROJECT_ROOT / "artifacts" / "splits" / dataset / "split_manifest.json")} for dataset in DATASETS}
    write_json(output / "features" / "feature_manifest_bindings.json", bindings)
    write_json(output / "manifests" / "diagnostics_manifest.json", {"git_commit": subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip(), "seed": SEED, "resamples": RESAMPLES, "protocol_deviation": "docs/P4_PROTOCOL_DEVIATIONS.md#deviation-1-deterministic-model-state-reconstruction-for-foreign-context"})
    write_json(output / "environment" / "environment.json", {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform()})
    write_json(output / "runtime" / "diagnostics.json", {"elapsed_seconds": time.time() - started})
    print(json.dumps({"metrics": metrics_summary, "primary_bootstrap": bootstrap["comparisons"]["A1-A0"], "loso": {dataset: report["A1-A0"] for dataset, report in loso_reports.items()}, "foreign": {dataset: report["variants"]["a1"]["normal_minus_foreign"] for dataset, report in foreign_reports.items()}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
