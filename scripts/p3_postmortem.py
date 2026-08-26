#!/usr/bin/env python3
"""Frozen P3-M exploratory post-mortem from committed P3 artifacts only."""

import argparse
import csv
import json
from pathlib import Path
import subprocess

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS = ("re2ob", "re2tt")
VARIANTS = ("z1", "z2", "z3")
FAULTS = ("cpu", "mem", "disk", "socket", "delay", "loss")
SEED = 20260826
RESAMPLES = 10000


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def case_metrics(row):
    rank = row["ranking"].index(row["root_service"]) + 1
    return {"rank": rank, "AC@1": float(rank <= 1), "AC@3": float(rank <= 3), "AC@5": float(rank <= 5), "Avg@5": sum(float(rank <= k) for k in range(1, 6)) / 5.0, "MRR": 1.0 / rank}


def load_predictions():
    data = {}
    for dataset in DATASETS:
        data[dataset] = {}
        for variant in VARIANTS:
            rows = read_jsonl(PROJECT_ROOT / "artifacts" / "runs" / variant / dataset / "predictions.jsonl")
            if len(rows) != 90 or len({row["case_id"] for row in rows}) != 90:
                raise ValueError("{} {} is not a complete 90-case OOF artifact".format(dataset, variant))
            data[dataset][variant] = {row["case_id"]: {**row, **case_metrics(row)} for row in rows}
    return data


def bootstrap_metric(left, right, metric):
    by_fault = {fault: [] for fault in FAULTS}
    for case_id in sorted(left):
        by_fault[left[case_id]["fault_type"]].append(left[case_id][metric] - right[case_id][metric])
    if any(len(values) != 15 for values in by_fault.values()):
        raise ValueError("bootstrap strata must contain 15 cases per fault")
    rng = np.random.RandomState(SEED)
    arrays = {fault: np.asarray(values, dtype=float) for fault, values in by_fault.items()}
    samples = np.empty(RESAMPLES, dtype=float)
    for index in range(RESAMPLES):
        samples[index] = np.mean(np.concatenate([values[rng.randint(0, 15, 15)] for values in arrays.values()]))
    return {"point_delta": float(np.mean(np.concatenate(list(arrays.values())))), "ci95": [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))], "resamples": RESAMPLES, "seed": SEED, "fault_stratified": True}


def aggregate(rows):
    rows = list(rows)
    if not rows:
        return {"status": "NOT_AVAILABLE_ZERO_CASES", "cases": 0}
    return {"cases": len(rows), "AC@1": float(np.mean([row["AC@1"] for row in rows])), "AC@3": float(np.mean([row["AC@3"] for row in rows])), "AC@5": float(np.mean([row["AC@5"] for row in rows])), "Avg@5": float(np.mean([row["Avg@5"] for row in rows])), "MRR": float(np.mean([row["MRR"] for row in rows])), "mean_root_rank": float(np.mean([row["rank"] for row in rows]))}


def transition_label(left_rank, right_rank):
    return "improved" if right_rank < left_rank else "degraded" if right_rank > left_rank else "unchanged"


def build_transitions(predictions):
    rows = []
    for dataset in DATASETS:
        for case_id in sorted(predictions[dataset]["z1"]):
            variants = {name: predictions[dataset][name][case_id] for name in VARIANTS}
            row = {"dataset": dataset, "case_id": case_id, "fault_type": variants["z1"]["fault_type"], "root_service": variants["z1"]["root_service"], "fold": variants["z1"]["fold"]}
            for variant, value in variants.items():
                root = value["root_service"]
                scores = value["candidate_scores"]
                best_nonroot = max(float(score) for candidate, score in scores.items() if candidate != root)
                row[variant + "_rank"] = value["rank"]
                row[variant + "_root_margin"] = float(scores[root]) - best_nonroot
            row["z2_vs_z1"] = transition_label(row["z1_rank"], row["z2_rank"])
            row["z3_vs_z1"] = transition_label(row["z1_rank"], row["z3_rank"])
            for k in (1, 3, 5):
                row["z2_top{}_gained".format(k)] = int(row["z1_rank"] > k and row["z2_rank"] <= k)
                row["z2_top{}_lost".format(k)] = int(row["z1_rank"] <= k and row["z2_rank"] > k)
                row["z3_top{}_gained".format(k)] = int(row["z1_rank"] > k and row["z3_rank"] <= k)
                row["z3_top{}_lost".format(k)] = int(row["z1_rank"] <= k and row["z3_rank"] > k)
            rows.append(row)
    return rows


def subset_analysis(predictions, mi):
    report = {}
    for dataset in DATASETS:
        membership = {row["case_id"]: row for row in mi[dataset]["cases"]}
        report[dataset] = {}
        for subset, key, expected in (("MI-1", "mi_1", True), ("non-MI-1", "mi_1", False), ("MI-3", "mi_3", True), ("non-MI-3", "mi_3", False)):
            case_ids = [case_id for case_id, row in membership.items() if bool(row[key]) == expected]
            report[dataset][subset] = {variant: aggregate(predictions[dataset][variant][case_id] for case_id in case_ids) for variant in VARIANTS}
            report[dataset][subset]["z2_minus_z1"] = {metric: report[dataset][subset]["z2"].get(metric, float("nan")) - report[dataset][subset]["z1"].get(metric, float("nan")) for metric in ("Avg@5", "AC@1", "mean_root_rank")}
    return report


def group_analysis(predictions):
    report = {}
    for dataset in DATASETS:
        report[dataset] = {}
        reference = predictions[dataset]["z1"]
        group_specs = {"fault": "fault_type", "root": "root_service", "fold": "fold"}
        for group_name, field in group_specs.items():
            values = sorted({row[field] for row in reference.values()}, key=str)
            report[dataset][group_name] = {}
            for value in values:
                case_ids = [case_id for case_id, row in reference.items() if row[field] == value]
                entry = {variant: aggregate(predictions[dataset][variant][case_id] for case_id in case_ids) for variant in VARIANTS}
                entry["z2_minus_z1"] = {metric: entry["z2"][metric] - entry["z1"][metric] for metric in ("Avg@5", "AC@1", "mean_root_rank")}
                entry["z3_minus_z1"] = {metric: entry["z3"][metric] - entry["z1"][metric] for metric in ("Avg@5", "AC@1", "mean_root_rank")}
                report[dataset][group_name][str(value)] = entry
    return report


def coverage_analysis(predictions, transitions):
    transition_map = {(row["dataset"], row["case_id"]): row["z2_vs_z1"] for row in transitions}
    report = {}
    for dataset in DATASETS:
        rows = []
        for case_id in sorted(predictions[dataset]["z1"]):
            with np.load(PROJECT_ROOT / "artifacts" / "features" / dataset / (case_id + ".npz")) as data:
                base = np.asarray(data["base"], dtype=float)
                q_mask = np.asarray(data["q_mask"], dtype=float)
                active = np.asarray(data["morphology_active"], dtype=float)
            rows.append({"case_id": case_id, "q_observed_ratio": float(q_mask.mean()), "channel_available_ratio": float((base[:, :, 7] > 0).mean()), "morphology_active_ratio": float(active.mean()), "z2_vs_z1": transition_map[(dataset, case_id)], "rank_gain": float(predictions[dataset]["z1"][case_id]["rank"] - predictions[dataset]["z2"][case_id]["rank"])})
        report[dataset] = {"status": "AVAILABLE_FROM_FROZEN_FEATURE_ARTIFACTS", "overall": {key: float(np.mean([row[key] for row in rows])) for key in ("q_observed_ratio", "channel_available_ratio", "morphology_active_ratio")}, "by_transition": {state: {"cases": sum(row["z2_vs_z1"] == state for row in rows), **{key: float(np.mean([row[key] for row in rows if row["z2_vs_z1"] == state])) if any(row["z2_vs_z1"] == state for row in rows) else None for key in ("q_observed_ratio", "channel_available_ratio", "morphology_active_ratio")}} for state in ("improved", "degraded", "unchanged")}, "rank_gain_correlation": {key: float(np.corrcoef([row[key] for row in rows], [row["rank_gain"] for row in rows])[0, 1]) for key in ("q_observed_ratio", "channel_available_ratio", "morphology_active_ratio")}}
    return report


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="artifacts/postmortem")
    parser.add_argument("--doc", default="docs/P3_POSTMORTEM.md")
    args = parser.parse_args()
    predictions = load_predictions()
    mi = json.loads((PROJECT_ROOT / "artifacts" / "audits" / "magnitude_inversion.json").read_text())
    output_root = PROJECT_ROOT / args.output_root
    bootstrap = {"schema_version": "p3_m_z2_vs_z1_bootstrap_v1", "status": "EXPLORATORY_ONLY", "seed": SEED, "resamples": RESAMPLES, "datasets": {}}
    for dataset in DATASETS:
        bootstrap["datasets"][dataset] = {metric: bootstrap_metric(predictions[dataset]["z2"], predictions[dataset]["z1"], metric) for metric in ("Avg@5", "AC@1")}
    bootstrap["two_dataset_descriptive_mean"] = {metric: float(np.mean([bootstrap["datasets"][dataset][metric]["point_delta"] for dataset in DATASETS])) for metric in ("Avg@5", "AC@1")}
    transitions = build_transitions(predictions)
    subset = subset_analysis(predictions, mi)
    groups = group_analysis(predictions)
    coverage = coverage_analysis(predictions, transitions)
    write_json(output_root / "z2_vs_z1_bootstrap.json", bootstrap)
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "case_rank_transitions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(transitions[0]))
        writer.writeheader(); writer.writerows(transitions)
    write_json(output_root / "mi_subset_analysis.json", subset)
    write_json(output_root / "fault_root_fold_analysis.json", groups)
    write_json(output_root / "coverage_analysis.json", coverage)
    summaries = {}
    for dataset in DATASETS:
        dataset_rows = [row for row in transitions if row["dataset"] == dataset]
        summaries[dataset] = {"z2_vs_z1_transitions": {state: sum(row["z2_vs_z1"] == state for row in dataset_rows) for state in ("improved", "degraded", "unchanged")}, "top_transitions": {"top{}_gained".format(k): sum(row["z2_top{}_gained".format(k)] for row in dataset_rows) for k in (1, 3, 5)}, "top_lost": {"top{}_lost".format(k): sum(row["z2_top{}_lost".format(k)] for row in dataset_rows) for k in (1, 3, 5)}}
    document = """# P3 Exploratory Post-Mortem\n\nStatus: **EXPLORATORY ONLY**. P4-G0 protocol, implementation, tests, and configs were committed before this analysis. These results cannot modify P4.\n\n## Z2-Z1 paired bootstrap\n\n| Dataset | Avg@5 delta [95% CI] | AC@1 delta [95% CI] |\n|---|---:|---:|\n"""
    for dataset in DATASETS:
        avg = bootstrap["datasets"][dataset]["Avg@5"]; ac1 = bootstrap["datasets"][dataset]["AC@1"]
        document += "| {} | {:+.6f} [{:+.6f}, {:+.6f}] | {:+.6f} [{:+.6f}, {:+.6f}] |\n".format(dataset.upper(), avg["point_delta"], *avg["ci95"], ac1["point_delta"], *ac1["ci95"])
    document += "\nTwo-dataset descriptive mean: Avg@5 {:+.6f}; AC@1 {:+.6f}. No untouched confirmation claim is made.\n\n## Case transitions\n\n".format(bootstrap["two_dataset_descriptive_mean"]["Avg@5"], bootstrap["two_dataset_descriptive_mean"]["AC@1"])
    for dataset in DATASETS:
        document += "- {} Z2 vs Z1: {}.\n".format(dataset.upper(), summaries[dataset])
    document += "\n## MI, fault, root, fold, and coverage\n\nDetailed pre-specified exploratory outputs are preserved in `artifacts/postmortem/mi_subset_analysis.json`, `fault_root_fold_analysis.json`, and `coverage_analysis.json`. Coverage status is `AVAILABLE_FROM_FROZEN_FEATURE_ARTIFACTS`. Interpret heterogeneity descriptively only. P3-G1 remains `NO-GO / CLOSED`.\n\n## Provenance\n\nGenerated from clean Ada-RCA commit `{}` using only committed P3 predictions, MI membership, and frozen feature artifacts; bootstrap uses 10,000 fault-stratified paired case resamples with seed 20260826.\n".format(subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip())
    (PROJECT_ROOT / args.doc).write_text(document, encoding="utf-8")
    print(json.dumps({"bootstrap": bootstrap, "transitions": summaries}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
