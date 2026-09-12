#!/usr/bin/env python3
"""Create paired statistics and case-level diagnostics for Z2-XGB closure."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.closure_diagnostics import (
    paired_metric_statistics,
    summarize_rank_transitions,
)
from src.rca.supervised_baselines.common import sha256_file


DATASETS = ("re2ob", "re2tt")
METRICS = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")
PAIRED_METRICS = ("Avg@5", "AC@1", "MRR")
Z1_CL_COMMIT = "d36ad67"
Z1_CL_ROOT = "artifacts/p4_g0/predictions/a0"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def git_json(commit: str, path: str):
    raw = subprocess.check_output(
        ("git", "show", "{}:{}".format(commit, path)), cwd=str(PROJECT_ROOT)
    )
    return json.loads(raw)


def verify_checksums(directory: Path) -> None:
    checksums = read_json(directory / "checksums.json")
    for relative, expected in checksums.items():
        actual = sha256_file(directory / relative)
        if actual != expected:
            raise ValueError("checksum mismatch: {}".format(directory / relative))


def _case_metric_map(metrics):
    rows = {str(row["case_id"]): dict(row) for row in metrics["case_metrics"]}
    if len(rows) != len(metrics["case_metrics"]):
        raise ValueError("duplicate case metric IDs")
    return rows


def load_aggregate_records(artifact_root: Path, method: str, dataset: str):
    directory = artifact_root / method / dataset / "aggregate"
    verify_checksums(directory)
    metrics = read_json(directory / "metrics.json")
    metric_rows = _case_metric_map(metrics)
    rows = read_jsonl(directory / "predictions.jsonl")
    by_case = {}
    for row in rows:
        by_case.setdefault(str(row["case_id"]), []).append(row)
    if set(by_case) != set(metric_rows) or len(by_case) != 90:
        raise ValueError("aggregate case universe mismatch for {}/{}".format(method, dataset))
    result = {}
    for case_id in sorted(by_case):
        case_rows = sorted(by_case[case_id], key=lambda row: int(row["rank"]))
        root_ranks = {int(row["root_rank"]) for row in case_rows}
        faults = {str(row["fault_type"]) for row in case_rows}
        roots = {str(row["root_service"]) for row in case_rows}
        folds = {int(row["fold"]) for row in case_rows}
        if len(root_ranks) != 1 or len(faults) != 1 or len(roots) != 1 or len(folds) != 1:
            raise ValueError("inconsistent aggregate metadata for {}".format(case_id))
        row = metric_rows[case_id]
        if str(row["fault_type"]) != next(iter(faults)) or int(row["fold"]) != next(iter(folds)):
            raise ValueError("aggregate metrics metadata mismatch for {}".format(case_id))
        result[case_id] = {
            **row,
            "root_rank": next(iter(root_ranks)),
            "root_service": next(iter(roots)),
        }
    return result, metrics["overall_cases"]


def load_final_records(dataset: str):
    directory = PROJECT_ROOT / "artifacts" / "final_method" / dataset
    verify_checksums(directory)
    metrics = read_json(directory / "metrics.json")
    metric_rows = _case_metric_map(metrics)
    predictions = read_jsonl(directory / "predictions.jsonl")
    result = {}
    for prediction in predictions:
        case_id = str(prediction["case_id"])
        if case_id in result or case_id not in metric_rows:
            raise ValueError("invalid Ada-RCA case coverage for {}".format(case_id))
        ranking = tuple(str(value) for value in prediction["ranking"])
        root = str(prediction["root_service"])
        if len(ranking) != len(set(ranking)) or root not in ranking:
            raise ValueError("Ada-RCA ranking is incomplete for {}".format(case_id))
        row = metric_rows[case_id]
        result[case_id] = {
            **row,
            "root_rank": ranking.index(root) + 1,
            "root_service": root,
        }
    if len(result) != 90:
        raise ValueError("Ada-RCA prediction case count is not 90")
    return result, metrics["overall_cases"]


def load_historical_z1_cl(dataset: str):
    metrics_path = "{}/{}/metrics.json".format(Z1_CL_ROOT, dataset)
    metrics = git_json(Z1_CL_COMMIT, metrics_path)
    return metrics["overall_cases"], {
        "commit": Z1_CL_COMMIT,
        "path": metrics_path,
        "config": git_json(Z1_CL_COMMIT, "{}/{}/config.json".format(Z1_CL_ROOT, dataset)),
        "manifest": git_json(Z1_CL_COMMIT, "{}/{}/manifest.json".format(Z1_CL_ROOT, dataset)),
        "checksums": git_json(Z1_CL_COMMIT, "{}/{}/checksums.json".format(Z1_CL_ROOT, dataset)),
    }


def git_identity():
    return {
        "commit": subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=str(PROJECT_ROOT), text=True
        ).strip(),
        "branch": subprocess.check_output(
            ("git", "branch", "--show-current"), cwd=str(PROJECT_ROOT), text=True
        ).strip(),
    }


def main() -> None:
    output_root = PROJECT_ROOT / "artifacts" / "z2_xgb_closure" / "diagnostics"
    if output_root.exists():
        raise FileExistsError("diagnostic output already exists: {}".format(output_root))

    records = {dataset: {} for dataset in DATASETS}
    overall = {dataset: {} for dataset in DATASETS}
    z1_cl = {}
    z1_cl_provenance = {}
    for dataset in DATASETS:
        records[dataset]["z2_xgb"], overall[dataset]["z2_xgb"] = load_aggregate_records(
            PROJECT_ROOT / "artifacts" / "z2_xgb_closure", "z2_xgb", dataset
        )
        records[dataset]["z1_xgb"], overall[dataset]["z1_xgb"] = load_aggregate_records(
            PROJECT_ROOT / "artifacts" / "supervised_baselines", "xgb_ranker", dataset
        )
        records[dataset]["tcn"], overall[dataset]["tcn"] = load_aggregate_records(
            PROJECT_ROOT / "artifacts" / "supervised_baselines", "tcn", dataset
        )
        records[dataset]["ada"], overall[dataset]["ada"] = load_final_records(dataset)
        overall[dataset]["z1_cl"], z1_cl_provenance[dataset] = load_historical_z1_cl(dataset)
        z1_cl[dataset] = overall[dataset]["z1_cl"]

    matrix = {}
    attribution = {}
    for dataset in DATASETS:
        matrix[dataset] = {
            method: {metric: float(overall[dataset][method][metric]) for metric in METRICS}
            for method in ("z1_cl", "ada", "z1_xgb", "z2_xgb")
        }
        attribution[dataset] = {}
        for metric in METRICS:
            linear = matrix[dataset]["ada"][metric] - matrix[dataset]["z1_cl"][metric]
            xgb = matrix[dataset]["z2_xgb"][metric] - matrix[dataset]["z1_xgb"][metric]
            attribution[dataset][metric] = {
                "delta_morph_linear": linear,
                "delta_morph_xgb": xgb,
                "interaction_delta": xgb - linear,
            }

    pair_definitions = (
        ("z2_xgb_minus_z1_xgb", "z2_xgb", "z1_xgb"),
        ("z2_xgb_minus_ada", "z2_xgb", "ada"),
        ("z1_xgb_minus_ada", "z1_xgb", "ada"),
        ("tcn_minus_ada", "tcn", "ada"),
    )
    paired = {dataset: {} for dataset in DATASETS}
    for dataset in DATASETS:
        for name, left, right in pair_definitions:
            paired[dataset][name] = paired_metric_statistics(
                records[dataset][left],
                records[dataset][right],
                left,
                right,
                metrics=PAIRED_METRICS,
                resamples=10000,
                seed=20260826,
            )

    comparison_definitions = (
        ("z1_xgb_vs_ada", "z1_xgb", "ada"),
        ("z2_xgb_vs_z1_xgb", "z2_xgb", "z1_xgb"),
        ("z2_xgb_vs_ada", "z2_xgb", "ada"),
        ("tcn_vs_ada", "tcn", "ada"),
    )
    transitions = {dataset: {} for dataset in DATASETS}
    transition_rows = []
    for dataset in DATASETS:
        for name, new, old in comparison_definitions:
            summary = summarize_rank_transitions(records[dataset][new], records[dataset][old])
            transitions[dataset][name] = {
                key: value for key, value in summary.items() if key != "case_rows"
            }
            for row in summary["case_rows"]:
                transition_rows.append({
                    "dataset": dataset,
                    "comparison": name,
                    "new_method": new,
                    "old_method": old,
                    **row,
                })

    provenance = {
        "protocol": "docs/z2_xgb_closure/Z2_XGB_CLOSURE_PROTOCOL_V1.md",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": git_identity(),
        "z1_cl": z1_cl_provenance,
        "input_artifacts": {
            "z2_xgb": "artifacts/z2_xgb_closure/z2_xgb/{dataset}/aggregate",
            "z1_xgb": "artifacts/supervised_baselines/xgb_ranker/{dataset}/aggregate",
            "tcn": "artifacts/supervised_baselines/tcn/{dataset}/aggregate",
            "ada": "artifacts/final_method/{dataset}",
        },
    }
    summary = {
        "schema_version": "z2_xgb_scientific_closure_diagnostics_v1",
        "datasets": list(DATASETS),
        "metrics": list(METRICS),
        "paired_metrics": list(PAIRED_METRICS),
        "bootstrap": {"resamples": 10000, "seed": 20260826, "stratification": "fault_type"},
        "matrix": matrix,
        "attribution": attribution,
        "paired_statistics": paired,
        "rank_transition_summaries": transitions,
        "provenance": provenance,
    }
    output_root.mkdir(parents=True)
    (output_root / "closure_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_root / "paired_statistics.json").write_text(
        json.dumps(paired, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_root / "rank_transitions.json").write_text(
        json.dumps(transitions, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_root / "attribution.json").write_text(
        json.dumps({"matrix": matrix, "attribution": attribution}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "rank_transition_cases.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in transition_rows),
        encoding="utf-8",
    )
    checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_root.iterdir())
        if path.is_file()
    }
    (output_root / "checksums.json").write_text(
        json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "PASS",
        "output": str(output_root),
        "datasets": list(DATASETS),
        "comparisons": [name for name, _, _ in comparison_definitions],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
