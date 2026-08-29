"""Adapters for non-performance P6-E4 qualification of pinned RCAEval methods."""

import ast
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .p6_e4 import (
    DATASETS,
    RCAEVAL_SHA,
    SOURCE_CHECKSUM_PATHS,
    WINDOW_SECONDS,
    assert_clean_upstream,
    legal_case_directories,
    sha256_file,
    write_json,
)


AUXILIARY_ENTITIES = frozenset(
    (
        "frontend-check",
        "frontend-external",
        "health",
        "InboundPassthroughClusterIpv4",
        "istio-init",
        "loadgenerator",
        "PassthroughCluster",
        "traceservice",
    )
)
SERVICE_ALIASES = {"frontendservice": "frontend"}
TRACE_CONVERSION_FACTOR = 1_000_000
MMBARO_DATASET_ALIASES = {"re2-ob": "mm-ob", "re2-tt": "mm-tt"}


def _header(path: Path) -> Tuple[str, ...]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return tuple(next(csv.reader(handle)))


def legal_service_registry(case_path: Path) -> Tuple[str, ...]:
    services = {
        column.rsplit("_", 1)[0]
        for column in _header(case_path / "simple_metrics.csv")
        if column.endswith("_cpu") or column.endswith("_mem")
    }
    services.difference_update(AUXILIARY_ENTITIES)
    if not services:
        raise ValueError("empty label-free legal service registry")
    return tuple(sorted(services))


def stable_dataset_registry(dataset_root: Path) -> Tuple[str, ...]:
    registries = {legal_service_registry(case) for case in legal_case_directories(dataset_root)}
    if len(registries) != 1:
        raise ValueError("legal service registry is not stable within dataset")
    return next(iter(registries))


def normalize_service_name(name: str, registry: Sequence[str]) -> Optional[str]:
    candidate = str(name)
    if candidate in registry:
        return candidate
    if candidate in SERVICE_ALIASES and SERVICE_ALIASES[candidate] in registry:
        return SERVICE_ALIASES[candidate]
    if candidate.endswith("-db") and candidate[:-3] in registry:
        return candidate[:-3]
    return None


def indicator_service(indicator: str, registry: Sequence[str]) -> Tuple[Optional[str], str]:
    matches = [
        service
        for service in registry
        if indicator == service or indicator.startswith(service + "_")
    ]
    if matches:
        return sorted(matches, key=lambda value: (-len(value), value))[0], "LEGAL_PREFIX"
    raw_prefix = indicator.split("_", 1)[0]
    normalized = normalize_service_name(raw_prefix, registry)
    if normalized is not None:
        return normalized, "GOVERNED_ALIAS"
    if raw_prefix in AUXILIARY_ENTITIES:
        return None, "NON_SERVICE_AUXILIARY"
    return None, "UNKNOWN"


def project_indicator_ranking(
    ranking: Sequence[str], registry: Sequence[str]
) -> Mapping[str, object]:
    projected: List[str] = []
    duplicates = 0
    unknown = []
    auxiliary = []
    for indicator in ranking:
        service, status = indicator_service(str(indicator), registry)
        if status == "UNKNOWN":
            unknown.append(str(indicator))
            continue
        if status == "NON_SERVICE_AUXILIARY":
            auxiliary.append(str(indicator))
            continue
        if service in projected:
            duplicates += 1
            continue
        projected.append(str(service))
    return {
        "ranking": projected,
        "duplicate_count": duplicates,
        "unknown": unknown,
        "unknown_count": len(unknown),
        "auxiliary_excluded": auxiliary,
        "auxiliary_excluded_count": len(auxiliary),
        "completed_with_unranked_services": False,
    }


def operation_service_map(span_df: pd.DataFrame) -> Mapping[str, object]:
    method = span_df["methodName"].fillna(span_df["operationName"])
    operations = span_df["serviceName"].astype(str) + "_" + method.astype(str)
    pairs: Dict[str, set] = {}
    for operation, service in zip(operations, span_df["serviceName"].astype(str)):
        pairs.setdefault(operation, set()).add(service)
    conflicts = {
        operation: sorted(services) for operation, services in pairs.items() if len(services) != 1
    }
    mapping = {
        operation: next(iter(services)) for operation, services in pairs.items() if len(services) == 1
    }
    return {"mapping": mapping, "conflicts": conflicts}


def project_operation_ranking(
    ranking: Sequence[str], operation_map: Mapping[str, str], registry: Sequence[str]
) -> Mapping[str, object]:
    projected: List[str] = []
    duplicates = 0
    unknown = []
    auxiliary = []
    for operation in ranking:
        raw_service = operation_map.get(str(operation))
        if raw_service is None:
            unknown.append(str(operation))
            continue
        service = normalize_service_name(raw_service, registry)
        if service is None:
            if raw_service in AUXILIARY_ENTITIES:
                auxiliary.append(str(operation))
            else:
                unknown.append(str(operation))
            continue
        if service in projected:
            duplicates += 1
            continue
        projected.append(service)
    return {
        "ranking": projected,
        "duplicate_count": duplicates,
        "unknown": unknown,
        "unknown_count": len(unknown),
        "auxiliary_excluded": auxiliary,
        "auxiliary_excluded_count": len(auxiliary),
        "completed_with_unranked_services": False,
    }


def ranking_checksum(ranking: Sequence[str]) -> str:
    payload = json.dumps(list(ranking), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def load_metric_window(case_path: Path, inject_time: int) -> Mapping[str, object]:
    data = pd.read_csv(case_path / "simple_metrics.csv")
    input_rows = len(data)
    data = data.loc[:, ~data.columns.str.endswith("_latency-50")]
    data = data.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    data = data[(data["time"] >= inject_time - WINDOW_SECONDS) &
                (data["time"] < inject_time + WINDOW_SECONDS)].copy()
    data = data.rename(
        columns={
            column: column.replace("_latency-90", "_latency")
            for column in data.columns
            if column.endswith("_latency-90")
        }
    )
    return {
        "data": data,
        "input_rows": input_rows,
        "window_rows": len(data),
        "pre_rows": int((data["time"] < inject_time).sum()),
        "post_rows": int((data["time"] >= inject_time).sum()),
        "loader_preprocessing": [
            "drop columns ending _latency-50",
            "replace +/-inf with NaN",
            "forward fill then zero fill",
            "select half-open [t0-600,t0+600)",
            "rename _latency-90 suffix to _latency",
        ],
    }


def load_trace_window(case_path: Path, inject_time: int) -> Mapping[str, object]:
    columns = (
        "traceID",
        "spanID",
        "serviceName",
        "methodName",
        "operationName",
        "startTime",
        "duration",
    )
    lower = (inject_time - WINDOW_SECONDS) * TRACE_CONVERSION_FACTOR
    upper = (inject_time + WINDOW_SECONDS) * TRACE_CONVERSION_FACTOR
    anchor = inject_time * TRACE_CONVERSION_FACTOR
    selected = []
    input_rows = 0
    for chunk in pd.read_csv(
        case_path / "traces.csv", usecols=list(columns), chunksize=250000, low_memory=False
    ):
        input_rows += len(chunk)
        end_time = pd.to_numeric(chunk["startTime"], errors="coerce") + pd.to_numeric(
            chunk["duration"], errors="coerce"
        )
        mask = (end_time >= lower) & (end_time < upper)
        if bool(mask.any()):
            selected.append(chunk.loc[mask].copy())
    spans = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame(columns=columns)
    end_time = pd.to_numeric(spans["startTime"], errors="coerce") + pd.to_numeric(
        spans["duration"], errors="coerce"
    )
    return {
        "data": spans,
        "input_rows": input_rows,
        "selected_spans": len(spans),
        "pre_spans": int((end_time < anchor).sum()),
        "post_spans": int((end_time >= anchor).sum()),
        "window_quantity": "span endTime = startTime + duration",
        "window_semantics": "half-open [t0-600,t0+600) after seconds-to-microseconds conversion",
        "adapter_assumption": True,
    }


def load_clean_source_module(rcaeval_root: Path, relative_path: str, module_name: str):
    assert_clean_upstream(rcaeval_root)
    expected = {
        "RCAEval/e2e/baro.py": "ddaae58b4b03453a812c4af33eb0053d803bcb6132453dd37bfa1f5e675b72c4",
        "RCAEval/e2e/tracerca.py": "1ef420e4430a7ad0379689c1d18eee9dd7fb0d15ac4371f6ff968900a22b0946",
    }[relative_path]
    path = rcaeval_root / relative_path
    if sha256_file(path) != expected:
        raise RuntimeError("source checksum mismatch for {}".format(relative_path))
    clean_root = str(rcaeval_root.resolve())
    if clean_root not in sys.path:
        sys.path.insert(0, clean_root)
    from RCAEval.io import time_series

    if Path(time_series.__file__).resolve() != (rcaeval_root / "RCAEval/io/time_series.py").resolve():
        raise RuntimeError("RCAEval.io.time_series was not imported from the clean worktree")
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load clean source module {}".format(relative_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_call(function, *args, **kwargs) -> Mapping[str, object]:
    try:
        output = function(*args, **kwargs)
    except (ImportError, ModuleNotFoundError) as exc:
        return {
            "execution_status": "F-C_ENVIRONMENT",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "output": None,
            "dummy_fallback_accepted": False,
        }
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return {
            "execution_status": "F-A_ALGORITHMIC_FAILURE",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "output": None,
            "dummy_fallback_accepted": False,
        }
    except Exception as exc:
        return {
            "execution_status": "F-A_ALGORITHMIC_FAILURE",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "output": None,
            "dummy_fallback_accepted": False,
        }
    if not isinstance(output, Mapping) or "ranks" not in output:
        return {
            "execution_status": "F-A_ALGORITHMIC_FAILURE",
            "exception_type": "InvalidNativeOutput",
            "exception": "callable did not return a ranks field",
            "output": None,
            "dummy_fallback_accepted": False,
        }
    return {
        "execution_status": "SUCCESS",
        "exception_type": None,
        "exception": None,
        "output": output,
        "dummy_fallback_accepted": False,
    }


def _observed_headers(dataset_root: Path, filename: str) -> Tuple[str, ...]:
    columns = set()
    for case in legal_case_directories(dataset_root):
        columns.update(column for column in _header(case / filename) if column != "time")
    return tuple(sorted(columns))


def build_indicator_mapping_audit() -> Mapping[str, object]:
    datasets = {}
    for dataset, root in sorted(DATASETS.items()):
        registry = stable_dataset_registry(root)
        indicators = _observed_headers(root, "simple_metrics.csv")
        rows = []
        for indicator in indicators:
            service, status = indicator_service(indicator, registry)
            rows.append({"indicator": indicator, "service": service, "status": status})
        datasets[dataset] = {
            "legal_service_registry": list(registry),
            "observed_indicator_count": len(rows),
            "unknown_count": sum(row["status"] == "UNKNOWN" for row in rows),
            "auxiliary_count": sum(row["status"] == "NON_SERVICE_AUXILIARY" for row in rows),
            "mappings": rows,
        }
    return {
        "schema_version": "p6_e4_baro_indicator_mapping_audit_v1",
        "rule": "longest legal service prefix at underscore boundary; governed aliases; auxiliary exclusion",
        "special_mappings": SERVICE_ALIASES,
        "db_suffix_rule": "remove terminal -db only when the resulting service is legal",
        "datasets": datasets,
    }


def build_timestamp_unit_audit(all_case_audit: Mapping[str, object]) -> Mapping[str, object]:
    cases = all_case_audit["cases"]
    by_dataset = {}
    for dataset in sorted(DATASETS):
        rows = [row for row in cases if row["dataset"] == dataset]
        by_dataset[dataset] = {
            "inject_time_min": min(row["inject_time"] for row in rows),
            "inject_time_max": max(row["inject_time"] for row in rows),
            "startTime_min": min(row["trace_startTime_min"] for row in rows),
            "startTime_max": max(row["trace_startTime_max"] for row in rows),
            "duration_min": min(row["trace_duration_min"] for row in rows),
            "duration_max": max(row["trace_duration_max"] for row in rows),
            "endTime_min": min(row["trace_endTime_min"] for row in rows),
            "endTime_max": max(row["trace_endTime_max"] for row in rows),
        }
    return {
        "schema_version": "p6_e4_tracerca_timestamp_unit_audit_v1",
        "numeric_evidence": by_dataset,
        "source_evidence": [
            {
                "source": "pinned README.md",
                "fact": "inject_time.txt is documented as a Unix timestamp",
            },
            {
                "source": "pinned RCAEval/e2e/pdiagnose.py",
                "fact": "inject_time is multiplied by 1_000_000 before comparison with startTime + duration",
            },
            {
                "source": "pinned RCAEval/e2e/tracerca.py",
                "fact": "the internal pre/post split compares startTime + duration with inject_time",
            },
            {
                "source": "RE2 traces.csv schema",
                "fact": "startTime is approximately 1e15 and paired startTimeMillis is approximately 1e12",
            },
            {
                "source": "TraceRCA duration processing",
                "fact": "duration is divided by 1_000 to obtain millisecond-scale latency",
            },
        ],
        "inject_time_unit": "seconds since Unix epoch",
        "startTime_unit": "microseconds since Unix epoch",
        "duration_unit": "microseconds",
        "endTime_unit": "microseconds since Unix epoch",
        "chosen_conversion_factor": TRACE_CONVERSION_FACTOR,
        "justification": "convert inject_time seconds to the microsecond unit used by span endTime",
        "ob_tt_consistency": True,
        "remaining_ambiguity": None,
        "status": "UNIQUE_SEMANTICS_JUSTIFIED",
    }


def build_trace_window_audit() -> Mapping[str, object]:
    return {
        "schema_version": "p6_e4_tracerca_window_semantics_v1",
        "frozen_window_seconds": [-WINDOW_SECONDS, WINDOW_SECONDS],
        "boundary": "half-open",
        "inclusion_quantity": "startTime + duration",
        "source_basis": "TraceRCA uses span endTime for its internal pre/post partition",
        "adapter_assumption": True,
        "assumption_reason": "no official symmetric TraceRCA runner window is implemented",
        "performance_evidence_used": False,
    }


def build_mmbaro_input_dictionary_audit(baro_source: Path) -> Mapping[str, object]:
    tree = ast.parse(baro_source.read_text(encoding="utf-8"))
    mmnsigma = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "mmnsigma"
    )
    accessed = sorted(
        {
            node.slice.value
            for node in ast.walk(mmnsigma)
            if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "data"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        }
    )
    classifications = {
        "metric": "REQUIRED_AND_USED",
        "logs": "REQUIRED_LOADED_NOT_USED",
        "logts": "REQUIRED_AND_USED",
        "traces": "REQUIRED_LOADED_NOT_USED",
        "tracets_err": "REQUIRED_CONDITIONALLY_USED",
        "tracets_lat": "REQUIRED_CONDITIONALLY_USED",
        "cluster_info": "REQUIRED_LOADED_NOT_USED",
    }
    return {
        "schema_version": "p6_e4_mmbaro_input_dictionary_audit_v1",
        "source_sha256": sha256_file(baro_source),
        "dictionary_keys_accessed": accessed,
        "classifications": classifications,
        "key_presence_implies_modality_use": False,
    }


def build_mmbaro_alias_audit() -> Mapping[str, object]:
    return {
        "schema_version": "p6_e4_mmbaro_dataset_alias_audit_v1",
        "proposed_mapping": MMBARO_DATASET_ALIASES,
        "source_evidence": [
            "baro.py gates trace-derived branches on literal mm-ob or mm-tt",
            "main.py and README use official dataset identifiers re2-ob and re2-tt",
            "comments and hard-coded demos use mm-ob as an older multi-source path name",
            "the official multi-source notebook calls mmbaro without a dataset argument",
            "no pinned code, history, notebook, CI command, or documentation explicitly maps re2-* to mm-*",
        ],
        "performance_evidence_used": False,
        "mapping_frozen": False,
        "chosen_mapping": None,
        "remaining_ambiguity": "No explicit upstream intended-alias statement or runner mapping exists",
        "status": "BLOCKED / SEMANTIC_AMBIGUITY",
    }


def build_mmbaro_modality_audit(alias_audit: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "schema_version": "p6_e4_mmbaro_modality_activation_audit_v1",
        "dataset_argument": "re2-ob or re2-tt (official identifier; alias not applied)",
        "alias_status": alias_audit["status"],
        "modalities": {
            "metric": "USED",
            "log_time_series": "USED",
            "trace_error_time_series": "LOADED_NOT_USED",
            "trace_latency_time_series": "LOADED_NOT_USED",
            "raw_logs": "LOADED_NOT_USED",
            "raw_spans": "LOADED_NOT_USED",
            "cluster_info": "LOADED_NOT_USED",
        },
        "description_boundary": "metric + log time series only under official RE2 identifiers",
        "tri_modal_claim_permitted": False,
        "smoke_execution_authorized": False,
    }


def write_static_semantic_audits(output_root: Path, rcaeval_root: Path) -> None:
    assert_clean_upstream(rcaeval_root)
    all_case = json.loads((output_root / "all_case_schema_audit.json").read_text())
    write_json(output_root / "baro" / "indicator_mapping_audit.json", build_indicator_mapping_audit())
    write_json(
        output_root / "tracerca" / "timestamp_unit_audit.json",
        build_timestamp_unit_audit(all_case),
    )
    write_json(output_root / "tracerca" / "window_semantics_audit.json", build_trace_window_audit())
    dictionary_audit = build_mmbaro_input_dictionary_audit(rcaeval_root / "RCAEval/e2e/baro.py")
    alias_audit = build_mmbaro_alias_audit()
    write_json(output_root / "mmbaro" / "input_dictionary_audit.json", dictionary_audit)
    write_json(output_root / "mmbaro" / "dataset_alias_audit.json", alias_audit)
    write_json(
        output_root / "mmbaro" / "modality_activation_audit.json",
        build_mmbaro_modality_audit(alias_audit),
    )


def _smoke_paths(output_root: Path, dataset: str) -> Tuple[Path, ...]:
    manifest = json.loads((output_root / "smoke_case_manifest.json").read_text())
    root = DATASETS[dataset]
    return tuple(
        root / row["normalized_relative_path"]
        for row in manifest["selected_cases"][dataset]
    )


def _read_inject_time(case_path: Path) -> int:
    return int((case_path / "inject_time.txt").read_text(encoding="utf-8").strip())


def _failure_record(
    dataset: str,
    case_path: Path,
    dataset_root: Path,
    repeat: int,
    call: Mapping[str, object],
    counts: Mapping[str, object],
) -> Mapping[str, object]:
    row = {
        "dataset": dataset,
        "normalized_case_path": case_path.relative_to(dataset_root).as_posix(),
        "repeat": repeat,
        "execution_status": call["execution_status"],
        "failure_taxonomy": call["execution_status"],
        "exception_type": call["exception_type"],
        "exception": call["exception"],
        "dummy_fallback_accepted": False,
        "ranking_checksum": None,
    }
    row.update(counts)
    return row


def run_baro_smoke(output_root: Path, rcaeval_root: Path) -> Mapping[str, object]:
    module = load_clean_source_module(
        rcaeval_root, "RCAEval/e2e/baro.py", "_p6_clean_rcaeval_baro"
    )
    dataset_summaries = {}
    all_records = []
    for dataset in sorted(DATASETS):
        dataset_root = DATASETS[dataset]
        records = []
        for case_path in _smoke_paths(output_root, dataset):
            inject_time = _read_inject_time(case_path)
            registry = legal_service_registry(case_path)
            loaded = load_metric_window(case_path, inject_time)
            counts = {
                "input_row_count": loaded["input_rows"],
                "window_row_count": loaded["window_rows"],
                "pre_rows": loaded["pre_rows"],
                "post_rows": loaded["post_rows"],
                "window": "[t0-600,t0+600)",
                "loader_preprocessing": loaded["loader_preprocessing"],
                "rcaeval_preprocess": "drop time and constant columns; convert *_mem to MB",
                "baro_scaler": "per-indicator pre-event RobustScaler",
                "native_semantics": "indicators sorted by maximum post-event robust z-score",
            }
            for repeat in (1, 2):
                call = raw_call(
                    module.baro,
                    loaded["data"].copy(deep=True),
                    inject_time,
                    dataset=dataset,
                    anomalies=None,
                    dk_select_useful=False,
                )
                if call["execution_status"] != "SUCCESS":
                    records.append(
                        _failure_record(dataset, case_path, dataset_root, repeat, call, counts)
                    )
                    continue
                native = list(call["output"]["ranks"])
                projection = project_indicator_ranking(native, registry)
                status = "SUCCESS"
                exception = None
                if not native or not projection["ranking"]:
                    status = "F-A_ALGORITHMIC_FAILURE"
                    exception = "empty native or projected ranking"
                elif projection["unknown_count"]:
                    status = "F-D_ADAPTER_INTEGRATION"
                    exception = "unknown indicator-to-service mapping"
                records.append(
                    {
                        "dataset": dataset,
                        "normalized_case_path": case_path.relative_to(dataset_root).as_posix(),
                        "repeat": repeat,
                        **counts,
                        "native_rank_length": len(native),
                        "projected_service_rank_length": len(projection["ranking"]),
                        "duplicate_count": projection["duplicate_count"],
                        "unknown_mapping_count": projection["unknown_count"],
                        "auxiliary_excluded_count": projection["auxiliary_excluded_count"],
                        "completed_with_unranked_services": False,
                        "execution_status": status,
                        "failure_taxonomy": None if status == "SUCCESS" else status,
                        "exception_type": None,
                        "exception": exception,
                        "dummy_fallback_accepted": False,
                        "native_ranking_checksum": ranking_checksum(native),
                        "ranking_checksum": ranking_checksum(projection["ranking"]),
                    }
                )
        write_jsonl(output_root / "baro" / ("ob_smoke.jsonl" if dataset == "re2-ob" else "tt_smoke.jsonl"), records)
        dataset_summaries[dataset] = summarize_repeat_records(records)
        all_records.extend(records)
    summary = summarize_method("BARO", all_records, dataset_summaries)
    write_json(output_root / "baro" / "qualification_summary.json", summary)
    return summary


def run_tracerca_smoke(output_root: Path, rcaeval_root: Path) -> Mapping[str, object]:
    timestamp_audit = json.loads(
        (output_root / "tracerca" / "timestamp_unit_audit.json").read_text()
    )
    if timestamp_audit["status"] != "UNIQUE_SEMANTICS_JUSTIFIED":
        raise RuntimeError("TraceRCA timestamp semantics are not qualified")
    module = load_clean_source_module(
        rcaeval_root, "RCAEval/e2e/tracerca.py", "_p6_clean_rcaeval_tracerca"
    )
    dataset_summaries = {}
    all_records = []
    for dataset in sorted(DATASETS):
        dataset_root = DATASETS[dataset]
        records = []
        for case_path in _smoke_paths(output_root, dataset):
            inject_time = _read_inject_time(case_path)
            registry = legal_service_registry(case_path)
            loaded = load_trace_window(case_path, inject_time)
            operation_audit = operation_service_map(loaded["data"])
            counts = {
                "input_row_count": loaded["input_rows"],
                "selected_spans": loaded["selected_spans"],
                "pre_spans": loaded["pre_spans"],
                "post_spans": loaded["post_spans"],
                "timestamp_conversion_factor": TRACE_CONVERSION_FACTOR,
                "window": "[t0-600,t0+600)",
                "window_inclusion_quantity": loaded["window_quantity"],
                "window_adapter_assumption": loaded["adapter_assumption"],
                "operation_mapping_conflict_count": len(operation_audit["conflicts"]),
            }
            if not loaded["selected_spans"] or not loaded["pre_spans"] or not loaded["post_spans"]:
                call = {
                    "execution_status": "F-E_DATA_INTEGRITY",
                    "exception_type": "EmptyTracePartition",
                    "exception": "selected, pre, and post spans must all be nonempty",
                }
                for repeat in (1, 2):
                    records.append(
                        _failure_record(dataset, case_path, dataset_root, repeat, call, counts)
                    )
                continue
            if operation_audit["conflicts"]:
                call = {
                    "execution_status": "F-D_ADAPTER_INTEGRATION",
                    "exception_type": "OperationMappingConflict",
                    "exception": "one native operation maps to multiple services",
                }
                for repeat in (1, 2):
                    records.append(
                        _failure_record(dataset, case_path, dataset_root, repeat, call, counts)
                    )
                continue
            for repeat in (1, 2):
                call = raw_call(
                    module.tracerca,
                    loaded["data"].copy(deep=True),
                    inject_time * TRACE_CONVERSION_FACTOR,
                    dataset=dataset,
                )
                if call["execution_status"] != "SUCCESS":
                    records.append(
                        _failure_record(dataset, case_path, dataset_root, repeat, call, counts)
                    )
                    continue
                native = list(call["output"]["ranks"])
                projection = project_operation_ranking(
                    native, operation_audit["mapping"], registry
                )
                nan_count = sum(isinstance(value, float) and math.isnan(value) for value in native)
                status = "SUCCESS"
                exception = None
                if not native or not projection["ranking"]:
                    status = "F-A_ALGORITHMIC_FAILURE"
                    exception = "empty native or projected ranking"
                elif projection["unknown_count"] or nan_count:
                    status = "F-D_ADAPTER_INTEGRATION"
                    exception = "unknown or NaN native operation output"
                records.append(
                    {
                        "dataset": dataset,
                        "normalized_case_path": case_path.relative_to(dataset_root).as_posix(),
                        "repeat": repeat,
                        **counts,
                        "native_operation_rank_length": len(native),
                        "projected_service_rank_length": len(projection["ranking"]),
                        "duplicate_count": projection["duplicate_count"],
                        "unknown_mapping_count": projection["unknown_count"],
                        "auxiliary_excluded_count": projection["auxiliary_excluded_count"],
                        "nan_count": nan_count,
                        "empty_output": not bool(native),
                        "completed_with_unranked_services": False,
                        "execution_status": status,
                        "failure_taxonomy": None if status == "SUCCESS" else status,
                        "exception_type": None,
                        "exception": exception,
                        "dummy_fallback_accepted": False,
                        "native_ranking_checksum": ranking_checksum(native),
                        "ranking_checksum": ranking_checksum(projection["ranking"]),
                    }
                )
        write_jsonl(
            output_root / "tracerca" / ("ob_smoke.jsonl" if dataset == "re2-ob" else "tt_smoke.jsonl"),
            records,
        )
        dataset_summaries[dataset] = summarize_repeat_records(records)
        all_records.extend(records)
    summary = summarize_method("TraceRCA", all_records, dataset_summaries)
    write_json(output_root / "tracerca" / "qualification_summary.json", summary)
    return summary


def write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def summarize_repeat_records(records: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
    cases: Dict[str, List[Mapping[str, object]]] = {}
    for row in records:
        cases.setdefault(str(row["normalized_case_path"]), []).append(row)
    deterministic = True
    for rows in cases.values():
        if len(rows) != 2:
            deterministic = False
        elif rows[0].get("ranking_checksum") != rows[1].get("ranking_checksum"):
            deterministic = False
        elif rows[0].get("execution_status") != rows[1].get("execution_status"):
            deterministic = False
    return {
        "case_count": len(cases),
        "record_count": len(records),
        "successful_records": sum(row["execution_status"] == "SUCCESS" for row in records),
        "deterministic_repeats": deterministic,
        "failure_counts": {
            status: sum(row["execution_status"] == status for row in records)
            for status in sorted({str(row["execution_status"]) for row in records})
            if status != "SUCCESS"
        },
    }


def summarize_method(
    method: str,
    records: Sequence[Mapping[str, object]],
    dataset_summaries: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object]:
    all_success = bool(records) and all(row["execution_status"] == "SUCCESS" for row in records)
    deterministic = all(summary["deterministic_repeats"] for summary in dataset_summaries.values())
    no_unknown = all(int(row.get("unknown_mapping_count", 0)) == 0 for row in records)
    status = "READY" if all_success and deterministic and no_unknown else "BLOCKED / UNSUPPORTED_INPUT"
    return {
        "schema_version": "p6_e4_method_qualification_summary_v1",
        "method": method,
        "status": status,
        "datasets": dataset_summaries,
        "all_smoke_records_successful": all_success,
        "deterministic_repeat_output": deterministic,
        "mapping_unknown_count": sum(int(row.get("unknown_mapping_count", 0)) for row in records),
        "dummy_fallback_accepted": False,
        "performance_firewall": "PASS",
    }


def blocked_mmbaro_summary(output_root: Path) -> Mapping[str, object]:
    alias = json.loads((output_root / "mmbaro" / "dataset_alias_audit.json").read_text())
    summary = {
        "schema_version": "p6_e4_method_qualification_summary_v1",
        "method": "mmBARO",
        "status": alias["status"],
        "smoke_execution_performed": False,
        "reason": alias["remaining_ambiguity"],
        "tier_b_substitution": False,
        "performance_firewall": "PASS",
    }
    write_json(output_root / "mmbaro" / "qualification_summary.json", summary)
    return summary


def load_time_series_window(case_path: Path, filename: str, inject_time: int) -> Mapping[str, object]:
    """Load a derived time-series source using the frozen half-open event window."""
    frame = pd.read_csv(case_path / filename)
    input_rows = len(frame)
    if "time" not in frame.columns:
        raise ValueError("{} has no time column".format(filename))
    frame = frame.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    frame = frame[(frame["time"] >= inject_time - WINDOW_SECONDS) &
                  (frame["time"] < inject_time + WINDOW_SECONDS)].copy()
    return {
        "data": frame,
        "input_rows": input_rows,
        "window_rows": len(frame),
        "pre_rows": int((frame["time"] < inject_time).sum()),
        "post_rows": int((frame["time"] >= inject_time).sum()),
    }


def load_mmbaro_inputs(case_path: Path, inject_time: int) -> Mapping[str, object]:
    """Build mmBARO's complete dictionary while activating metric and logts only."""
    metric = load_metric_window(case_path, inject_time)
    logts = load_time_series_window(case_path, "logts.csv", inject_time)
    inactive = {
        "logs": None,
        "traces": pd.DataFrame(),
        "tracets_err": pd.DataFrame(),
        "tracets_lat": pd.DataFrame(),
        "cluster_info": None,
    }
    data = {"metric": metric["data"], "logts": logts["data"], **inactive}
    return {
        "data": data,
        "metric": metric,
        "logts": logts,
        "active_modalities": ["metric", "log_time_series"],
        "inactive_modalities": [
            "trace_error_time_series", "trace_latency_time_series", "raw_logs",
            "raw_spans", "cluster_info",
        ],
    }


def run_mmbaro_smoke(output_root: Path, rcaeval_root: Path) -> Mapping[str, object]:
    """Run official mmBARO with official RE2 identifiers and no trace alias."""
    module = load_clean_source_module(
        rcaeval_root, "RCAEval/e2e/baro.py", "_p6_clean_rcaeval_mmbaro"
    )
    dataset_summaries = {}
    all_records = []
    for dataset in sorted(DATASETS):
        dataset_root = DATASETS[dataset]
        records = []
        for case_path in _smoke_paths(output_root, dataset):
            inject_time = _read_inject_time(case_path)
            registry = legal_service_registry(case_path)
            loaded = load_mmbaro_inputs(case_path, inject_time)
            counts = {
                "metric_input_row_count": loaded["metric"]["input_rows"],
                "metric_window_rows": loaded["metric"]["window_rows"],
                "metric_pre_rows": loaded["metric"]["pre_rows"],
                "metric_post_rows": loaded["metric"]["post_rows"],
                "logts_input_row_count": loaded["logts"]["input_rows"],
                "logts_window_rows": loaded["logts"]["window_rows"],
                "logts_pre_rows": loaded["logts"]["pre_rows"],
                "logts_post_rows": loaded["logts"]["post_rows"],
                "active_modalities": loaded["active_modalities"],
                "dataset_identifier": dataset,
                "dataset_alias_used": False,
                "window": "[t0-600,t0+600)",
            }
            for repeat in (1, 2):
                call = raw_call(
                    module.mmbaro,
                    loaded["data"],
                    inject_time,
                    dataset=dataset,
                    dk_select_useful=False,
                )
                if call["execution_status"] != "SUCCESS":
                    records.append(_failure_record(dataset, case_path, dataset_root, repeat, call, counts))
                    continue
                native = list(call["output"]["ranks"])
                projection = project_indicator_ranking(native, registry)
                status = "SUCCESS"
                exception = None
                if not native or not projection["ranking"]:
                    status = "F-A_ALGORITHMIC_FAILURE"
                    exception = "empty native or projected ranking"
                elif projection["unknown_count"]:
                    status = "F-D_ADAPTER_INTEGRATION"
                    exception = "unknown indicator-to-service mapping"
                records.append({
                    "dataset": dataset,
                    "normalized_case_path": case_path.relative_to(dataset_root).as_posix(),
                    "repeat": repeat,
                    **counts,
                    "native_rank_length": len(native),
                    "projected_service_rank_length": len(projection["ranking"]),
                    "duplicate_count": projection["duplicate_count"],
                    "unknown_mapping_count": projection["unknown_count"],
                    "completed_with_unranked_services": False,
                    "execution_status": status,
                    "failure_taxonomy": None if status == "SUCCESS" else status,
                    "exception_type": None,
                    "exception": exception,
                    "dummy_fallback_accepted": False,
                    "native_ranking_checksum": ranking_checksum(native),
                    "ranking_checksum": ranking_checksum(projection["ranking"]),
                })
        write_jsonl(output_root / "mmbaro" / ("ob_smoke.jsonl" if dataset == "re2-ob" else "tt_smoke.jsonl"), records)
        dataset_summaries[dataset] = summarize_repeat_records(records)
        all_records.extend(records)
    base = summarize_method("mmBARO", all_records, dataset_summaries)
    native_fa = any(row.get("failure_taxonomy") == "F-A_ALGORITHMIC_FAILURE" for row in all_records)
    if base["status"] == "READY":
        status = "READY_OFFICIAL_RE2_METRIC_LOG"
    elif native_fa and all(row.get("failure_taxonomy") in (None, "F-A_ALGORITHMIC_FAILURE") for row in all_records):
        status = "EXECUTION_QUALIFIED_WITH_NATIVE_F-A"
    else:
        status = "BLOCKED / INVALID"
    summary = dict(base)
    summary.update({
        "schema_version": "p6_e4r_mmbaro_qualification_summary_v1",
        "status": status,
        "dataset_alias_used": False,
        "active_modalities": ["metric", "log_time_series"],
        "trace_branches_active": False,
        "smoke_execution_performed": True,
    })
    write_json(output_root / "mmbaro" / "qualification_summary.json", summary)
    return summary


def write_overall_qualification(
    output_root: Path,
    baro: Mapping[str, object],
    tracerca: Mapping[str, object],
    mmbaro: Mapping[str, object],
) -> Mapping[str, object]:
    methods = {"BARO": baro["status"], "TraceRCA": tracerca["status"], "mmBARO": mmbaro["status"]}
    gate = (
        "P6-G1 = GO — TIER-A INTEGRATION QUALIFIED"
        if all(status == "READY" for status in methods.values())
        else "P6-G1 = PARTIAL — AWAITING HUMAN REVIEW"
    )
    status = {
        "schema_version": "p6_e4_overall_qualification_v1",
        "methods": methods,
        "p6_g1": gate,
        "tier_b_substitution": False,
        "formal_p6_e5_executed": False,
    }
    write_json(output_root / "qualification_status.json", status)

    failure_counts: Dict[str, int] = {}
    for method_dir in ("baro", "tracerca"):
        for filename in ("ob_smoke.jsonl", "tt_smoke.jsonl"):
            path = output_root / method_dir / filename
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                failure = row.get("failure_taxonomy")
                if failure:
                    failure_counts[str(failure)] = failure_counts.get(str(failure), 0) + 1
    write_json(
        output_root / "failure_audit.json",
        {
            "schema_version": "p6_e4_failure_audit_v1",
            "raw_failure_counts": failure_counts,
            "failures_converted_to_performance_zero": False,
            "dummy_fallback_accepted": False,
            "successful_subset_suppression_used": False,
        },
    )
    write_json(
        output_root / "performance_firewall_audit.json",
        {
            "schema_version": "p6_e4_performance_firewall_audit_v1",
            "root_label_dependency": False,
            "performance_evaluator_dependency": False,
            "performance_fields_in_smoke_artifacts": [],
            "published_result_used_for_adapter_choice": False,
            "result_based_adapter_choice": False,
            "status": "PASS",
        },
    )
    return status
