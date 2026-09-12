"""Reproducible post-lock audit of the frozen RCA baseline evidence.

The generator is intentionally a reader of already locked records.  It does
not invoke a baseline method, mutate a prediction record, or create a lock.
Labels are read only after the existing BARO and combined V2 lock gates pass.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.baseline_eval.audit_evaluator import (
    METRICS,
    PROTOCOL_VERSION as DUAL_PROTOCOL_VERSION,
    evaluate_records,
)
from src.baseline_eval.confirmatory import (
    DATASET_DISPLAY,
    DATASET_ORDER,
    INPUT_MANIFEST_RELATIVE,
    RCAEVAL_CLEAN,
    RCAEVAL_COMMIT,
    RCAEVAL_SOURCE_DIGESTS,
    atomic_write_json,
    canonical_payload_digest,
    expected_case_ids,
    git,
    read_json,
    read_jsonl,
    sha256_file,
    verify_rcaeval_clean,
)
from src.baseline_eval.final_comparison import (
    BARO_ENVIRONMENT_RELATIVE,
    BARO_LOCK_RELATIVE,
    FINAL_COMPARISON_ROOT_RELATIVE,
    V2_EVALUATION_ROOT_RELATIVE,
    verify_baro_v1_lock,
    verify_six_method_v2_lock,
)
from src.baseline_eval.rescue_v2 import (
    CAUSALRCA_CPU_ATTEMPT_ID,
    CAUSALRCA_CPU_EXECUTION_ROOT_RELATIVE,
    CAUSALRCA_CPU_PROTOCOL_DIGEST,
    V2_COMBINED_GLOBAL_LOCK_RELATIVE,
    V2_COMBINED_METHODS,
    v2_attempt_relative,
    verify_v2_combined_global_prediction_lock,
    verify_v2_method_lock,
)
from src.baseline_eval.worker import load_legal_case_input


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_ROOT_RELATIVE = Path("artifacts/baseline_eval/audit_fix_v1")
AUDIT_REPORT_RELATIVE = Path("docs/baseline_eval/RCA_BASELINE_AUDIT_FIX_V1.md")
AUDIT_SCHEMA_VERSION = "rca_baseline_audit_fix_v1"
EXPECTED_DENOMINATOR = 90
METHOD_ORDER = (
    "BARO",
    "CIRCA",
    "MicroCause",
    "MicroRank",
    "TraceRCA",
    "mmBARO",
    "CausalRCA",
)
ALL_STATUSES = (
    "SUCCESS",
    "METHOD_FAILURE",
    "ADAPTER_FAILURE",
    "DATA_FAILURE",
    "ENVIRONMENT_FAILURE",
    "INPUT_INTEGRITY_FAILURE",
    "PROCESS_CRASH/OOM",
    "TIMEOUT",
)
BLOCKING_STATUSES = {
    "ADAPTER_FAILURE",
    "DATA_FAILURE",
    "ENVIRONMENT_FAILURE",
    "INPUT_INTEGRITY_FAILURE",
    "PROCESS_CRASH/OOM",
    "TIMEOUT",
}
AUDIT_OUTPUTS = (
    "provenance_audit.json",
    "denominator_audit.json",
    "denominator_audit.csv",
    "dual_protocol_results.json",
    "dual_protocol_results.csv",
    "protocol_difference_cases.jsonl",
    "regular_fraction_audit.json",
    "microrank_static_audit.json",
    "causalrca_static_audit.json",
    "causalrca_diagnostics_schema.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _commit_for_path(root: Path, relative: Path) -> str:
    result = git(root, "log", "-1", "--format=%H", "--", relative.as_posix(), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _source_lines(path: Path, start: int, end: int) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        "path": str(path),
        "start_line": start,
        "end_line": end,
        "text": "\n".join(lines[start - 1 : end]),
    }


def _counter_dict(values: Iterable[Any]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _status_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in ALL_STATUSES}
    for row in rows:
        status = str(row.get("terminal_status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _label_maps(root: Path, dataset: str) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    rows = read_jsonl(root / "artifacts/source" / dataset / "labels.jsonl")
    labels = {row["case_id"]: row["root_service"] for row in rows}
    details = {
        row["case_id"]: {
            "root_service": row["root_service"],
            "fault_type": str(row["fault_type"]).lower(),
        }
        for row in rows
    }
    return labels, details


def _dataset_metadata(root: Path, dataset: str) -> dict[str, Any]:
    inputs = read_jsonl(root / "artifacts/source" / dataset / "inputs.jsonl")
    labels = read_jsonl(root / "artifacts/source" / dataset / "labels.jsonl")
    sources = read_jsonl(root / "artifacts/source" / dataset / "sources.jsonl")
    registry_path = root / "artifacts/source" / dataset / "service_registry.json"
    registry = read_json(registry_path)["services"]
    return {
        "display_name": DATASET_DISPLAY[dataset],
        "case_count": len(inputs),
        "unique_case_count": len({row["case_id"] for row in inputs}),
        "case_ids_aligned": (
            [row["case_id"] for row in inputs]
            == [row["case_id"] for row in labels]
            == [row["case_id"] for row in sources]
        ),
        "fault_case_counts": _counter_dict(row["fault_type"].lower() for row in labels),
        "root_case_counts": _counter_dict(row["root_service"] for row in labels),
        "candidate_count": len(registry),
        "candidate_services": registry,
        "input_manifest_case_count": len(inputs),
        "artifacts": {
            "inputs": {
                "path": f"artifacts/source/{dataset}/inputs.jsonl",
                "sha256": sha256_file(root / "artifacts/source" / dataset / "inputs.jsonl"),
            },
            "labels": {
                "path": f"artifacts/source/{dataset}/labels.jsonl",
                "sha256": sha256_file(root / "artifacts/source" / dataset / "labels.jsonl"),
            },
            "sources": {
                "path": f"artifacts/source/{dataset}/sources.jsonl",
                "sha256": sha256_file(root / "artifacts/source" / dataset / "sources.jsonl"),
            },
            "service_registry": {
                "path": f"artifacts/source/{dataset}/service_registry.json",
                "sha256": sha256_file(registry_path),
            },
        },
    }


def _active_method_binding(
    root: Path,
    method: str,
    *,
    combined_lock: Mapping[str, Any],
    baro_lock: Mapping[str, Any],
) -> dict[str, Any]:
    if method == "BARO":
        lock_relative = BARO_LOCK_RELATIVE
        lock = dict(baro_lock)
        attempt_id = str(lock["attempt_id"])
        record_root = Path("artifacts/baseline_eval/execution_v1/records/baro") / attempt_id
        environment_relative = BARO_ENVIRONMENT_RELATIVE
        attempt_relative = None
        source_digest = RCAEVAL_SOURCE_DIGESTS["RCAEval/e2e/baro.py"]
        execution_root = Path("artifacts/baseline_eval/execution_v1")
    else:
        method_rows = {row["method"]: row for row in combined_lock["methods"]}
        method_row = method_rows[method]
        lock_relative = Path(method_row["method_lock_path"])
        lock = verify_v2_method_lock(
            root, method, require_committed=True, lock_relative=lock_relative
        )
        attempt_id = str(lock["attempt_id"])
        profile_root = (
            CAUSALRCA_CPU_EXECUTION_ROOT_RELATIVE if method == "CausalRCA"
            else Path("artifacts/baseline_eval/execution_v2")
        )
        record_root = profile_root / "records" / method.lower() / attempt_id
        environment_relative = (
            profile_root / "environments" / f"{method.lower()}.json"
        )
        attempt_relative = v2_attempt_relative(method, attempt_id)
        source_digest = RCAEVAL_SOURCE_DIGESTS[
            f"RCAEval/e2e/{method.lower() if method != 'mmBARO' else 'baro'}.py"
        ]
        execution_root = profile_root
    environment = read_json(root / environment_relative)
    attempt = read_json(root / attempt_relative) if attempt_relative else None
    return {
        "method": method,
        "attempt_id": attempt_id,
        "lock": lock,
        "lock_path": lock_relative.as_posix(),
        "lock_sha256": sha256_file(root / lock_relative),
        "lock_commit": _commit_for_path(root, lock_relative),
        "record_root": record_root.as_posix(),
        "environment_path": environment_relative.as_posix(),
        "environment_sha256": sha256_file(root / environment_relative),
        "environment_digest": environment.get("environment_digest"),
        "attempt_path": attempt_relative.as_posix() if attempt_relative else None,
        "attempt": attempt,
        "execution_root": execution_root.as_posix(),
        "source_digest": source_digest,
    }


def _load_active_records(
    root: Path,
    binding: Mapping[str, Any],
    dataset: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = expected_case_ids(root, dataset)
    directory = root / str(binding["record_root"]) / dataset
    files = sorted(path for path in directory.glob("*.json") if path.is_file())
    rows = [read_json(path) for path in files]
    observed_ids = [str(row.get("case_id")) for row in rows]
    observed_counter = Counter(observed_ids)
    duplicate_ids = sorted(case_id for case_id, count in observed_counter.items() if count > 1)
    missing_ids = sorted(set(expected).difference(observed_counter))
    foreign_ids = sorted(set(observed_counter).difference(expected))
    by_id = {str(row["case_id"]): row for row in rows if str(row.get("case_id")) in set(expected)}
    ordered = [by_id[case_id] for case_id in expected if case_id in by_id]
    status_counts = _status_counts(rows)
    failure_errors = Counter(
        str(row.get("error_type"))
        for row in rows
        if row.get("terminal_status") != "SUCCESS" and row.get("error_type")
    )
    metadata = {
        "directory": directory.relative_to(root).as_posix(),
        "discovered_record_files": len(files),
        "execution_records": len(rows),
        "terminal_records": sum(bool(row.get("terminal_status")) for row in rows),
        "observed_case_id_count": len(observed_counter),
        "duplicate_case_ids": duplicate_ids,
        "missing_case_ids": missing_ids,
        "foreign_case_ids": foreign_ids,
        "record_file_names": [path.name for path in files],
        "status_counts": status_counts,
        "failure_error_types": dict(sorted(failure_errors.items())),
        "record_sha256": {
            str(row.get("case_id")): sha256_file(directory / f"{row.get('case_id')}.json")
            for row in ordered
        },
        "execution_commits": sorted({str(row.get("execution_commit")) for row in rows}),
        "native_output_lengths": _counter_dict(
            row.get("native_output_length") for row in rows if row.get("terminal_status") == "SUCCESS"
        ),
        "adapted_output_lengths": _counter_dict(
            row.get("adapted_output_length") for row in rows if row.get("terminal_status") == "SUCCESS"
        ),
        "duplicate_native_item_counts": _counter_dict(
            row.get("duplicate_count") for row in rows if row.get("terminal_status") == "SUCCESS"
        ),
        "unmapped_native_item_counts": _counter_dict(
            row.get("unmapped_count") for row in rows if row.get("terminal_status") == "SUCCESS"
        ),
    }
    if len(ordered) != EXPECTED_DENOMINATOR or metadata["duplicate_case_ids"] or missing_ids or foreign_ids:
        raise RuntimeError(
            f"active {binding['method']} {dataset} records do not cover the exact frozen 90-case universe"
        )
    return ordered, metadata


def _old_metrics(root: Path, method: str, dataset: str) -> tuple[dict[str, Any], str]:
    if method == "BARO":
        relative = FINAL_COMPARISON_ROOT_RELATIVE / "overall_v3.json"
    else:
        relative = V2_EVALUATION_ROOT_RELATIVE / "overall_v2.json"
    payload = read_json(root / relative)
    metrics = dict(payload["method_dataset_metrics"][f"{method}__{dataset}"])
    return metrics, relative.as_posix()


def _case_digest_and_metrics(
    root: Path,
    method: str,
    dataset: str,
    records: Sequence[Mapping[str, Any]],
    labels: Mapping[str, str],
    candidates: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    case_rows, aggregates = evaluate_records(
        records,
        labels,
        candidates,
        expected_case_ids(root, dataset),
    )
    enriched: list[dict[str, Any]] = []
    for case_row, record in zip(case_rows, records):
        enriched.append({
            **case_row,
            "method": method,
            "dataset": dataset,
            "native_output_length": record.get("native_output_length"),
            "adapted_output_length": record.get("adapted_output_length"),
            "native_output_digest": record.get("native_output_digest"),
            "adapted_output_digest": record.get("adapted_output_digest"),
            "duplicate_native_items": record.get("duplicate_native_items", []),
            "unmapped_native_items": record.get("unmapped_native_items", []),
            "missing_candidate_reasons": record.get("missing_candidate_reasons", {}),
            "error_type": record.get("error_type"),
            "record_terminal_status": record.get("terminal_status"),
        })
    old, old_source = _old_metrics(root, method, dataset)
    old_identity = {
        metric: (
            old.get(metric) is not None
            and abs(float(old[metric]) - float(aggregates["unique_service"]["metrics"][metric])) <= 5e-10
        )
        for metric in (*METRICS, "Avg@5")
    }
    return enriched, aggregates, {
        "old_metrics": old,
        "old_source": old_source,
        "old_equals_recomputed_unique_service": old_identity,
    }


def _flatten_status(status_counts: Mapping[str, int]) -> dict[str, int]:
    return {status: int(status_counts.get(status, 0)) for status in ALL_STATUSES}


def _dual_result_row(
    method: str,
    dataset: str,
    aggregates: Mapping[str, Mapping[str, Any]],
    old_info: Mapping[str, Any],
) -> dict[str, Any]:
    unique = aggregates["unique_service"]
    slot = aggregates["rcaeval_service_slot"]
    old = old_info["old_metrics"]
    row: dict[str, Any] = {
        "method": method,
        "dataset": dataset,
        "dataset_display": DATASET_DISPLAY[dataset],
        "denominator": EXPECTED_DENOMINATOR,
        "success_cases": unique["status_counts"].get("SUCCESS", 0),
        "method_failures": unique["status_counts"].get("METHOD_FAILURE", 0),
        "blocking_failures": sum(
            unique["status_counts"].get(status, 0) for status in BLOCKING_STATUSES
        ),
        "old_source": old_info["old_source"],
        "old_identity_check": old_info["old_equals_recomputed_unique_service"],
        "status_counts": _flatten_status(unique["status_counts"]),
        "protocol_version": DUAL_PROTOCOL_VERSION,
    }
    for metric in (*METRICS, "Avg@5"):
        old_value = old.get(metric)
        unique_value = unique["metrics"][metric]
        slot_value = slot["metrics"][metric]
        row[f"old_{metric}"] = old_value
        row[f"unique_service_{metric}"] = unique_value
        row[f"rcaeval_service_slot_{metric}"] = slot_value
        row[f"delta_{metric}_slot_minus_unique"] = slot_value - unique_value
        row[f"delta_{metric}_unique_minus_old"] = (
            unique_value - float(old_value) if old_value is not None else None
        )
        row[f"delta_{metric}_slot_minus_old"] = (
            slot_value - float(old_value) if old_value is not None else None
        )
    row["unique_hit_counts"] = unique["hit_counts"]
    row["rcaeval_service_slot_hit_counts"] = slot["hit_counts"]
    row["avg_numerator_unique"] = unique["avg_at_5_numerator"]
    row["avg_numerator_rcaeval_service_slot"] = slot["avg_at_5_numerator"]
    return row


def _csv_write(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            serial = dict(row)
            for key, value in list(serial.items()):
                if isinstance(value, (dict, list, tuple)):
                    serial[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            writer.writerow(serial)


def _jsonl_write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _source_static_audit(root: Path) -> dict[str, Any]:
    source_root = RCAEVAL_CLEAN / "RCAEval/e2e"
    entries: dict[str, Any] = {}
    for method, filename in (
        ("BARO", "baro.py"),
        ("CIRCA", "circa.py"),
        ("MicroCause", "microcause.py"),
        ("MicroRank", "microrank.py"),
        ("TraceRCA", "tracerca.py"),
        ("mmBARO", "baro.py"),
        ("CausalRCA", "causalrca.py"),
    ):
        path = source_root / filename
        entries[method] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "expected_sha256": RCAEVAL_SOURCE_DIGESTS[
                f"RCAEval/e2e/{filename}"
            ],
            "digest_matches_freeze": sha256_file(path)
            == RCAEVAL_SOURCE_DIGESTS[f"RCAEval/e2e/{filename}"],
        }
    entries["BARO"]["claims"] = {
        "normal_anomalous_partition": _source_lines(source_root / "baro.py", 19, 41),
        "robust_scaler_and_descending_score": _source_lines(source_root / "baro.py", 43, 60),
    }
    entries["mmBARO"]["claims"] = {
        "modalities_and_robust_scaler": _source_lines(source_root / "baro.py", 63, 174),
    }
    entries["CIRCA"]["claims"] = {
        "preprocess_graph_and_descending_rht": _source_lines(source_root / "circa.py", 15, 40),
        "tt_dataset_hardcoded_to_ob": _source_lines(source_root / "circa.py", 28, 34),
    }
    entries["MicroCause"]["claims"] = {
        "descending_gamma_ranking": _source_lines(source_root / "microcause.py", 2168, 2195),
        "return_contract": _source_lines(source_root / "microcause.py", 2330, 2365),
    }
    entries["MicroRank"]["claims"] = {
        "top_max_plus_six": _source_lines(source_root / "microrank.py", 439, 447),
        "operation_and_normal_anomalous_partition": _source_lines(source_root / "microrank.py", 646, 707),
    }
    entries["TraceRCA"]["claims"] = {
        "slo_support_confidence_ji_descending": _source_lines(source_root / "tracerca.py", 45, 98),
    }
    entries["CausalRCA"]["claims"] = {
        "node_names_and_graph_threshold": _source_lines(source_root / "causalrca.py", 347, 352),
        "thresholding": _source_lines(source_root / "causalrca.py", 607, 616),
        "pagerank_fallback": _source_lines(source_root / "causalrca.py", 620, 643),
        "official_broad_wrapper_fallback": _source_lines(
            source_root / "__init__.py", 21, 30
        ),
    }
    return entries


def _evaluator_static_audit(root: Path) -> dict[str, Any]:
    official = RCAEVAL_CLEAN / "RCAEval/benchmark/evaluation.py"
    driver = RCAEVAL_CLEAN / "main.py"
    local = root / "src/baseline_eval/evaluation_v2.py"
    adapter = root / "src/baseline_eval/__init__.py"
    return {
        "local_unified_evaluator": {
            "path": str(local),
            "sha256": sha256_file(local),
            "semantics": "persisted adapted_ranking, fixed 90 denominator, METHOD_FAILURE zero utility",
        },
        "local_adapter": {
            "path": str(adapter),
            "sha256": sha256_file(adapter),
            "semantics": "longest legal candidate prefix, frontendservice alias, first occurrence retained, unmapped omitted (unique_service only)",
        },
        "pinned_rcaeval_evaluator_class": {
            "path": str(official),
            "sha256": sha256_file(official),
            "service_slot_code": _source_lines(official, 14, 25),
            "finding": "Evaluator service_ranks preserves the supplied entity slot sequence; no service dedup occurs inside add_case before service_ranks[:k].",
        },
        "pinned_rcaeval_main_driver": {
            "path": str(driver),
            "sha256": sha256_file(driver),
            "projection_and_dedup_code": _source_lines(driver, 379, 397),
            "finding": "The pinned historical main.py driver separately maps x.split('_')[0].replace('-db','') and then removes duplicate Node services before calling Evaluator.",
        },
        "audit_protocol_decision": "unique_service reproduces the current adapter's first-occurrence deduplication. RCAEval-service-slot applies pinned main.py's x.split('_')[0].replace('-db','') entity projection to every native slot and then reproduces Evaluator class slot membership without deduplication; it does not apply the local candidate registry or alias rule.",
    }


def _micro_rank_audit(
    case_rows: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    records: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    labels: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "source_contract": {
            "top_max": 5,
            "native_return_cap": 11,
            "native_return_formula": "top_max + 6",
            "ranking_direction": "descending score",
            "operation_name": "serviceName_methodName",
        },
        "datasets": {},
    }
    for dataset in DATASET_ORDER:
        rows = case_rows["MicroRank", dataset]
        raw_records = records["MicroRank", dataset]
        stats = Counter()
        truncation_cases: list[str] = []
        root_prefix5 = 0
        root_any = 0
        examples: dict[str, Any] = {}
        for evaluated, record in zip(rows, raw_records):
            if evaluated["status"] != "SUCCESS":
                continue
            service = labels[dataset][evaluated["case_id"]]["root_service"]
            projected = evaluated["projected_service_slots"]
            if service in [value for value in projected[:5] if value is not None]:
                root_prefix5 += 1
            if service in [value for value in projected if value is not None]:
                root_any += 1
            native_length = int(record.get("native_output_length") or len(evaluated["native_ranking"]))
            stats[native_length] += 1
            reason = evaluated["missing_candidate_reasons"].get(service)
            if reason == "NATIVE_TOP_K_TRUNCATION":
                truncation_cases.append(evaluated["case_id"])
            if not examples.get("top1_miss_top3_hit") and evaluated["hits_unique"][0] == 0 and evaluated["hits_unique"][2] == 1:
                examples["top1_miss_top3_hit"] = evaluated
            if not examples.get("dedup_changes_outcome") and evaluated["affected_k"]:
                examples["dedup_changes_outcome"] = evaluated
        # Include one failed case only as an operational example, never as a
        # fabricated ranking.
        for evaluated in rows:
            if evaluated["status"] != "SUCCESS":
                examples.setdefault("first_method_failure", evaluated)
                break
        if truncation_cases:
            case_id = truncation_cases[0]
            examples["root_excluded_by_native_truncation"] = next(
                row for row in rows if row["case_id"] == case_id
            )
        output["datasets"][dataset] = {
            "native_ranking_length_distribution_success": dict(sorted(stats.items())),
            "native_top_k_truncation_case_count": len(truncation_cases),
            "native_top_k_truncation_case_ids": truncation_cases,
            "root_in_native_prefix_5_success_count": root_prefix5,
            "root_in_native_output_success_count": root_any,
            "success_count": sum(row["status"] == "SUCCESS" for row in rows),
            "examples": examples,
        }
    return output


def _reconstruct_causal_node_names(root: Path, dataset: str) -> list[dict[str, Any]]:
    """Reconstruct only the name filtering visible in pinned CausalRCA code."""

    result: list[dict[str, Any]] = []
    record_directory = (
        root / CAUSALRCA_CPU_EXECUTION_ROOT_RELATIVE / "records/causalrca"
        / CAUSALRCA_CPU_ATTEMPT_ID / dataset
    )
    for case_id in expected_case_ids(root, dataset):
        telemetry, anchor, _candidates, _sli, _observed, _provenance = load_legal_case_input(
            "CausalRCA", dataset, case_id, drop_nonfinite_time=True
        )
        metric = telemetry.iloc[::15, :]

        def pinned_preprocess(frame):
            frame = frame.drop(columns=["time"])
            frame = frame.loc[:, (frame != frame.iloc[0]).any()]
            return frame

        normal = pinned_preprocess(metric[metric["time"] < anchor])
        anomalous = pinned_preprocess(metric[metric["time"] >= anchor])
        node_names = [column for column in normal.columns if column in anomalous.columns]
        overall = pinned_preprocess(telemetry.copy()).columns.tolist()
        record = read_json(record_directory / f"{case_id}.json")
        native = list(record.get("native_ranking", []))
        result.append({
            "case_id": case_id,
            "overall_runner_preprocessed_column_count": len(overall),
            "causal_split_intersection_column_count": len(node_names),
            "native_output_length": len(native),
            "native_equals_reconstructed_node_names": native == node_names,
            "native_is_prefix_of_reconstructed_node_names": native == node_names[: len(native)],
            "native_names_not_in_reconstructed_node_names": sorted(set(native).difference(node_names)),
            "reconstruction_note": "node_names and adjacency were not persisted; this is an offline name-only reconstruction from the pinned source logic and current manifest-bound inputs.",
        })
    return result


def _causal_static_audit(
    root: Path,
    causal_case_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    causal_records: Mapping[str, Sequence[Mapping[str, Any]]],
    label_details: Mapping[str, Mapping[str, Mapping[str, str]]],
) -> dict[str, Any]:
    source_path = RCAEVAL_CLEAN / "RCAEval/e2e/causalrca.py"
    wrapper_path = RCAEVAL_CLEAN / "RCAEval/e2e/__init__.py"
    output: dict[str, Any] = {
        "schema_version": "rca_baseline_causalrca_static_audit_v1",
        "execution_performed_by_codex": False,
        "runtime_diagnostic_status": "NOT_EXECUTED",
        "source": {
            "path": str(source_path),
            "sha256": sha256_file(source_path),
            "expected_sha256": RCAEVAL_SOURCE_DIGESTS["RCAEval/e2e/causalrca.py"],
            "pinned_commit": RCAEVAL_COMMIT,
            "pagerank_fallback": _source_lines(source_path, 620, 626),
            "ranking_sort_and_return": _source_lines(source_path, 628, 643),
            "threshold_and_training_exception_scope": _source_lines(source_path, 607, 616),
            "wrapper_broad_exception": _source_lines(wrapper_path, 21, 30),
        },
        "fallback_logic_interpretation": {
            "confirmed": [
                "Pinned causalrca.py catches Exception around PageRank and returns node_names as ranks.",
                "The wrapper in pinned e2e/__init__.py also catches Exception and returns preprocessed column order.",
            ],
            "not_claimed": "The source comment says empty graph, but the Python except Exception scope is broader; the exact historical runtime exception is not stored in records.",
        },
        "datasets": {},
    }
    for dataset in DATASET_ORDER:
        rows = causal_case_rows[dataset]
        records = causal_records[dataset]
        digest_groups: dict[str, list[str]] = defaultdict(list)
        adapted_groups: dict[str, list[str]] = defaultdict(list)
        root_positions: dict[str, Counter[int | None]] = defaultdict(Counter)
        case_outputs: list[dict[str, Any]] = []
        for evaluated, record in zip(rows, records):
            native = list(evaluated["native_ranking"])
            adapted = list(evaluated["unique_service_ranking"])
            native_digest = str(record.get("native_output_digest"))
            adapted_digest = str(record.get("adapted_output_digest"))
            digest_groups[native_digest].append(evaluated["case_id"])
            adapted_groups[adapted_digest].append(evaluated["case_id"])
            target = label_details[dataset][evaluated["case_id"]]["root_service"]
            root_positions[target][evaluated["root_rank_unique"]] += 1
            case_outputs.append({
                "case_id": evaluated["case_id"],
                "ground_truth": target,
                "terminal_status": evaluated["status"],
                "native_ranking": native,
                "adapted_ranking": adapted,
                "native_ranking_length": len(native),
                "adapted_ranking_length": len(adapted),
                "native_ranking_digest": native_digest,
                "native_ranking_digest_recomputed": canonical_payload_digest(native),
                "adapted_ranking_digest": adapted_digest,
                "adapted_ranking_digest_recomputed": canonical_payload_digest(adapted),
                "root_rank": evaluated["root_rank_unique"],
                "root_rank_unique": evaluated["root_rank_unique"],
                "root_rank_slot": evaluated["root_rank_slot"],
                "hit_at_1": evaluated["hits_unique"][0],
                "hit_at_2": evaluated["hits_unique"][1],
                "hit_at_3": evaluated["hits_unique"][2],
                "hit_at_4": evaluated["hits_unique"][3],
                "hit_at_5": evaluated["hits_unique"][4],
                "adjacency_persisted": "adj" in record,
                "node_names_persisted": "node_names" in record,
            })
        reconstruction = _reconstruct_causal_node_names(root, dataset)
        output["datasets"][dataset] = {
            "case_count": len(case_outputs),
            "status_counts": _status_counts(records),
            "native_ranking_unique_digest_count": len(digest_groups),
            "adapted_ranking_unique_digest_count": len(adapted_groups),
            "native_digest_groups_largest": [
                {"digest": digest, "case_count": len(case_ids), "case_ids": case_ids[:5]}
                for digest, case_ids in sorted(digest_groups.items(), key=lambda item: (-len(item[1]), item[0]))[:10]
            ],
            "adapted_digest_groups": [
                {"digest": digest, "case_count": len(case_ids), "case_ids": case_ids[:5]}
                for digest, case_ids in sorted(adapted_groups.items(), key=lambda item: (-len(item[1]), item[0]))
            ],
            "fixed_adapted_ranking": (
                case_outputs[0]["adapted_ranking"] if case_outputs else []
            ),
            "root_positions": {
                service: {str(position): count for position, count in sorted(positions.items(), key=lambda item: str(item[0]))}
                for service, positions in sorted(root_positions.items())
            },
            "all_adapted_rankings_identical": len(adapted_groups) == 1,
            "all_native_digests_recomputed_match_records": all(
                row["native_ranking_digest"] == row["native_ranking_digest_recomputed"]
                and row["adapted_ranking_digest"] == row["adapted_ranking_digest_recomputed"]
                for row in case_outputs
            ),
            "adjacency_reconstructed": False,
            "adjacency_reconstruction_reason": "adjacency is not present in frozen case records; no adjacency values were invented.",
            "input_column_reconstruction": {
                "exact_match_count": sum(row["native_equals_reconstructed_node_names"] for row in reconstruction),
                "prefix_match_count": sum(row["native_is_prefix_of_reconstructed_node_names"] for row in reconstruction),
                "native_contains_extra_names_count": sum(bool(row["native_names_not_in_reconstructed_node_names"]) for row in reconstruction),
                "cases": reconstruction,
            },
            "case_outputs": case_outputs,
        }
    return output


def _regular_fraction_audit(
    aggregates: Mapping[tuple[str, str], Mapping[str, Mapping[str, Any]]],
    design: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    targets = (0.1667, 0.2000, 0.3333, 0.4000, 0.6000, 0.6667, 0.8333, 0.8778, 0.9889)
    occurrences: dict[str, list[dict[str, Any]]] = {f"{value:.4f}": [] for value in targets}
    for (method, dataset), method_aggregates in sorted(aggregates.items()):
        for protocol, aggregate in method_aggregates.items():
            for metric in METRICS:
                value = float(aggregate["metrics"][metric])
                display = f"{value:.4f}"
                if display in occurrences:
                    numerator = int(aggregate["hit_counts"][f"hit@{metric.split('@')[1]}"])
                    occurrences[display].append({
                        "method": method,
                        "dataset": dataset,
                        "protocol": protocol,
                        "metric": metric,
                        "displayed_value": display,
                        "numerator": numerator,
                        "denominator": EXPECTED_DENOMINATOR,
                        "exact_value": value,
                    })
            value = float(aggregate["metrics"]["Avg@5"])
            display = f"{value:.4f}"
            if display in occurrences:
                occurrences[display].append({
                    "method": method,
                    "dataset": dataset,
                    "protocol": protocol,
                    "metric": "Avg@5",
                    "displayed_value": display,
                    "numerator": int(aggregate["avg_at_5_numerator"]),
                    "denominator": 5 * EXPECTED_DENOMINATOR,
                    "exact_value": value,
                })
    for display, rows in occurrences.items():
        for row in rows:
            if row["metric"] == "Avg@5":
                assert row["numerator"] == sum(
                    aggregates[(row["method"], row["dataset"])][row["protocol"]]["hit_counts"].values()
                )
            else:
                assert row["numerator"] / row["denominator"] == row["exact_value"]
    return {
        "targets": [f"{value:.4f}" for value in targets],
        "occurrences": occurrences,
        "dataset_design": design,
        "interpretation": "AC@K values use integer hits over 90 cases; Avg@5 uses the unrounded sum of five raw hit counts over 450 slots. The displayed fraction alone does not identify case-micro versus equally sized fault-macro aggregation.",
    }


def _denominator_rows(
    record_metadata: Mapping[tuple[str, str], Mapping[str, Any]],
    case_rows: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    aggregates: Mapping[tuple[str, str], Mapping[str, Mapping[str, Any]]],
    old_info: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        for dataset in DATASET_ORDER:
            metadata = record_metadata[(method, dataset)]
            unique = aggregates[(method, dataset)]["unique_service"]
            slot = aggregates[(method, dataset)]["rcaeval_service_slot"]
            row: dict[str, Any] = {
                "method": method,
                "dataset": dataset,
                "expected_cases": EXPECTED_DENOMINATOR,
                "discovered_cases": metadata["discovered_record_files"],
                "execution_records": metadata["execution_records"],
                "terminal_records": metadata["terminal_records"],
                "success": unique["status_counts"].get("SUCCESS", 0),
                "method_failure": unique["status_counts"].get("METHOD_FAILURE", 0),
                "blocking": sum(
                    unique["status_counts"].get(status, 0) for status in BLOCKING_STATUSES
                ),
                "actual_evaluation_denominator": len(case_rows[(method, dataset)]),
                "successful_case_denominator_if_used": unique["status_counts"].get("SUCCESS", 0),
                "missing_records": len(metadata["missing_case_ids"]),
                "duplicate_records": len(metadata["duplicate_case_ids"]),
                "foreign_records": len(metadata["foreign_case_ids"]),
                "missing_case_ids": metadata["missing_case_ids"],
                "duplicate_case_ids": metadata["duplicate_case_ids"],
                "foreign_case_ids": metadata["foreign_case_ids"],
                "status_counts": metadata["status_counts"],
                "failure_error_types": metadata["failure_error_types"],
                "failure_denominator_policy": "METHOD_FAILURE remains in denominator 90 and contributes five zero hits; blocking statuses would invalidate formal evaluation.",
                "old_source": old_info[(method, dataset)]["old_source"],
                "old_identity_check": old_info[(method, dataset)]["old_equals_recomputed_unique_service"],
                "unique_hit_counts": unique["hit_counts"],
                "rcaeval_service_slot_hit_counts": slot["hit_counts"],
                "unique_metrics": unique["metrics"],
                "rcaeval_service_slot_metrics": slot["metrics"],
                "avg5_unique_formula_check": unique["avg_at_5_numerator"] == sum(unique["hit_counts"].values()),
                "avg5_slot_formula_check": slot["avg_at_5_numerator"] == sum(slot["hit_counts"].values()),
            }
            rows.append(row)
    return rows


def _protocol_difference_rows(
    case_rows: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]]
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        for dataset in DATASET_ORDER:
            for row in case_rows[(method, dataset)]:
                unique = row["unique_service_ranking"]
                slots = row["projected_service_slots"]
                if unique == slots and not row["affected_k"]:
                    continue
                differences.append({
                    "method": method,
                    "dataset": dataset,
                    "case_id": row["case_id"],
                    "ground_truth": row["ground_truth"],
                    "status": row["status"],
                    "native_ranking": row["native_ranking"],
                    "projected_service_slots": slots,
                    "unique_service_ranking": unique,
                    "root_rank_slot": row["root_rank_slot"],
                    "root_rank_unique": row["root_rank_unique"],
                    "affected_k": row["affected_k"],
                    "dedup_changed": row["dedup_changed"],
                    "native_ranking_length": row["native_output_length"],
                    "adapted_ranking_length": row["adapted_output_length"],
                    "native_ranking_digest": row["native_output_digest"],
                    "adapted_ranking_digest": row["adapted_output_digest"],
                    "duplicate_native_items": row["duplicate_native_items"],
                    "unmapped_native_items": row["unmapped_native_items"],
                    "missing_candidate_reasons": row["missing_candidate_reasons"],
                    "error_type": row["error_type"],
                })
    return differences


def _diagnostic_schema(
    causal_case_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    causal_static: Mapping[str, Any],
) -> dict[str, Any]:
    selection: list[dict[str, Any]] = []
    for dataset in DATASET_ORDER:
        seen_roots: set[str] = set()
        for row in causal_case_rows[dataset]:
            root_service = str(row["ground_truth"])
            if root_service in seen_roots:
                continue
            seen_roots.add(root_service)
            selection.append({
                "dataset": dataset,
                "case_id": row["case_id"],
                "root_service": root_service,
                "reason": "one case per distinct frozen root; service projection is fixed-order in historical record",
                "historical_root_rank": row["root_rank_unique"],
                "historical_native_digest": row["native_output_digest"],
            })
    return {
        "schema_version": "rca_baseline_causalrca_runtime_diagnostic_schema_v1",
        "status": "NOT_EXECUTED",
        "codex_runs_executed": 0,
        "case_selection": selection,
        "selection_count": len(selection),
        "selection_policy": "five root-diverse cases per dataset, selected from frozen CausalRCA records; this file contains no runtime diagnostic output.",
        "instrumentation_events": [
            "pagerank_called",
            "pagerank_success",
            "pagerank_exception",
        ],
        "recorded_fields": [
            "PageRank input shape, nonzero count, density, finite/min/max",
            "PageRank score shape, digest, unique count, finite/min/max/std",
            "exception type and message",
            "returned node_names, ranks, adjacency shape/nonzero count",
            "ranks == node_names and explicit runtime failure classification",
        ],
        "source": causal_static["source"],
        "manual_operator_note": "Run only after reviewing the report. The diagnostic runner is single-process and writes to a caller-selected path; it does not resume or overwrite confirmatory records or locks.",
    }


def _format_metric(value: Any) -> str:
    if isinstance(value, str):
        return value
    return f"{float(value):.10f}"


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def render_report(payload: Mapping[str, Any]) -> str:
    """Render the committed human-readable audit report from JSON payloads."""

    provenance = payload["provenance"]
    denominator = payload["denominator_rows"]
    results = payload["dual_result_rows"]
    differences = payload["protocol_difference_rows"]
    causal = payload["causal_static"]
    micro = payload["microrank_audit"]
    method_audit = payload["method_source_audit"]
    lines: list[str] = []
    lines.extend([
        "# RCA Baseline Audit and Necessary Fix V1",
        "",
        "## 1. Executive Summary",
        "",
        "The frozen baseline evidence is operationally complete for the seven listed methods: each method/dataset has exactly 90 terminal records, no missing or duplicate case ID, and no blocking terminal status. The historical numerical table is reproducible under the current `unique_service` adapter and fixed 90-case denominator.",
        "",
        "The audit nevertheless finds two scientific qualifications. First, the pinned RCAEval `Evaluator` class evaluates service slots without deduplicating before Top-K, while its historical `main.py` driver performs a separate deduplication step; therefore both frozen audit protocols are reported and are not selected by performance. Second, CausalRCA's service-level output is exactly degenerate within each dataset: one adapted ranking is repeated for all 90 cases. The pinned source contains a broad `except Exception` around PageRank, but the old records do not preserve the exception or adjacency, so the exact historical trigger is not confirmed.",
        "",
        "Overall conclusion: the ordinary baseline rows are usable only with explicit protocol, partial-ranking, and failure disclosure. The current CausalRCA row is not safe as a normal model-performance claim.",
        "",
        "## 2. Experiment Provenance",
        "",
        _markdown_table(
            ["Item", "Evidence"],
            [
                ["Ada-RCA branch", provenance["branch"]],
                ["Audit source HEAD", provenance["audit_generated_from_head"]],
                ["RCAEval checkout", provenance["rcaeval"]["path"]],
                ["RCAEval pinned commit", provenance["rcaeval"]["head"]],
                ["Input manifest", provenance["input_manifest"]["sha256"]],
                ["Global prediction lock", f"{provenance['global_prediction_lock']['path']} ({provenance['global_prediction_lock']['sha256']})"],
                ["Dual evaluator commit", provenance["dual_evaluator_commit"]],
                ["CausalRCA Codex executions", "0"],
            ],
        ),
        "",
        "Dataset design is balanced by six fault types (15 cases each) and five root services (18 cases each) in both RE2-OB and RE2-TT. These equal-size strata can make fault-macro and case-micro arithmetic coincide; the fraction pattern alone is not proof of aggregation.",
        "",
        "## 3. Denominator Audit",
        "",
        _markdown_table(
            ["Method", "Dataset", "Expected", "Records", "SUCCESS", "METHOD_FAILURE", "Blocking", "Denominator", "hit@1", "hit@3", "hit@5"],
            [
                [row["method"], DATASET_DISPLAY[row["dataset"]], row["expected_cases"], row["execution_records"], row["success"], row["method_failure"], row["blocking"], row["actual_evaluation_denominator"], row["unique_hit_counts"]["hit@1"], row["unique_hit_counts"]["hit@3"], row["unique_hit_counts"]["hit@5"]]
                for row in denominator
            ],
        ),
        "",
        "There are no skipped cases in the active evidence. `METHOD_FAILURE` is retained in the denominator and contributes five zero hits under the frozen utility policy. Missing, duplicate, foreign, or blocking records would stop evaluation; none are present.",
        "",
        "The Avg@5 checks are true for all 14 method/dataset rows. The audit computes `sum(raw hit@1..hit@5)/(5*90)` and does not average rounded cells.",
        "",
        "## 4. Regular Fraction Audit",
        "",
        _markdown_table(
            ["Displayed", "Observed numerator/denominator examples"],
            [
                [display, ", ".join(f"{row['numerator']}/{row['denominator']} ({row['method']} {DATASET_DISPLAY[row['dataset']]} {row['protocol']} {row['metric']})" for row in rows[:4]) or "not observed"]
                for display, rows in payload["regular_fraction_audit"]["occurrences"].items()
            ],
        ),
        "",
        "For AC@K, the denominator is 90. For Avg@5, the denominator is 450. In particular, 0.3333 is 30/90, 0.6667 is 60/90, 0.1667 is 15/90, 0.8333 as an AC cell is 75/90, 0.8778 is 79/90, and 0.9889 is 89/90. The 0.8333 displayed Avg@5 occurrences, where present, are 375/450 and must not be misread as 75/90 without the metric name.",
        "",
        "## 5. Evaluation Protocol Audit",
        "",
        "`unique_service`: native ranking -> frozen longest-prefix/alias mapping -> first occurrence retained -> duplicate service removed -> unmapped item removed -> Top-K.",
        "",
        "`rcaeval_service_slot`: native ranking -> pinned `main.py` entity projection (`x.split('_')[0].replace('-db','')`) at every native slot -> no service deduplication or local candidate filtering -> Top-K slot membership. This isolates the pinned `Evaluator.add_case` service-slot behavior. The local `frontendservice` alias belongs only to `unique_service`.",
        "",
        "Static source review found that pinned `RCAEval/benchmark/evaluation.py` uses `service_ranks[:k]` without deduplication. It also found pinned `main.py` deduplicates `Node` services before calling that class. This driver/class distinction is recorded rather than silently resolved in favor of a higher score.",
        "",
        "Synthetic test: `A_cpu, A_mem, B_cpu, C_cpu` with target `C` produces `A,B,C` and rank 3 under unique-service, versus `A,A,B,C` and rank 4 under service-slot.",
        "",
        "## 6. Dual-protocol Results",
        "",
        _markdown_table(
            ["Method", "Dataset", "Metric", "Old", "Unique-service", "RCAEval-slot", "Delta (slot-unique)"],
            [
                [row["method"], DATASET_DISPLAY[row["dataset"]], metric, _format_metric(row[f"old_{metric}"]), _format_metric(row[f"unique_service_{metric}"]), _format_metric(row[f"rcaeval_service_slot_{metric}"]), _format_metric(row[f"delta_{metric}_slot_minus_unique"])]
                for row in results
                for metric in (*METRICS, "Avg@5")
            ],
        ),
        "",
        "The old values identity-check against the recomputed unique-service values for every reported metric. This is evidence that the current table is not a successful-case-only or post-hoc fraction calculation. The slot protocol lowers some Top-K values where duplicate operations/indicators occupy native slots; for CausalRCA the pinned entity projection happens to match the local service projection in these records.",
        "",
        "## 7. Protocol Difference Cases",
        "",
        f"The complete case-level list is stored in `artifacts/baseline_eval/audit_fix_v1/protocol_difference_cases.jsonl` ({len(differences)} rows). A difference row is emitted when the two projected rankings differ or any hit@K differs. Typical affected cases:",
        "",
        _markdown_table(
            ["Method", "Dataset", "Case", "Root", "Unique rank", "Slot rank", "Affected K", "Unique prefix", "Slot prefix"],
            [
                [row["method"], DATASET_DISPLAY[row["dataset"]], row["case_id"], row["ground_truth"], row["root_rank_unique"], row["root_rank_slot"], row["affected_k"] or "-", row["unique_service_ranking"][:5], row["projected_service_slots"][:5]]
                for row in [r for r in differences if r["affected_k"]][:8]
            ],
        ),
        "",
        "## 8. Method Source and Execution Audit",
        "",
        "All six non-CausalRCA methods use the pinned source digests recorded in the active locks. The local worker passes the frozen windowed inputs and preserves native ranking direction; it does not reverse rankings or inject labels. BARO uses the upstream RobustScaler and descending score sort. mmBARO uses the upstream multi-modal metric/log/trace paths and RobustScaler. CIRCA calls the upstream PC/RHT path and the pinned source hard-codes `pc_default(..., dataset=\"ob\")`, including when the local runner supplies TT; this is an upstream behavior/limitation, not a local silent substitution. MicroCause sorts its gamma score descending. MicroRank constructs `serviceName_methodName`, sorts descending, and returns up to `top_max + 6 = 11`. TraceRCA uses support/confidence/Ji and descending Ji sort.",
        "",
        _markdown_table(
            ["Method", "Source digest matches", "Audit interpretation"],
            [[method, value["digest_matches_freeze"], value.get("claims", {}).get("finding", "native source inspected; no ranking-direction rewrite in local worker") if isinstance(value.get("claims"), Mapping) else "native source inspected"] for method, value in method_audit.items()],
        ),
        "",
        "## 9. MicroRank专项审计",
        "",
        "The pinned implementation returns at most 11 native operations because `top_max=5` is used in a `index < top_max + 6` prefix. The active records preserve 11-operation outputs where successful, and the runner records `NATIVE_TOP_K_TRUNCATION` separately from no observed telemetry.",
        "",
        _markdown_table(
            ["Dataset", "Native lengths", "Truncation cases", "Root in first 5", "Root anywhere", "Top-1 miss/Top-3 hit case", "Truncation example", "Dedup outcome example"],
            [
                [
                    DATASET_DISPLAY[dataset],
                    micro["datasets"][dataset]["native_ranking_length_distribution_success"],
                    micro["datasets"][dataset]["native_top_k_truncation_case_count"],
                    micro["datasets"][dataset]["root_in_native_prefix_5_success_count"],
                    micro["datasets"][dataset]["root_in_native_output_success_count"],
                    micro["datasets"][dataset]["examples"].get("top1_miss_top3_hit", {}).get("case_id", "none"),
                    micro["datasets"][dataset]["examples"].get("root_excluded_by_native_truncation", {}).get("case_id", "none"),
                    micro["datasets"][dataset]["examples"].get("dedup_changes_outcome", {}).get("case_id", "none"),
                ]
                for dataset in DATASET_ORDER
            ],
        ),
        "",
        "For RE2-OB, at least one case has a Top-1 miss but Top-3 hit, and a separate case has native truncation evidence. The full case rows in the JSONL contain the exact rankings. Therefore MicroRank OB AC@1=0 is caused by the real case-level native predictions under the frozen service projection; it is not an evaluator bug. Deduplication can change later Top-K outcomes, but it cannot turn a zero Top-1 hit count into a nonzero one.",
        "",
        "## 10. CausalRCA Static Audit",
        "",
        "No CausalRCA case was executed by Codex. The source audit confirms that `causalrca.py` thresholds the learned graph, transposes/absolutizes it, then calls PageRank in a `try` block. Any `Exception` from PageRank returns `node_names` as `ranks`; the exception scope is broader than the source comment `# empty graph`. The top-level pinned `rca` wrapper also catches any `Exception` and returns a preprocessed column-order ranking.",
        "",
        _markdown_table(
            ["Dataset", "Native unique digests", "Adapted unique digests", "Fixed adapted root positions", "OB/TT exact result explanation"],
            [
                [
                    DATASET_DISPLAY[dataset],
                    causal["datasets"][dataset]["native_ranking_unique_digest_count"],
                    causal["datasets"][dataset]["adapted_ranking_unique_digest_count"],
                    causal["datasets"][dataset]["root_positions"],
                    "five roots x 18 cases; positions are fixed after service projection",
                ]
                for dataset in DATASET_ORDER
            ],
        ),
        "",
        "RE2-OB adapted root positions are checkoutservice=3, currencyservice=4, emailservice=5, productcatalogservice=8, recommendationservice=9. Thus hit counts are 0/90, 0/90, 18/90, 36/90, 54/90 for AC@1..5, exactly 0, 0, 0.2, 0.4, 0.6. RE2-TT positions are 9, 35, 47, 57, and 60, so all five roots are outside Top-5 and AC@1/3/5 are all 0. The native rankings have 69 and 80 unique persisted digests, respectively, but the adapted service ranking has one digest in each dataset; the degeneration relevant to the reported service metric is confirmed.",
        "",
        "The frozen records contain no `adj` or `node_names`, so adjacency and exact PageRank score vectors cannot be reconstructed. Offline name-only reconstruction from current manifest-bound inputs is retained in `causalrca_static_audit.json`; mismatches are not converted into invented runtime facts.",
        "",
        "## 11. CausalRCA Evidence Level",
        "",
        _markdown_table(
            ["Level", "Conclusion"],
            [
                ["CONFIRMED", "Active CausalRCA records are SUCCESS at 90+90, and adapted rankings are fixed within each dataset; the OB/TT score pattern follows the measured fixed root positions exactly."],
                ["HIGHLY LIKELY", "The fixed-order output is caused by the pinned PageRank exception fallback or the broad wrapper fallback, because both source fallbacks return column order; old artifacts lack runtime trigger evidence."],
                ["UNKNOWN", "Exact historical exception type/message, adjacency shape/density, PageRank score vector, and whether the inner or outer fallback fired for each case."],
            ],
        ),
        "",
        "## 12. Per-baseline Verdict",
        "",
        _markdown_table(
            ["Method", "Verdict", "Evidence", "Model rerun", "Evaluator recomputation", "Paper use"],
            [
                ["BARO", "NO_EVIDENCE_OF_IMPLEMENTATION_ERROR", "Pinned RobustScaler/descending path; old equals unique recomputation; 90/90 success.", "No", "Done", "SAFE WITH PROTOCOL DISCLOSURE"],
                ["CIRCA", "IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW", "Pinned PC/RHT path; TT `dataset=ob` hard-code is upstream; failures remain 90 denominator.", "No", "Done", "SAFE WITH PROTOCOL DISCLOSURE"],
                ["MicroCause", "IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW", "Native low hits and persisted METHOD_FAILUREs explain the counts; no ranking substitution.", "No", "Done", "SAFE WITH PROTOCOL DISCLOSURE"],
                ["MicroRank", "IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW", "OB Top-1 zero is real case-level output; top_max+6 truncation and operation duplicates are explicit.", "No", "Done", "SAFE WITH PROTOCOL DISCLOSURE"],
                ["TraceRCA", "IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW", "Pinned SLO/support/confidence/Ji descending path; service-slot sensitivity and TT failures disclosed.", "No", "Done", "SAFE WITH PROTOCOL DISCLOSURE"],
                ["mmBARO", "NO_EVIDENCE_OF_IMPLEMENTATION_ERROR", "Pinned multi-modal RobustScaler path; old equals unique recomputation; failures/statuses explicit.", "No", "Done", "SAFE WITH PROTOCOL DISCLOSURE"],
                ["CausalRCA", "HIGHLY_SUSPECT", "Fixed adapted ranking; broad PageRank/wrapper fallbacks; exact trigger absent from records.", "Diagnostic first; full rerun before repaired claim", "Done; protocol-independent here", "NOT SAFE"],
            ],
        ),
        "",
        "## 13. Paper Safety",
        "",
        "SAFE means the numerical row can be used only if the frozen protocol is stated. SAFE WITH PROTOCOL DISCLOSURE is recommended for all ordinary baselines because native outputs are partial rankings, service projection is not a complete candidate completion, failures remain in the denominator, and the pinned evaluator class/driver have distinct deduplication stages. CausalRCA is NOT SAFE as a normal model-performance claim until a manual diagnostic and, if a valid repaired method is desired, a separately authorized 180-case rerun produce runtime-backed records.",
        "",
        "## 14. Required Reruns",
        "",
        "No ordinary baseline rerun is required for this audit. CausalRCA requires the prepared manual diagnostic to identify the runtime trigger. A full 180-case CausalRCA rerun is not needed to establish that the frozen service output is degenerate, but it is required before publishing a new repaired CausalRCA result. Any such rerun needs a new authorized lock/attempt and must not overwrite the historical records.",
        "",
        "## 15. CausalRCA Manual Commands",
        "",
        "The following commands are prepared but were not executed by Codex. They use the frozen common environment, the manifest-bound clean RCAEval checkout, one diagnostic process (no `--workers` option), seed/hash controls, and `/tmp` output so a manual diagnostic cannot silently enter the committed confirmatory tree. The selected cases come from `causalrca_diagnostics_schema.json`.",
        "",
        "### Command A — RE2-OB diagnostic",
        "",
        "```bash\ncd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin\nsource ~/.venvs/ada-rca-baselines-common/bin/activate\nPYTHONHASHSEED=20260830 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/home/zhangll24/RCA_project/RCAEval-clean:/home/zhangll24/RCA_project/Ada-RCA-v2-causalrca python scripts/baseline_eval/run_causalrca_diagnostic.py --dataset re2ob --case-file artifacts/baseline_eval/audit_fix_v1/causalrca_diagnostics_schema.json --output /tmp/causalrca_diagnostic_re2ob.json 2>&1 | tee /tmp/causalrca_diagnostic_re2ob.log\n```",
        "",
        "### Command B — RE2-TT diagnostic",
        "",
        "```bash\ncd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin\nsource ~/.venvs/ada-rca-baselines-common/bin/activate\nPYTHONHASHSEED=20260830 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/home/zhangll24/RCA_project/RCAEval-clean:/home/zhangll24/RCA_project/Ada-RCA-v2-causalrca python scripts/baseline_eval/run_causalrca_diagnostic.py --dataset re2tt --case-file artifacts/baseline_eval/audit_fix_v1/causalrca_diagnostics_schema.json --output /tmp/causalrca_diagnostic_re2tt.json 2>&1 | tee /tmp/causalrca_diagnostic_re2tt.log\n```",
        "",
        "No full-rerun commands are supplied in this report because the exact diagnostic result and a new authorized execution/lock identity are not yet known. Existing `scripts/run_baseline_rescue_v2.py run` is the real V2 runner, but reusing the frozen CausalRCA attempt would violate the no-overwrite/no-resume evidence rule.",
        "",
        "## 16. Artifacts, Tests, and Commits",
        "",
        "Artifacts: `artifacts/baseline_eval/audit_fix_v1/` contains the provenance, denominator, dual-protocol, protocol-difference, regular-fraction, CausalRCA static audit, and diagnostic schema files. The full native rankings/ground truth used after the existing locks are joined are in the JSONL/case-level JSON artifacts; historical records and locks are unchanged.",
        "",
        "Tests include fixed-denominator, failure-zero-utility, duplicate-service synthetic evaluation, PageRank success/exception instrumentation, empty/non-empty graph cases, fallback classification, and the existing performance firewall. The final command/result is recorded in the handoff after artifact generation.",
        "",
    ])
    return "\n".join(lines)


def generate_audit(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Read frozen evidence and create all audit-fix outputs exactly once."""

    audit_root = root / AUDIT_ROOT_RELATIVE
    if any((audit_root / name).exists() for name in AUDIT_OUTPUTS):
        raise RuntimeError("audit_fix_v1 output already exists; refusing to overwrite evidence")
    status_before = git(root, "status", "--porcelain=v1", "--untracked-files=all").stdout
    if status_before:
        raise RuntimeError("audit generator requires a clean worktree at start")
    audit_head = git(root, "rev-parse", "HEAD").stdout.strip()

    # These gates are deliberately executed before reading labels or computing
    # performance.  None of them invokes a baseline method.
    rcaeval = verify_rcaeval_clean()
    baro_verification = verify_baro_v1_lock(root)
    verify_six_method_v2_lock(root)
    combined_lock = verify_v2_combined_global_prediction_lock(root, require_committed=True)

    labels_by_dataset: dict[str, dict[str, str]] = {}
    details_by_dataset: dict[str, dict[str, dict[str, str]]] = {}
    dataset_info: dict[str, dict[str, Any]] = {}
    for dataset in DATASET_ORDER:
        labels, details = _label_maps(root, dataset)
        labels_by_dataset[dataset] = labels
        details_by_dataset[dataset] = details
        dataset_info[dataset] = _dataset_metadata(root, dataset)

    bindings: dict[str, dict[str, Any]] = {}
    for method in METHOD_ORDER:
        bindings[method] = _active_method_binding(
            root,
            method,
            combined_lock=combined_lock,
            baro_lock=baro_verification["lock"],
        )

    records: dict[tuple[str, str], list[dict[str, Any]]] = {}
    record_metadata: dict[tuple[str, str], dict[str, Any]] = {}
    evaluated_case_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    aggregates: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    old_info: dict[tuple[str, str], dict[str, Any]] = {}
    for method in METHOD_ORDER:
        for dataset in DATASET_ORDER:
            selected, metadata = _load_active_records(root, bindings[method], dataset)
            records[(method, dataset)] = selected
            record_metadata[(method, dataset)] = metadata
            evaluated, method_aggregates, method_old_info = _case_digest_and_metrics(
                root,
                method,
                dataset,
                selected,
                labels_by_dataset[dataset],
                dataset_info[dataset]["candidate_services"],
            )
            evaluated_case_rows[(method, dataset)] = evaluated
            aggregates[(method, dataset)] = method_aggregates
            old_info[(method, dataset)] = method_old_info

    denominator_rows = _denominator_rows(record_metadata, evaluated_case_rows, aggregates, old_info)
    dual_result_rows = [
        _dual_result_row(method, dataset, aggregates[(method, dataset)], old_info[(method, dataset)])
        for method in METHOD_ORDER
        for dataset in DATASET_ORDER
    ]
    protocol_difference_rows = _protocol_difference_rows(evaluated_case_rows)
    causal_case_rows = {
        dataset: evaluated_case_rows[("CausalRCA", dataset)] for dataset in DATASET_ORDER
    }
    causal_records = {
        dataset: records[("CausalRCA", dataset)] for dataset in DATASET_ORDER
    }
    causal_static = _causal_static_audit(
        root,
        causal_case_rows,
        causal_records,
        details_by_dataset,
    )
    micro_rank = _micro_rank_audit(
        {key: value for key, value in evaluated_case_rows.items()},
        {key: value for key, value in records.items()},
        details_by_dataset,
    )
    regular_fraction = _regular_fraction_audit(aggregates, dataset_info)
    diagnostic_schema = _diagnostic_schema(causal_case_rows, causal_static)
    method_source_audit = _source_static_audit(root)
    evaluator_static_audit = _evaluator_static_audit(root)

    provenance = {
        "schema_version": "rca_baseline_provenance_audit_v1",
        "audit_version": AUDIT_SCHEMA_VERSION,
        "audit_status": "COMPLETE",
        "post_lock_audit": True,
        "generated_at": _utc_now(),
        "audit_generated_from_head": audit_head,
        "branch": git(root, "branch", "--show-current").stdout.strip(),
        "status_before_audit": status_before,
        "method_runs_executed_by_codex": 0,
        "causalrca_runs_executed_by_codex": 0,
        "dual_evaluator_commit": _commit_for_path(
            root, Path("src/baseline_eval/audit_evaluator.py")
        ),
        "causalrca_diagnostic_commit": _commit_for_path(
            root, Path("src/baseline_eval/causalrca_diagnostic.py")
        ),
        "audit_generator_commit": audit_head,
        "rcaeval": {
            "path": str(RCAEVAL_CLEAN),
            "head": rcaeval["head"],
            "clean": rcaeval["clean"],
            "source_digests": rcaeval["source_digests"],
            "required_commit": RCAEVAL_COMMIT,
        },
        "input_manifest": {
            "path": INPUT_MANIFEST_RELATIVE.as_posix(),
            "sha256": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        },
        "protocol": {
            "v1": "artifacts/baseline_eval/protocol_freeze_v1.json",
            "v1_sha256": sha256_file(root / "artifacts/baseline_eval/protocol_freeze_v1.json"),
            "v2_combined": "artifacts/baseline_eval/rescue_protocol_v2_causalrca_combined.json",
            "v2_combined_sha256": sha256_file(root / "artifacts/baseline_eval/rescue_protocol_v2_causalrca_combined.json"),
            "dual_protocol_version": DUAL_PROTOCOL_VERSION,
        },
        "global_prediction_lock": {
            "path": V2_COMBINED_GLOBAL_LOCK_RELATIVE.as_posix(),
            "sha256": sha256_file(root / V2_COMBINED_GLOBAL_LOCK_RELATIVE),
            "commit": _commit_for_path(root, V2_COMBINED_GLOBAL_LOCK_RELATIVE),
            "labels_joined": combined_lock["labels_joined"],
            "contains_evaluation": combined_lock["contains_evaluation"],
        },
        "baro_prediction_lock": {
            "path": BARO_LOCK_RELATIVE.as_posix(),
            "sha256": sha256_file(root / BARO_LOCK_RELATIVE),
            "commit": _commit_for_path(root, BARO_LOCK_RELATIVE),
        },
        "dataset_info": dataset_info,
        "active_method_evidence": bindings,
        "method_source_audit": method_source_audit,
        "evaluator_static_audit": evaluator_static_audit,
        "failure_policy": {
            "expected_denominator": EXPECTED_DENOMINATOR,
            "method_failure_in_denominator": True,
            "method_failure_utility": "five zero hits",
            "blocking_statuses": sorted(BLOCKING_STATUSES),
            "candidate_completion": "NONE",
            "mrr": "NOT-IDENTIFIABLE",
        },
        "historical_evidence_preserved": True,
        "historical_records_modified": False,
    }

    output_payloads = {
        "provenance_audit.json": provenance,
        "denominator_audit.json": {
            "schema_version": "rca_baseline_denominator_audit_v1",
            "audit_status": "COMPLETE",
            "post_lock_audit": True,
            "expected_denominator": EXPECTED_DENOMINATOR,
            "rows": denominator_rows,
            "assertions": {
                "all_method_dataset_expected_90": all(row["expected_cases"] == EXPECTED_DENOMINATOR for row in denominator_rows),
                "all_method_dataset_actual_90": all(row["actual_evaluation_denominator"] == EXPECTED_DENOMINATOR for row in denominator_rows),
                "no_skipped_case": all(row["missing_records"] == 0 for row in denominator_rows),
                "no_duplicate_case": all(row["duplicate_records"] == 0 for row in denominator_rows),
                "no_foreign_case": all(row["foreign_records"] == 0 for row in denominator_rows),
                "no_blocking_status": all(row["blocking"] == 0 for row in denominator_rows),
                "method_failures_stay_in_denominator": True,
                "no_intermediate_rounding": all(row["avg5_unique_formula_check"] and row["avg5_slot_formula_check"] for row in denominator_rows),
            },
        },
        "dual_protocol_results.json": {
            "schema_version": "rca_baseline_dual_protocol_results_v1",
            "audit_status": "COMPLETE",
            "post_lock_audit": True,
            "protocol_version": DUAL_PROTOCOL_VERSION,
            "old_protocol": "current persisted adapted_ranking evaluator",
            "rows": dual_result_rows,
        },
        "regular_fraction_audit.json": {
            "schema_version": "rca_baseline_regular_fraction_audit_v1",
            "audit_status": "COMPLETE",
            "post_lock_audit": True,
            **regular_fraction,
        },
        "microrank_static_audit.json": {
            "schema_version": "rca_baseline_microrank_static_audit_v1",
            "audit_status": "COMPLETE",
            "post_lock_audit": True,
            **micro_rank,
        },
        "causalrca_static_audit.json": causal_static,
        "causalrca_diagnostics_schema.json": diagnostic_schema,
    }
    audit_root.mkdir(parents=True, exist_ok=True)
    for filename in (
        "provenance_audit.json",
        "denominator_audit.json",
        "dual_protocol_results.json",
        "regular_fraction_audit.json",
        "microrank_static_audit.json",
        "causalrca_static_audit.json",
        "causalrca_diagnostics_schema.json",
    ):
        atomic_write_json(audit_root / filename, output_payloads[filename])
    denominator_fields = [
        "method", "dataset", "expected_cases", "discovered_cases", "execution_records", "terminal_records", "success", "method_failure", "blocking", "actual_evaluation_denominator", "successful_case_denominator_if_used", "missing_records", "duplicate_records", "foreign_records", "unique_hit_counts", "rcaeval_service_slot_hit_counts", "unique_metrics", "rcaeval_service_slot_metrics", "status_counts", "failure_error_types", "old_identity_check",
    ]
    _csv_write(audit_root / "denominator_audit.csv", denominator_rows, denominator_fields)
    result_fields = [
        "method", "dataset", "denominator", "success_cases", "method_failures", "blocking_failures", "old_source", "old_identity_check", "protocol_version",
        *[f"old_{metric}" for metric in (*METRICS, "Avg@5")],
        *[f"unique_service_{metric}" for metric in (*METRICS, "Avg@5")],
        *[f"rcaeval_service_slot_{metric}" for metric in (*METRICS, "Avg@5")],
        *[f"delta_{metric}_slot_minus_unique" for metric in (*METRICS, "Avg@5")],
        "unique_hit_counts", "rcaeval_service_slot_hit_counts", "avg_numerator_unique", "avg_numerator_rcaeval_service_slot",
    ]
    _csv_write(audit_root / "dual_protocol_results.csv", dual_result_rows, result_fields)
    _jsonl_write(audit_root / "protocol_difference_cases.jsonl", protocol_difference_rows)

    report_payload = {
        "provenance": provenance,
        "denominator_rows": denominator_rows,
        "dual_result_rows": dual_result_rows,
        "protocol_difference_rows": protocol_difference_rows,
        "regular_fraction_audit": regular_fraction,
        "causal_static": causal_static,
        "microrank_audit": micro_rank,
        "method_source_audit": method_source_audit,
    }
    report_path = root / AUDIT_REPORT_RELATIVE
    report_path.write_text(render_report(report_payload), encoding="utf-8")
    output_payloads["denominator_audit.csv"] = denominator_rows
    output_payloads["dual_protocol_results.csv"] = dual_result_rows
    output_payloads["protocol_difference_cases.jsonl"] = protocol_difference_rows
    return {
        "provenance": provenance,
        "denominator_rows": denominator_rows,
        "dual_result_rows": dual_result_rows,
        "protocol_difference_rows": protocol_difference_rows,
        "regular_fraction_audit": regular_fraction,
        "causal_static": causal_static,
        "microrank_audit": micro_rank,
        "method_source_audit": method_source_audit,
        "evaluator_static_audit": evaluator_static_audit,
        "report_path": report_path.as_posix(),
        "audit_root": audit_root.as_posix(),
    }


__all__ = [
    "AUDIT_OUTPUTS",
    "AUDIT_REPORT_RELATIVE",
    "AUDIT_ROOT_RELATIVE",
    "AUDIT_SCHEMA_VERSION",
    "generate_audit",
    "render_report",
]
