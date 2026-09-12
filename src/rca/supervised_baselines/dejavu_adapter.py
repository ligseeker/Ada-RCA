"""Label-blind input audit and preparation primitives for the DejaVu adapter."""

import csv
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np


TRACE_REQUIRED_COLUMNS = (
    "time",
    "traceID",
    "spanID",
    "serviceName",
    "methodName",
    "operationName",
    "startTimeMillis",
    "startTime",
    "duration",
    "statusCode",
    "parentSpanID",
)
METRIC_OFFSETS_SECONDS = tuple(range(-600, 541, 60))
METRIC_SUFFIXES = ("cpu", "mem")


def _file_record(path: Path) -> Mapping[str, object]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _map_trace_service(raw_service: str, candidates: Sequence[str], dataset: str):
    service = str(raw_service).strip()
    if dataset == "re2ob" and service == "frontendservice":
        service = "frontend"
    return service if service in candidates else None


def audit_case_source(
    source_row: Mapping[str, object], candidates: Sequence[str], dataset: str
) -> Mapping[str, object]:
    """Audit one label-free RE2 source row and derive its explicit call edges."""

    if dataset not in ("re2ob", "re2tt"):
        raise ValueError("dataset must be re2ob or re2tt")
    canonical = tuple(str(value) for value in candidates)
    if len(canonical) < 2 or len(set(canonical)) != len(canonical):
        raise ValueError("candidate registry must be unique")
    required_fields = ("case_id", "simple_metrics_path", "traces_path", "inject_time_path")
    if not all(field in source_row for field in required_fields):
        raise ValueError("source row lacks required label-free paths")

    metric_path = Path(str(source_row["simple_metrics_path"]))
    trace_path = Path(str(source_row["traces_path"]))
    inject_path = Path(str(source_row["inject_time_path"]))
    for path in (metric_path, trace_path, inject_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    injection_time = float(inject_path.read_text(encoding="utf-8").strip())
    required_times = {injection_time + offset for offset in METRIC_OFFSETS_SECONDS}
    required_metric_columns = tuple(
        "{}_{}".format(candidate, suffix)
        for suffix in METRIC_SUFFIXES
        for candidate in canonical
    )

    observed_metric_samples = set()
    nonfinite_metric_samples = 0
    with metric_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        metric_header = tuple(reader.fieldnames or ())
        missing_metric_columns = sorted(set(required_metric_columns) - set(metric_header))
        if "time" not in metric_header:
            raise ValueError("simple_metrics.csv lacks time")
        for row in reader:
            try:
                timestamp = float(row["time"])
            except (TypeError, ValueError):
                continue
            if timestamp not in required_times:
                continue
            for column in required_metric_columns:
                if column not in row:
                    continue
                try:
                    value = float(row[column])
                except (TypeError, ValueError):
                    nonfinite_metric_samples += 1
                    continue
                if not math.isfinite(value):
                    nonfinite_metric_samples += 1
                    continue
                observed_metric_samples.add((timestamp, column))

    forward_fillable_samples = 0
    unfillable_samples = 0
    for column in required_metric_columns:
        has_prior_value = False
        for timestamp in sorted(required_times):
            if (timestamp, column) in observed_metric_samples:
                has_prior_value = True
            elif has_prior_value:
                forward_fillable_samples += 1
            else:
                unfillable_samples += 1

    span_rows = []
    span_services = {}
    span_service_sets = {}
    duplicate_span_keys = set()
    raw_trace_services = set()
    with trace_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        trace_header = tuple(reader.fieldnames or ())
        missing_trace_columns = sorted(set(TRACE_REQUIRED_COLUMNS) - set(trace_header))
        for row in reader:
            trace_id = str(row.get("traceID", "")).strip()
            span_id = str(row.get("spanID", "")).strip()
            parent_id = str(row.get("parentSpanID", "")).strip()
            raw_service = str(row.get("serviceName", "")).strip()
            if raw_service:
                raw_trace_services.add(raw_service)
            mapped_service = _map_trace_service(raw_service, canonical, dataset)
            if trace_id and span_id:
                key = (trace_id, span_id)
                if key in span_services:
                    duplicate_span_keys.add(key)
                    span_service_sets[key].add(mapped_service)
                else:
                    span_services[key] = mapped_service
                    span_service_sets[key] = {mapped_service}
            span_rows.append((trace_id, parent_id, mapped_service))

    edges = set()
    missing_parent_span_joins = 0
    for trace_id, parent_id, child_service in span_rows:
        if not trace_id or not parent_id:
            continue
        parent_key = (trace_id, parent_id)
        if parent_key not in span_services:
            missing_parent_span_joins += 1
            continue
        parent_service = span_services[parent_key]
        if (
            parent_service is not None
            and child_service is not None
            and parent_service != child_service
        ):
            edges.add((parent_service, child_service))

    mapped_raw_services = {
        raw for raw in raw_trace_services
        if _map_trace_service(raw, canonical, dataset) is not None
    }
    unmapped_services = sorted(raw_trace_services - mapped_raw_services)
    edge_nodes = sorted({node for edge in edges for node in edge})
    expected_samples = len(required_times) * len(required_metric_columns)
    return {
        "case_id": str(source_row["case_id"]),
        "dataset": dataset,
        "files": {
            "inject_time": _file_record(inject_path),
            "simple_metrics": _file_record(metric_path),
            "traces": _file_record(trace_path),
        },
        "trace_header": list(trace_header),
        "missing_trace_columns": missing_trace_columns,
        "metric_header_count": len(metric_header),
        "missing_metric_columns": missing_metric_columns,
        "required_metric_samples": expected_samples,
        "observed_required_metric_samples": len(observed_metric_samples),
        "missing_required_metric_samples": expected_samples - len(observed_metric_samples),
        "nonfinite_required_metric_samples": nonfinite_metric_samples,
        "forward_fillable_metric_samples": forward_fillable_samples,
        "unfillable_metric_samples": unfillable_samples,
        "duplicate_span_key_count": len(duplicate_span_keys),
        "ambiguous_span_key_count": sum(
            len({service for service in services if service is not None}) > 1
            for services in span_service_sets.values()
        ),
        "missing_parent_span_join_count": missing_parent_span_joins,
        "edges": [list(edge) for edge in sorted(edges)],
        "edge_node_coverage": edge_nodes,
        "isolated_candidates": sorted(set(canonical) - set(edge_nodes)),
        "unmapped_trace_services": unmapped_services,
    }


def _audit_case_args(args):
    return audit_case_source(*args)


def audit_source_registry(
    sources_path: Path,
    candidate_registry_path: Path,
    dataset: str,
    *,
    expected_cases: int = 90,
    workers: int = 1,
) -> Mapping[str, object]:
    """Audit a complete label-free source registry with deterministic output."""

    sources_path = Path(sources_path)
    candidate_registry_path = Path(candidate_registry_path)
    candidate_doc = json.loads(candidate_registry_path.read_text(encoding="utf-8"))
    candidates = tuple(str(value) for value in candidate_doc["services"])
    source_rows = tuple(
        json.loads(line)
        for line in sources_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    case_ids = tuple(str(row.get("case_id", "")) for row in source_rows)
    if len(source_rows) != expected_cases:
        raise ValueError("source registry case count mismatch")
    if not all(case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError("source registry case IDs must be complete and unique")
    if workers < 1:
        raise ValueError("workers must be positive")

    args = tuple((row, candidates, dataset) for row in source_rows)
    if workers == 1:
        cases = tuple(_audit_case_args(arg) for arg in args)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            cases = tuple(executor.map(_audit_case_args, args))
    cases = tuple(sorted(cases, key=lambda row: str(row["case_id"])))

    union_edges = sorted(
        {tuple(edge) for case in cases for edge in case["edges"]}
    )
    edge_nodes = {node for edge in union_edges for node in edge}
    failures = []
    for case in cases:
        if case["missing_trace_columns"]:
            failures.append("{}:missing_trace_columns".format(case["case_id"]))
        if case["missing_metric_columns"]:
            failures.append("{}:missing_metric_columns".format(case["case_id"]))
        if case["unfillable_metric_samples"]:
            failures.append("{}:unfillable_metric_samples".format(case["case_id"]))
        if case["ambiguous_span_key_count"]:
            failures.append("{}:ambiguous_span_keys".format(case["case_id"]))

    return {
        "schema_version": "dejavu_re2_source_audit_v1",
        "status": "PASS" if not failures else "FAIL",
        "dataset": dataset,
        "case_count": len(cases),
        "candidate_count": len(candidates),
        "candidates": list(candidates),
        "source_registry": _file_record(sources_path),
        "candidate_registry": _file_record(candidate_registry_path),
        "trace_file_count": len(cases),
        "metric_file_count": len(cases),
        "union_edges": [list(edge) for edge in union_edges],
        "candidates_ever_in_an_edge": sorted(edge_nodes),
        "candidates_never_in_an_edge": sorted(set(candidates) - edge_nodes),
        "unmapped_trace_services": sorted(
            {service for case in cases for service in case["unmapped_trace_services"]}
        ),
        "total_missing_parent_span_joins": sum(
            int(case["missing_parent_span_join_count"]) for case in cases
        ),
        "failures": failures,
        "cases": list(cases),
    }


def prepare_metric_tensor(
    source_row: Mapping[str, object], candidates: Sequence[str]
) -> np.ndarray:
    """Build one label-free candidate x CPU/MEM x time DejaVu tensor."""

    canonical = tuple(str(value) for value in candidates)
    if len(canonical) < 2 or len(set(canonical)) != len(canonical):
        raise ValueError("candidate registry must be unique")
    metric_path = Path(str(source_row["simple_metrics_path"]))
    inject_path = Path(str(source_row["inject_time_path"]))
    injection_time = float(inject_path.read_text(encoding="utf-8").strip())
    required_times = tuple(injection_time + offset for offset in METRIC_OFFSETS_SECONDS)
    required_set = set(required_times)
    rows_by_time = {}
    with metric_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = set(reader.fieldnames or ())
        required_columns = {
            "{}_{}".format(candidate, suffix)
            for candidate in canonical
            for suffix in METRIC_SUFFIXES
        }
        if "time" not in header or not required_columns <= header:
            raise ValueError("simple metric schema does not cover candidates")
        for row in reader:
            try:
                timestamp = float(row["time"])
            except (TypeError, ValueError):
                continue
            if timestamp not in required_set:
                continue
            if timestamp in rows_by_time:
                raise ValueError("duplicate required metric timestamp")
            rows_by_time[timestamp] = row

    tensor = np.empty(
        (len(canonical), len(METRIC_SUFFIXES), len(required_times)),
        dtype=np.float64,
    )
    for candidate_index, candidate in enumerate(canonical):
        for metric_index, suffix in enumerate(METRIC_SUFFIXES):
            column = "{}_{}".format(candidate, suffix)
            previous = None
            for time_index, timestamp in enumerate(required_times):
                raw = rows_by_time.get(timestamp, {}).get(column, "")
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    value = float("nan")
                if not math.isfinite(value):
                    if previous is None:
                        raise ValueError("required metric has an unfillable leading gap")
                    value = previous
                tensor[candidate_index, metric_index, time_index] = value
                previous = value

    tensor = np.clip(tensor, -10.0, 10.0)
    tensor -= np.mean(tensor[:, :, :10], axis=-1, keepdims=True)
    if not np.all(np.isfinite(tensor)):
        raise ValueError("prepared metric tensor must be finite")
    return tensor.astype(np.float32)


def build_graph_spec(
    candidates: Sequence[str], edges: Sequence[Sequence[str]]
) -> Mapping[str, object]:
    """Map provenance-bound service edges to canonical candidate indices."""

    canonical = tuple(str(value) for value in candidates)
    if len(canonical) < 2 or len(set(canonical)) != len(canonical):
        raise ValueError("candidate registry must be unique")
    index = {candidate: position for position, candidate in enumerate(canonical)}
    normalized = set()
    for raw_edge in edges:
        if len(raw_edge) != 2:
            raise ValueError("each source edge must have two endpoints")
        source, destination = map(str, raw_edge)
        if source not in index or destination not in index:
            raise ValueError("source edge endpoint is outside the candidate registry")
        if source == destination:
            raise ValueError("source FDG must not contain self loops")
        normalized.add((source, destination))
    ordered = sorted(normalized)
    return {
        "node_count": len(canonical),
        "source_indices": [index[source] for source, _ in ordered],
        "destination_indices": [index[destination] for _, destination in ordered],
    }


def dejavu_fold_partitions(project_root: Path, dataset: str, fold: int):
    """Return fixed model-train, inner-validation, and outer-test case IDs."""

    if dataset not in ("re2ob", "re2tt") or fold not in (0, 1, 2):
        raise ValueError("invalid dataset or fold")
    project_root = Path(project_root)
    source_path = project_root / "artifacts" / "source" / dataset / "sources.jsonl"
    assignment_path = project_root / "artifacts" / "splits" / dataset / "assignments.json"
    sources = {
        str(row["case_id"]): int(row["replicate"])
        for row in (
            json.loads(line)
            for line in source_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    assignments_doc = json.loads(assignment_path.read_text(encoding="utf-8"))
    assignments = {str(row["case_id"]): int(row["fold"]) for row in assignments_doc}
    if len(sources) != 90 or set(sources) != set(assignments):
        raise ValueError("source and split case universes differ")
    if any(assignments[case_id] != replicate - 1 for case_id, replicate in sources.items()):
        raise ValueError("existing fold is not the frozen repetition assignment")
    remaining_repetitions = sorted({1, 2, 3} - {fold + 1})
    train_repetition, validation_repetition = remaining_repetitions
    train_ids = tuple(sorted(case_id for case_id, rep in sources.items() if rep == train_repetition))
    validation_ids = tuple(sorted(case_id for case_id, rep in sources.items() if rep == validation_repetition))
    test_ids = tuple(sorted(case_id for case_id, rep in sources.items() if rep == fold + 1))
    if tuple(map(len, (train_ids, validation_ids, test_ids))) != (30, 30, 30):
        raise ValueError("DejaVu inner/outer partitions must each contain 30 events")
    return train_ids, validation_ids, test_ids
