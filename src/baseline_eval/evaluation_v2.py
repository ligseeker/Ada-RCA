"""Unified, post-global-lock RCAEval baseline evaluation for V2."""

from __future__ import annotations

from collections import defaultdict
import argparse
import json
import math
from pathlib import Path
import random
from typing import Any, Mapping, Sequence

from src.baseline_eval.confirmatory import (
    DATASET_ORDER,
    RCAEVAL_COMMIT,
    atomic_write_json,
    expected_case_ids,
    git,
    read_json,
    read_jsonl,
    require_clean_git,
    sha256_file,
    utc_now,
)
from src.baseline_eval import EXPECTED_CASES_PER_DATASET
from src.baseline_eval.rescue_v2 import (
    PROJECT_ROOT,
    V2_COMBINED_EVALUATION_ROOT_RELATIVE,
    V2_COMBINED_GLOBAL_LOCK_RELATIVE,
    V2_COMBINED_GLOBAL_LOCK_SCHEMA,
    V2_COMBINED_METHODS,
    V2_COMBINED_PROTOCOL_DIGEST,
    V2_EVALUATION_ROOT_RELATIVE,
    V2_GLOBAL_LOCK_RELATIVE,
    V2_METHODS,
    V2_PROTOCOL_DIGEST,
    V2EvaluationBlocked,
    V2_GLOBAL_LOCK_SCHEMA,
    V2_METHOD_ZERO_STATUS,
    V2_STATUS_VALUES,
    v2_record_relative,
    verify_v2_combined_global_prediction_lock,
    verify_v2_combined_protocol,
    verify_v2_global_prediction_lock,
    verify_v2_protocol,
    v2_source_manifest_digest,
)


OVERALL_RELATIVE = V2_EVALUATION_ROOT_RELATIVE / "overall_v2.json"
FAULT_RELATIVE = V2_EVALUATION_ROOT_RELATIVE / "fault_level_v2.json"
ROBUSTNESS_RELATIVE = V2_EVALUATION_ROOT_RELATIVE / "robustness_v2.json"
COMPARABILITY_RELATIVE = V2_EVALUATION_ROOT_RELATIVE / "comparability_v2.json"
BOOTSTRAP_RELATIVE = V2_EVALUATION_ROOT_RELATIVE / "paired_bootstrap_v2.json"
COMBINED_OVERALL_RELATIVE = V2_COMBINED_EVALUATION_ROOT_RELATIVE / "overall_v2.json"
COMBINED_FAULT_RELATIVE = V2_COMBINED_EVALUATION_ROOT_RELATIVE / "fault_level_v2.json"
COMBINED_ROBUSTNESS_RELATIVE = V2_COMBINED_EVALUATION_ROOT_RELATIVE / "robustness_v2.json"
COMBINED_COMPARABILITY_RELATIVE = V2_COMBINED_EVALUATION_ROOT_RELATIVE / "comparability_v2.json"
COMBINED_BOOTSTRAP_RELATIVE = V2_COMBINED_EVALUATION_ROOT_RELATIVE / "paired_bootstrap_v2.json"
REPORT_RELATIVE = Path("docs/baseline_eval/RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md")

FROZEN_ADA_METRICS = {
    "re2ob": {
        "AC@1": 0.8777777778,
        "AC@3": 0.9888888889,
        "AC@5": 0.9888888889,
        "Avg@5": 0.9622222222,
        "MRR": 0.9314814815,
    },
    "re2tt": {
        "AC@1": 0.7111111111,
        "AC@3": 0.8666666667,
        "AC@5": 0.9333333333,
        "Avg@5": 0.8511111111,
        "MRR": 0.8034718882,
    },
}
FROZEN_ADA_METRIC_SHA256 = {
    "re2ob": "080a4035753de2d9c8eeb15e9f4d18d43be34116ee9a3b7e0954ed797f5a43d1",
    "re2tt": "7dfcafc271420df860877e11c87778fba32a75793a3006a5ab48d3fad4f5ef5c",
}
FROZEN_ADA_PROVENANCE_SHA256 = {
    "re2ob": "34c0628c090b8fedaa6da3d6544d591cf541f3904bbed809ed06c21922ef3232",
    "re2tt": "24c25d1cb6fe1a3f76b878ba6a396cfa310072a4e52ec1b669447afc5dbaaa3b",
}
FAULTS = ("cpu", "mem", "disk", "socket", "delay", "loss")
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260827


def _evaluation_root(root: Path) -> Path:
    return root / V2_EVALUATION_ROOT_RELATIVE


def require_v2_metric_unlock(root: Path) -> dict[str, Any]:
    """Require a committed, integrity-valid global lock before reading labels."""

    require_clean_git(root)
    verify_v2_protocol(root)
    lock = verify_v2_global_prediction_lock(root, require_committed=True)
    if lock.get("schema_version") != V2_GLOBAL_LOCK_SCHEMA:
        raise V2EvaluationBlocked("V2 global lock schema is not metric-unlockable")
    if any((root / relative).exists() for relative in (
        OVERALL_RELATIVE,
        FAULT_RELATIVE,
        ROBUSTNESS_RELATIVE,
        COMPARABILITY_RELATIVE,
        BOOTSTRAP_RELATIVE,
    )):
        raise V2EvaluationBlocked("V2 evaluation output already exists and is immutable")
    return lock


def require_v2_combined_metric_unlock(root: Path) -> dict[str, Any]:
    """Require the committed six-method lock before joining labels."""

    require_clean_git(root)
    verify_v2_combined_protocol(root)
    lock = verify_v2_combined_global_prediction_lock(root, require_committed=True)
    if lock.get("schema_version") != V2_COMBINED_GLOBAL_LOCK_SCHEMA:
        raise V2EvaluationBlocked("combined V2 global lock is not metric-unlockable")
    if any(
        (root / relative).exists()
        for relative in (
            COMBINED_OVERALL_RELATIVE,
            COMBINED_FAULT_RELATIVE,
            COMBINED_ROBUSTNESS_RELATIVE,
            COMBINED_COMPARABILITY_RELATIVE,
            COMBINED_BOOTSTRAP_RELATIVE,
        )
    ):
        raise V2EvaluationBlocked("combined V2 evaluation output already exists and is immutable")
    return lock


def require_v2_evaluation_outputs(root: Path) -> dict[str, Any]:
    """Require the same committed lock while reading immutable post-lock files."""

    require_clean_git(root)
    verify_v2_protocol(root)
    lock = verify_v2_global_prediction_lock(root, require_committed=True)
    missing = [
        relative.as_posix()
        for relative in (OVERALL_RELATIVE, FAULT_RELATIVE, ROBUSTNESS_RELATIVE, COMPARABILITY_RELATIVE, BOOTSTRAP_RELATIVE)
        if not (root / relative).is_file()
    ]
    if missing:
        raise V2EvaluationBlocked("V2 evaluation outputs are incomplete: " + ", ".join(missing))
    return lock


def require_v2_combined_evaluation_outputs(root: Path) -> dict[str, Any]:
    """Require the same committed six-method lock for report projections."""

    require_clean_git(root)
    verify_v2_combined_protocol(root)
    lock = verify_v2_combined_global_prediction_lock(root, require_committed=True)
    missing = [
        relative.as_posix()
        for relative in (
            COMBINED_OVERALL_RELATIVE,
            COMBINED_FAULT_RELATIVE,
            COMBINED_ROBUSTNESS_RELATIVE,
            COMBINED_COMPARABILITY_RELATIVE,
            COMBINED_BOOTSTRAP_RELATIVE,
        )
        if not (root / relative).is_file()
    ]
    if missing:
        raise V2EvaluationBlocked(
            "combined V2 evaluation outputs are incomplete: " + ", ".join(missing)
        )
    return lock


def _frozen_ada_case_rows(root: Path, dataset: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metrics_path = root / "artifacts" / "final_method" / dataset / "metrics.json"
    provenance_path = root / "artifacts" / "final_method" / dataset / "provenance.json"
    if sha256_file(metrics_path) != FROZEN_ADA_METRIC_SHA256[dataset]:
        raise V2EvaluationBlocked(f"frozen Ada-RCA metrics bytes changed for {dataset}")
    if sha256_file(provenance_path) != FROZEN_ADA_PROVENANCE_SHA256[dataset]:
        raise V2EvaluationBlocked(f"frozen Ada-RCA provenance bytes changed for {dataset}")
    payload = read_json(metrics_path)
    rows = payload.get("case_metrics")
    if not isinstance(rows, list) or len(rows) != 90:
        raise V2EvaluationBlocked(f"frozen Ada-RCA case metrics do not contain 90 cases for {dataset}")
    if {row.get("case_id") for row in rows} != set(expected_case_ids(root, dataset)):
        raise V2EvaluationBlocked(f"frozen Ada-RCA case identity differs for {dataset}")
    observed = {
        metric: sum(float(row[metric]) for row in rows) / 90
        for metric in ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")
    }
    for metric, expected in FROZEN_ADA_METRICS[dataset].items():
        if not math.isclose(observed[metric], expected, rel_tol=0.0, abs_tol=5e-10):
            raise V2EvaluationBlocked(f"frozen Ada-RCA metric identity assertion failed for {dataset} {metric}")
    return [
        {
            "case_id": row["case_id"],
            "fault_type": row["fault_type"].lower(),
            "AC@1": float(row["AC@1"]),
            "AC@3": float(row["AC@3"]),
            "AC@5": float(row["AC@5"]),
            "Avg@5": float(row["Avg@5"]),
        }
        for row in rows
    ], {**FROZEN_ADA_METRICS[dataset], "source": str(metrics_path)}


def _labels_after_unlock(root: Path, dataset: str) -> dict[str, dict[str, str]]:
    rows = read_jsonl(root / "artifacts" / "source" / dataset / "labels.jsonl")
    mapping = {
        row["case_id"]: {
            "root_service": row["root_service"],
            "fault_type": row["fault_type"].lower(),
        }
        for row in rows
    }
    if set(mapping) != set(expected_case_ids(root, dataset)):
        raise V2EvaluationBlocked(f"label identity differs from the 90-case universe for {dataset}")
    return mapping


def _status_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter = {status: 0 for status in V2_STATUS_VALUES}
    for row in rows:
        status = row.get("terminal_status")
        if status not in counter:
            raise V2EvaluationBlocked(f"unknown V2 terminal status: {status}")
        counter[status] += 1
    return counter


def _case_utility(status: str, ranking: Sequence[str], target: str) -> tuple[int, ...]:
    if status == V2_METHOD_ZERO_STATUS:
        return (0, 0, 0, 0, 0)
    if status != "SUCCESS":
        raise V2EvaluationBlocked(f"{status} cannot enter formal V2 performance")
    return tuple(int(target in ranking[:k]) for k in range(1, 6))


def _aggregate_hits(hits: Sequence[Sequence[int]]) -> dict[str, float | str]:
    if len(hits) != EXPECTED_CASES_PER_DATASET:
        raise V2EvaluationBlocked("V2 metric denominator is not exactly 90")
    values = {
        f"AC@{k}": sum(row[k - 1] for row in hits) / EXPECTED_CASES_PER_DATASET
        for k in range(1, 6)
    }
    values["Avg@5"] = sum(float(values[f"AC@{k}"]) for k in range(1, 6)) / 5
    values["MRR"] = "NOT-IDENTIFIABLE"
    values["MRR_legality"] = "NOT-IDENTIFIABLE"
    return values


def _baseline_case_rows(
    root: Path,
    method: str,
    attempt_id: str,
    dataset: str,
    labels: Mapping[str, Mapping[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    for case_id in expected_case_ids(root, dataset):
        row = read_json(root / v2_record_relative(method, attempt_id, dataset, case_id))
        status = row["terminal_status"]
        hits = _case_utility(status, row.get("adapted_ranking", []), labels[case_id]["root_service"])
        rows.append({
            "case_id": case_id,
            "fault_type": labels[case_id]["fault_type"],
            "terminal_status": status,
            "hits": list(hits),
            **{f"AC@{k}": hits[k - 1] for k in range(1, 6)},
            "Avg@5": sum(hits) / 5,
        })
    statuses = _status_counts(rows)
    return rows, {
        **_aggregate_hits([row["hits"] for row in rows]),
        "cases": len(rows),
        "status_counts": statuses,
        "success_cases": statuses["SUCCESS"],
        "robustness_zero_method_failures": statuses["METHOD_FAILURE"],
    }


def _fault_rows(
    method: str,
    dataset: str,
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for fault in FAULTS:
        selected = [row for row in case_rows if row["fault_type"] == fault]
        if not selected:
            output.append({
                "method": method,
                "dataset": dataset,
                "fault": fault.upper(),
                "cases": 0,
                "AC@1": "N/A",
                "AC@3": "N/A",
                "AC@5": "N/A",
                "Avg@5": "N/A",
            })
            continue
        values = {
            f"AC@{k}": sum(float(row[f"AC@{k}"]) for row in selected) / len(selected)
            for k in (1, 3, 5)
        }
        values["Avg@5"] = sum(float(row["Avg@5"]) for row in selected) / len(selected)
        output.append({
            "method": method,
            "dataset": dataset,
            "fault": fault.upper(),
            "cases": len(selected),
            **values,
        })
    return output


def _comparability_rows(methods: Sequence[str] = (*V2_METHODS, "Ada-RCA")) -> list[dict[str, Any]]:
    specs = {
        "CIRCA": ("metric", "case-wise unsupervised", "indicator", "partial service projection", "NO", "NOT-IDENTIFIABLE"),
        "MicroCause": ("metric", "case-wise unsupervised", "indicator", "partial service projection", "NO", "NOT-IDENTIFIABLE"),
        "MicroRank": ("raw trace", "case-wise unsupervised", "operation", "partial service projection", "NO", "NOT-IDENTIFIABLE"),
        "TraceRCA": ("raw trace", "case-wise unsupervised", "operation", "partial service projection", "NO", "NOT-IDENTIFIABLE"),
        "mmBARO": ("multi-source", "case-wise unsupervised", "indicator", "partial service projection", "NO", "NOT-IDENTIFIABLE"),
        "CausalRCA": ("metric", "case-wise unsupervised", "indicator", "partial service projection", "NO", "NOT-IDENTIFIABLE"),
        "Ada-RCA": ("Metrics + Logs + Traces", "root-supervised cross-case training", "native service ranking", "native service ranking", "YES", "FROZEN/NATIVE"),
    }
    return [
        {
            "method": method,
            "input": values[0],
            "supervision": values[1],
            "native_granularity": values[2],
            "service_projection": values[3],
            "complete_service_ranking": values[4],
            "MRR_legality": values[5],
        }
        for method in methods
        for values in (specs[method],)
    ]


def _bootstrap_delta(
    ada_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    ada_by_case = {row["case_id"]: row for row in ada_rows}
    base_by_case = {row["case_id"]: row for row in baseline_rows}
    strata: dict[str, list[float]] = defaultdict(list)
    for case_id, base in base_by_case.items():
        if case_id not in ada_by_case:
            raise V2EvaluationBlocked("bootstrap case identity mismatch")
        strata[base["fault_type"]].append(
            float(ada_by_case[case_id][metric]) - float(base[metric])
        )
    if not strata:
        raise V2EvaluationBlocked("bootstrap has no fault strata")
    point = sum(sum(values) for values in strata.values()) / sum(len(values) for values in strata.values())
    rng = random.Random(seed)
    sampled_means: list[float] = []
    for _ in range(resamples):
        sampled = [rng.choice(values) for values in strata.values() for _ in values]
        sampled_means.append(sum(sampled) / len(sampled))
    sampled_means.sort()
    lower = sampled_means[int(0.025 * (resamples - 1))]
    upper = sampled_means[int(0.975 * (resamples - 1))]
    return {
        "estimand": f"Ada-RCA minus {metric} baseline",
        "metric": metric,
        "fault_stratified": True,
        "cases": sum(len(values) for values in strata.values()),
        "fault_case_counts": {fault: len(values) for fault, values in sorted(strata.items())},
        "point_estimate": point,
        "ci_95_percent": [lower, upper],
        "resamples": resamples,
        "seed": seed,
    }


def _evaluate_locked_scope(
    root: Path,
    *,
    lock: Mapping[str, Any],
    methods: Sequence[str],
    output_relatives: Mapping[str, Path],
    global_lock_relative: Path,
    protocol_digest: str,
    evaluation_scope: str,
) -> dict[str, Path]:
    """Evaluate one already-unlocked method scope without changing its lock."""

    labels = {dataset: _labels_after_unlock(root, dataset) for dataset in DATASET_ORDER}
    ada_case_rows: dict[str, list[dict[str, Any]]] = {}
    ada_metrics: dict[str, dict[str, Any]] = {}
    baseline_case_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    baseline_metrics: dict[tuple[str, str], dict[str, Any]] = {}
    robustness_rows: list[dict[str, Any]] = []
    fault_rows: list[dict[str, Any]] = []
    overall_values: dict[tuple[str, str], dict[str, Any]] = {}
    for dataset in DATASET_ORDER:
        ada_case_rows[dataset], ada_metrics[dataset] = _frozen_ada_case_rows(root, dataset)
        for row in ada_case_rows[dataset]:
            # This is an identity check only.  It runs after the global-lock
            # gate and prevents frozen Ada evidence from being paired with a
            # different post-lock fault taxonomy.
            if row["fault_type"] != labels[dataset][row["case_id"]]["fault_type"]:
                raise V2EvaluationBlocked(
                    f"frozen Ada-RCA fault identity differs from labels for {dataset} "
                    f"{row['case_id']}"
                )
        # Frozen Ada case metrics already contain the exact AC@k values; do not
        # infer ranks or retrain.  The aggregate was identity-asserted above.
        ada_metrics[dataset]["cases"] = 90
        ada_metrics[dataset]["status_counts"] = {status: (90 if status == "SUCCESS" else 0) for status in V2_STATUS_VALUES}
        overall_values[("Ada-RCA", dataset)] = ada_metrics[dataset]
        fault_rows.extend(_fault_rows("Ada-RCA", dataset, ada_case_rows[dataset]))
        for method in methods:
            attempt_id = lock["attempt_ids"][method]
            rows, metrics = _baseline_case_rows(root, method, attempt_id, dataset, labels[dataset])
            baseline_case_rows[(method, dataset)] = rows
            baseline_metrics[(method, dataset)] = metrics
            overall_values[(method, dataset)] = metrics
            fault_rows.extend(_fault_rows(method, dataset, rows))
            counts = metrics["status_counts"]
            robustness_rows.append({
                "method": method,
                "dataset": dataset,
                "cases": 90,
                "SUCCESS": counts["SUCCESS"],
                "METHOD_FAILURE": counts["METHOD_FAILURE"],
                "DATA_FAILURE": counts["DATA_FAILURE"],
                "ADAPTER_FAILURE": counts["ADAPTER_FAILURE"],
                "ENVIRONMENT_FAILURE": counts["ENVIRONMENT_FAILURE"],
                "INPUT_INTEGRITY_FAILURE": counts["INPUT_INTEGRITY_FAILURE"],
                "PROCESS_CRASH/OOM": counts["PROCESS_CRASH/OOM"],
                "TIMEOUT": counts["TIMEOUT"],
            })
    table_a_rows = []
    for method in (*methods, "Ada-RCA"):
        row = {"Method": method}
        for dataset, display in (("re2ob", "OB"), ("re2tt", "TT")):
            metrics = overall_values[(method, dataset)]
            for metric in ("AC@1", "AC@3", "AC@5", "Avg@5"):
                row[f"{display} {metric}"] = metrics[metric]
        table_a_rows.append(row)
    table_a = {
        "columns": ["Method", "OB AC@1", "OB AC@3", "OB AC@5", "OB Avg@5", "TT AC@1", "TT AC@3", "TT AC@5", "TT Avg@5"],
        "rows": table_a_rows,
        "pooling": "FORBIDDEN; RE2-OB and RE2-TT remain separate",
    }
    table_c = {
        "columns": ["Method", "Dataset", "Cases", "SUCCESS", "METHOD_FAILURE", "DATA_FAILURE", "ADAPTER_FAILURE", "ENVIRONMENT_FAILURE", "INPUT_INTEGRITY_FAILURE", "PROCESS_CRASH/OOM", "TIMEOUT"],
        "rows": robustness_rows,
        "process_crash_policy": "execution invalid/incomplete; never silently converted to METHOD_FAILURE",
    }
    table_d = {
        "columns": ["Method", "Input", "Supervision", "Native granularity", "Service projection", "Complete service ranking", "MRR legality"],
        "rows": _comparability_rows((*methods, "Ada-RCA")),
    }
    provenance = {
        "global_prediction_lock": {
            "path": global_lock_relative.as_posix(),
            "sha256": sha256_file(root / global_lock_relative),
            "commit": git(root, "log", "-1", "--format=%H", "--", global_lock_relative.as_posix()).stdout.strip(),
        },
        "protocol_digest": protocol_digest,
        "method_order": list(methods),
        "evaluation_scope": evaluation_scope,
        "input_manifest_digest": v2_source_manifest_digest(root),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "ada_rca_reference": FROZEN_ADA_METRICS,
    }
    overall_payload = {
        "schema_version": "rca_baseline_rescue_overall_evaluation_v2",
        "evaluated_at": utc_now(),
        "provenance": provenance,
        "table_a": table_a,
        "method_dataset_metrics": {
            f"{method}__{dataset}": metrics
            for (method, dataset), metrics in overall_values.items()
        },
        "baseline_mrr": "NOT-IDENTIFIABLE",
        "labels_joined_after_global_lock": True,
        "method_scope": list(methods),
    }
    fault_payload = {
        "schema_version": "rca_baseline_rescue_fault_level_evaluation_v2",
        "provenance": provenance,
        "faults": list(FAULTS),
        "rows": fault_rows,
        "absent_fault_policy": "N/A",
    }
    robustness_payload = {
        "schema_version": "rca_baseline_rescue_robustness_evaluation_v2",
        "provenance": provenance,
        "table_c": table_c,
    }
    comparability_payload = {
        "schema_version": "rca_baseline_rescue_comparability_v2",
        "provenance": provenance,
        "table_d": table_d,
    }
    bootstrap_rows = []
    for dataset in DATASET_ORDER:
        for method in methods:
            baseline = baseline_case_rows[(method, dataset)]
            bootstrap_rows.append({
                "method": method,
                "dataset": dataset,
                "primary_delta_avg5": _bootstrap_delta(ada_case_rows[dataset], baseline, metric="Avg@5"),
                "secondary_delta_ac1": _bootstrap_delta(ada_case_rows[dataset], baseline, metric="AC@1"),
            })
    bootstrap_payload = {
        "schema_version": "rca_baseline_rescue_paired_fault_stratified_bootstrap_v2",
        "provenance": provenance,
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "rows": bootstrap_rows,
    }
    outputs = {
        key: root / output_relatives[key]
        for key in ("overall", "fault_level", "robustness", "comparability", "paired_bootstrap")
    }
    for key, payload in (
        ("overall", overall_payload),
        ("fault_level", fault_payload),
        ("robustness", robustness_payload),
        ("comparability", comparability_payload),
        ("paired_bootstrap", bootstrap_payload),
    ):
        atomic_write_json(outputs[key], payload)
    return outputs


def evaluate_v2(root: Path) -> dict[str, Path]:
    """Evaluate the original frozen five-method V2 scope."""

    lock = require_v2_metric_unlock(root)
    return _evaluate_locked_scope(
        root,
        lock=lock,
        methods=V2_METHODS,
        output_relatives={
            "overall": OVERALL_RELATIVE,
            "fault_level": FAULT_RELATIVE,
            "robustness": ROBUSTNESS_RELATIVE,
            "comparability": COMPARABILITY_RELATIVE,
            "paired_bootstrap": BOOTSTRAP_RELATIVE,
        },
        global_lock_relative=V2_GLOBAL_LOCK_RELATIVE,
        protocol_digest=V2_PROTOCOL_DIGEST,
        evaluation_scope="V2_FIVE_BASELINES",
    )


def evaluate_v2_causalrca(root: Path) -> dict[str, Path]:
    """Evaluate all six baselines after the additive combined V2 lock."""

    lock = require_v2_combined_metric_unlock(root)
    return _evaluate_locked_scope(
        root,
        lock=lock,
        methods=V2_COMBINED_METHODS,
        output_relatives={
            "overall": COMBINED_OVERALL_RELATIVE,
            "fault_level": COMBINED_FAULT_RELATIVE,
            "robustness": COMBINED_ROBUSTNESS_RELATIVE,
            "comparability": COMBINED_COMPARABILITY_RELATIVE,
            "paired_bootstrap": COMBINED_BOOTSTRAP_RELATIVE,
        },
        global_lock_relative=V2_COMBINED_GLOBAL_LOCK_RELATIVE,
        protocol_digest=V2_COMBINED_PROTOCOL_DIGEST,
        evaluation_scope="V2_SIX_BASELINES_WITH_CAUSALRCA_CPU_EXTENSION",
    )


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.10f}"
    return str(value)


def _markdown_table(columns: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    def value_for(row: Mapping[str, Any], column: str) -> Any:
        if column in row:
            return row[column]
        normalized = column.lower().replace(" ", "_")
        if normalized in row:
            return row[normalized]
        for key, value in row.items():
            if str(key).lower().replace(" ", "_") == normalized:
                return value
        return "N/A"

    lines.extend(
        "| " + " | ".join(_fmt(value_for(row, column)) for column in columns) + " |"
        for row in rows
    )
    return "\n".join(lines)


def _render_report(
    root: Path,
    *,
    output_relatives: Mapping[str, Path],
    require_outputs: Any,
    title: str,
    methods: Sequence[str],
) -> Path:
    require_outputs(root)
    overall = read_json(root / output_relatives["overall"])
    fault = read_json(root / output_relatives["fault_level"])
    robustness = read_json(root / output_relatives["robustness"])
    comparability = read_json(root / output_relatives["comparability"])
    bootstrap = read_json(root / output_relatives["paired_bootstrap"])
    table_c_rows = [
        {
            **row,
            "dataset": {"re2ob": "RE2-OB", "re2tt": "RE2-TT"}.get(
                row.get("dataset"), row.get("dataset")
            ),
        }
        for row in robustness["table_c"]["rows"]
    ]
    report = f"""# {title}

Performance-blind rescue execution was frozen before this post-lock report.
Ada-RCA values are read from identity-asserted frozen evidence; no retraining is
performed. The baseline scope is `{', '.join(methods)}`. RE2-OB and RE2-TT are
reported separately and are never pooled.

## Table A — Overall RCA Performance

{_markdown_table(overall['table_a']['columns'], overall['table_a']['rows'])}

## Table B — Fault-Level Performance

{_markdown_table(('Method', 'Dataset', 'Fault', 'Cases', 'AC@1', 'AC@3', 'AC@5', 'Avg@5'), fault['rows'])}

## Table C — Execution Robustness

All six baselines are shown for both datasets with the frozen 90-case
denominator. `METHOD_FAILURE` is retained as a legal zero-utility outcome;
all blocking-status columns are zero, so every bound method lock is
`INTEGRITY_VALID`.

{_markdown_table(robustness['table_c']['columns'], table_c_rows)}

## Table D — Protocol / Output Comparability

The CausalRCA row is included through the authorized CPU case-level extension;
its native indicator output is evaluated through the same partial service
projection rule, so complete service ranking and MRR are not claimed.

{_markdown_table(comparability['table_d']['columns'], comparability['table_d']['rows'])}

## Paired fault-stratified bootstrap

- Resamples: `{bootstrap['resamples']}`
- Seed: `{bootstrap['seed']}`
- Primary: Ada-RCA minus baseline `Avg@5`
- Secondary: Ada-RCA minus baseline `AC@1`

The baseline MRR field is `NOT-IDENTIFIABLE` because RCAEval native outputs
are partial service projections and no candidate completion is legal.
"""
    path = root / REPORT_RELATIVE
    path.write_text(report, encoding="utf-8")
    return path


def render_report_v2(root: Path) -> Path:
    return _render_report(
        root,
        output_relatives={
            "overall": OVERALL_RELATIVE,
            "fault_level": FAULT_RELATIVE,
            "robustness": ROBUSTNESS_RELATIVE,
            "comparability": COMPARABILITY_RELATIVE,
            "paired_bootstrap": BOOTSTRAP_RELATIVE,
        },
        require_outputs=require_v2_evaluation_outputs,
        title="Ada-RCA — RCAEval Five-Baseline Rescue & Unified Evaluation V2",
        methods=V2_METHODS,
    )


def render_report_v2_causalrca(root: Path) -> Path:
    return _render_report(
        root,
        output_relatives={
            "overall": COMBINED_OVERALL_RELATIVE,
            "fault_level": COMBINED_FAULT_RELATIVE,
            "robustness": COMBINED_ROBUSTNESS_RELATIVE,
            "comparability": COMBINED_COMPARABILITY_RELATIVE,
            "paired_bootstrap": COMBINED_BOOTSTRAP_RELATIVE,
        },
        require_outputs=require_v2_combined_evaluation_outputs,
        title="Ada-RCA — RCAEval Six-Baseline Rescue & Unified Evaluation V2",
        methods=V2_COMBINED_METHODS,
    )


def command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("evaluate-v2")
    sub.add_parser("evaluate-v2-causalrca")
    sub.add_parser("render-report-v2")
    sub.add_parser("render-report-v2-causalrca")
    sub.add_parser("fault-level-v2")
    sub.add_parser("fault-level-v2-causalrca")
    sub.add_parser("robustness-v2")
    sub.add_parser("robustness-v2-causalrca")
    sub.add_parser("comparability-v2")
    sub.add_parser("comparability-v2-causalrca")
    sub.add_parser("paired-bootstrap-v2")
    sub.add_parser("paired-bootstrap-v2-causalrca")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = command_parser().parse_args(argv)
    root = PROJECT_ROOT
    if args.command == "evaluate-v2":
        for path in evaluate_v2(root).values():
            print(path)
    elif args.command == "evaluate-v2-causalrca":
        for path in evaluate_v2_causalrca(root).values():
            print(path)
    elif args.command == "render-report-v2":
        print(render_report_v2(root))
    elif args.command == "render-report-v2-causalrca":
        print(render_report_v2_causalrca(root))
    else:
        base_output_map = {
            "fault-level-v2": FAULT_RELATIVE,
            "robustness-v2": ROBUSTNESS_RELATIVE,
            "comparability-v2": COMPARABILITY_RELATIVE,
            "paired-bootstrap-v2": BOOTSTRAP_RELATIVE,
        }
        combined_output_map = {
            "fault-level-v2-causalrca": COMBINED_FAULT_RELATIVE,
            "robustness-v2-causalrca": COMBINED_ROBUSTNESS_RELATIVE,
            "comparability-v2-causalrca": COMBINED_COMPARABILITY_RELATIVE,
            "paired-bootstrap-v2-causalrca": COMBINED_BOOTSTRAP_RELATIVE,
        }
        # These commands are intentionally read-only projections of the one
        # atomic evaluate stage; they never bypass the metric-unlock gate.
        if args.command in base_output_map:
            require_v2_evaluation_outputs(root)
            path = root / base_output_map[args.command]
        elif args.command in combined_output_map:
            require_v2_combined_evaluation_outputs(root)
            path = root / combined_output_map[args.command]
        else:
            raise AssertionError(f"unhandled evaluation command: {args.command}")
        if not path.is_file():
            raise V2EvaluationBlocked("run the corresponding evaluate command first after the global lock commit")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
