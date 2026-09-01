"""Isolated label-free RCAEval worker for one synthetic or real case."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import argparse
import ast
import hashlib
import importlib
import io
import json
from pathlib import Path
import random
import sys
import time
import types
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from src.baseline_eval import (
    AdapterError,
    CANONICAL_SEED,
    MethodOutputError,
    TerminalStatus,
    adapt_native_ranking,
    assert_firewall_safe_record,
    frozen_microcause_sli,
    mmbaro_dataset_key,
    seed_in_process,
    trace_anchor_microseconds,
    validate_mmbaro_payload,
    validate_native_output,
)
from src.baseline_eval.confirmatory import (
    CASE_TIMEOUT_SECONDS,
    DATASET_ORDER,
    INPUT_MANIFEST_RELATIVE,
    INPUT_ROLES,
    METHOD_ORDER,
    PROTOCOL_DIGEST,
    PROTOCOL_VERSION,
    RCAEVAL_CLEAN,
    RCAEVAL_COMMIT,
    REQUIRED_STARTING_HEAD,
    atomic_write_json,
    canonical_payload_digest,
    read_json,
    read_jsonl,
    sha256_file,
    utc_now,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

METHOD_MODULES = {
    "BARO": ("RCAEval.e2e.baro", "baro"),
    "CIRCA": ("RCAEval.e2e.circa", "circa"),
    "MicroCause": ("RCAEval.e2e.microcause", "microcause"),
    "MicroRank": ("RCAEval.e2e.microrank", "microrank"),
    "TraceRCA": ("RCAEval.e2e.tracerca", "tracerca"),
    "mmBARO": ("RCAEval.e2e.baro", "mmbaro"),
    "CausalRCA": ("RCAEval.e2e.causalrca", "causalrca"),
}

METHOD_INPUT_ROLES = {
    "BARO": ("inject_time", "simple_metrics"),
    "CIRCA": ("inject_time", "simple_metrics"),
    "MicroCause": ("inject_time", "simple_metrics"),
    "MicroRank": ("inject_time", "traces"),
    "TraceRCA": ("inject_time", "traces"),
    "mmBARO": (
        "inject_time",
        "simple_metrics",
        "logs",
        "traces",
        "logts",
        "tracets_err",
        "tracets_lat",
    ),
    "CausalRCA": ("inject_time", "simple_metrics"),
}

NATIVE_OUTPUT_TYPES = {
    "BARO": "INDICATOR_RANKING",
    "CIRCA": "GRAPH_AND_PARTIAL_INDICATOR_RANKING",
    "MicroCause": "GRAPH_AND_RETAINED_INDICATOR_RANKING",
    "MicroRank": "OPERATION_RANKING_CAPPED_AT_11",
    "TraceRCA": "PARTIAL_OPERATION_RANKING",
    "mmBARO": "CROSS_MODALITY_INDICATOR_RANKING",
    "CausalRCA": "GRAPH_AND_RETAINED_INDICATOR_RANKING",
}

MICROCAUSE_SYNTHETIC_RANDOM_WALK_EPOCHS = 10
MICROCAUSE_SYNTHETIC_RANDOM_WALK_STEPS = 100


class DataInputError(ValueError):
    """A frozen case source is absent or does not match its manifest."""


class DigestSink(io.TextIOBase):
    """Capture only a digest/count, never native console contents."""

    def __init__(self) -> None:
        self._digest = hashlib.sha256()
        self.character_count = 0

    def write(self, value: str) -> int:
        encoded = value.encode("utf-8", errors="replace")
        self._digest.update(encoded)
        self.character_count += len(value)
        return len(value)

    def flush(self) -> None:
        return None

    @property
    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def _read_csv_source(path: Path, role: str) -> pd.DataFrame:
    try:
        # Pandas 2.3.3's native C parser deterministically segfaults on the
        # frozen trace source for re2ob-f30e2feeaa5218b8.  The CSV is
        # structurally valid and the Python parser preserves the same rows and
        # columns without crossing into native parser code.  Scope the safer
        # engine to raw traces; all other frozen sources retain their audited
        # parser behavior.
        if role == "traces":
            return pd.read_csv(path, engine="python")
        return pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise DataInputError(f"frozen {role} source is unreadable") from exc


def _require_numeric(
    data: pd.DataFrame, columns: Sequence[str], context: str, *, require_finite: bool = True
) -> None:
    for column in columns:
        if not pd.api.types.is_numeric_dtype(data[column]):
            raise DataInputError(f"{context} column is not numeric: {column}")
        values = data[column].to_numpy()
        if require_finite and not bool(np.isfinite(values).all()):
            raise DataInputError(f"{context} column is not finite: {column}")


def _module_callable(method: str):
    # Importing ``RCAEval.e2e`` normally eagerly imports every RCA method.  A
    # fresh per-case worker would otherwise pay that unrelated import cost and
    # could fail because of an excluded method's optional dependency.  Build a
    # namespace package and execute the exact pinned ``rca`` decorator AST; the
    # selected native method module itself is then imported unchanged.
    if "RCAEval.e2e" not in sys.modules:
        import RCAEval

        package_path = RCAEVAL_CLEAN / "RCAEval" / "e2e"
        init_path = package_path / "__init__.py"
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
        decorator = next(
            node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "rca"
        )
        package = types.ModuleType("RCAEval.e2e")
        package.__file__ = str(init_path)
        package.__package__ = "RCAEval.e2e"
        package.__path__ = [str(package_path)]
        exec(compile(ast.Module(body=[decorator], type_ignores=[]), str(init_path), "exec"), package.__dict__)
        sys.modules["RCAEval.e2e"] = package
        setattr(RCAEval, "e2e", package)
    module_name, attribute = METHOD_MODULES[method]
    module = importlib.import_module(module_name)
    module_path = Path(module.__file__).resolve()
    clean_root = RCAEVAL_CLEAN.resolve()
    if clean_root not in module_path.parents:
        raise RuntimeError("RCAEval import did not resolve to the frozen clean checkout")
    return getattr(module, attribute), module_path


@contextmanager
def synthetic_preflight_native_limits(method: str):
    """Bound diagnostic-only work without changing any real case invocation."""

    if method != "MicroCause":
        yield
        return
    module = importlib.import_module(METHOD_MODULES[method][0])
    native_randomwalk = module.randomwalk

    def bounded_randomwalk(
        matrix,
        epochs,
        start_node,
        teleportation_prob,
        walk_step=50,
        print_trace=False,
    ):
        return native_randomwalk(
            matrix,
            min(epochs, MICROCAUSE_SYNTHETIC_RANDOM_WALK_EPOCHS),
            start_node,
            teleportation_prob,
            min(walk_step, MICROCAUSE_SYNTHETIC_RANDOM_WALK_STEPS),
            print_trace,
        )

    module.randomwalk = bounded_randomwalk
    try:
        yield
    finally:
        module.randomwalk = native_randomwalk


def _common_metric_adapter(raw: pd.DataFrame, dataset: str, anchor: int) -> pd.DataFrame:
    if "time" not in raw:
        raise DataInputError("simple metric input has no time column")
    _require_numeric(raw, ("time",), "simple metric time")
    data = raw.loc[:, ~raw.columns.str.endswith("_latency-50")].copy()
    if dataset == "re2tt":
        time_column = data["time"].copy()
        data = data.loc[:, data.columns.str.startswith("ts-")].copy()
        data["time"] = time_column
    data = data.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    data = data[(data["time"] >= anchor - 600) & (data["time"] < anchor + 600)].copy()
    data = data.rename(
        columns={
            column: column.replace("_latency-90", "_latency")
            for column in data.columns
            if column.endswith("_latency-90")
        }
    )
    if data.empty:
        raise DataInputError("simple metric canonical window is empty")
    _require_numeric(data, tuple(data.columns), "simple metric")
    return data.reset_index(drop=True)


def _derived_adapter(raw: pd.DataFrame, anchor: int) -> pd.DataFrame:
    if "time" not in raw:
        raise DataInputError("derived telemetry has no time column")
    _require_numeric(raw, ("time",), "derived telemetry time")
    _require_numeric(
        raw,
        tuple(column for column in raw.columns if column != "time"),
        "derived telemetry",
        require_finite=False,
    )
    data = raw[(raw["time"] >= anchor - 600) & (raw["time"] < anchor + 600)].copy()
    if data.empty:
        raise DataInputError("derived telemetry canonical window is empty")
    return data.reset_index(drop=True)


def _trace_adapter(raw: pd.DataFrame, anchor: int) -> pd.DataFrame:
    required = {
        "serviceName",
        "methodName",
        "operationName",
        "traceID",
        "spanID",
        "parentSpanID",
        "startTime",
        "startTimeMillis",
        "duration",
    }
    if not required.issubset(raw.columns):
        raise DataInputError("raw trace schema is incomplete")
    _require_numeric(raw, ("startTime", "startTimeMillis", "duration"), "raw trace")
    if bool((raw["duration"] < 0).any()):
        raise DataInputError("raw trace duration cannot be negative")
    for column in ("serviceName", "operationName", "traceID", "spanID"):
        if raw[column].isna().any() or not raw[column].map(lambda value: isinstance(value, str)).all():
            raise DataInputError(f"raw trace identity column is invalid: {column}")
    non_null_parent_ids = raw["parentSpanID"].dropna()
    if not non_null_parent_ids.map(lambda value: isinstance(value, str)).all():
        raise DataInputError("raw trace identity column is invalid: parentSpanID")
    sampled = raw.iloc[:: max(len(raw) // 1000, 1)]
    if not bool(((sampled["startTime"] // 1000) == sampled["startTimeMillis"]).all()):
        raise DataInputError("raw trace timestamp units are inconsistent")
    anchor_us = anchor * 1_000_000
    span_end = raw["startTime"] + raw["duration"]
    data = raw[(span_end >= anchor_us - 600_000_000) & (span_end < anchor_us + 600_000_000)].copy()
    if data.empty:
        raise DataInputError("raw trace canonical window is empty")
    return data.reset_index(drop=True)


def _case_rows(dataset: str, case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = PROJECT_ROOT / "artifacts" / "source" / dataset
    inputs = {row["case_id"]: row for row in read_jsonl(bundle / "inputs.jsonl")}
    sources = {row["case_id"]: row for row in read_jsonl(bundle / "sources.jsonl")}
    if case_id not in inputs or case_id not in sources:
        raise DataInputError("opaque case ID is not in the frozen source index")
    return inputs[case_id], sources[case_id]


def _manifest_case(dataset: str, case_id: str) -> dict[str, Any]:
    manifest = read_json(PROJECT_ROOT / INPUT_MANIFEST_RELATIVE)
    for row in manifest["cases"]:
        if row["dataset"] == dataset and row["case_id"] == case_id:
            return row
    raise DataInputError("opaque case ID is absent from the frozen input manifest")


def _verified_paths(
    method: str, dataset: str, case_id: str
) -> tuple[dict[str, Any], dict[str, Path], list[dict[str, Any]]]:
    case, source = _case_rows(dataset, case_id)
    manifest_case = _manifest_case(dataset, case_id)
    manifest_sources = {row["logical_source_role"]: row for row in manifest_case["sources"]}
    paths: dict[str, Path] = {}
    provenance: list[dict[str, Any]] = []
    for role in METHOD_INPUT_ROLES[method]:
        source_key = INPUT_ROLES[role]
        path = Path(source[source_key])
        expected = manifest_sources.get(role)
        if expected is None or not path.is_file():
            raise DataInputError(f"frozen source is unavailable for role {role}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != expected["byte_size"] or digest != expected["sha256"]:
            raise DataInputError(f"frozen source digest mismatch for role {role}")
        paths[role] = path
        provenance.append({"logical_source_role": role, "byte_size": size, "sha256": digest})
    return case, paths, provenance


def _observed_metric_services(data: pd.DataFrame, candidates: Sequence[str]) -> set[str]:
    observed: set[str] = set()
    for column in data.columns:
        for candidate in candidates:
            if column == candidate or column.startswith(candidate + "_"):
                observed.add(candidate)
    return observed


def _observed_trace_services(data: pd.DataFrame, candidates: Sequence[str]) -> set[str]:
    names = {"frontend" if value == "frontendservice" else str(value) for value in data["serviceName"].dropna()}
    return set(candidates).intersection(names)


def load_legal_case_input(
    method: str, dataset: str, case_id: str
) -> tuple[Any, int, tuple[str, ...], str | None, set[str], list[dict[str, Any]]]:
    """Trusted path resolution; returned predictive inputs contain no path/root fields."""

    case, paths, provenance = _verified_paths(method, dataset, case_id)
    anchor = int(case["anchor_time"])
    if int(paths["inject_time"].read_text(encoding="utf-8").strip()) != anchor:
        raise DataInputError("inject-time contents differ from the canonical anchor")
    candidates = tuple(case["candidates"])
    sli = None
    observed: set[str]
    if method in {"BARO", "CIRCA", "MicroCause", "CausalRCA"}:
        metric = _common_metric_adapter(
            _read_csv_source(paths["simple_metrics"], "simple_metrics"), dataset, anchor
        )
        observed = _observed_metric_services(metric, candidates)
        if method == "MicroCause":
            sli = frozen_microcause_sli(dataset, tuple(metric.columns))
        return metric, anchor, candidates, sli, observed, provenance
    if method in {"MicroRank", "TraceRCA"}:
        traces = _trace_adapter(_read_csv_source(paths["traces"], "traces"), anchor)
        observed = _observed_trace_services(traces, candidates)
        return traces, anchor, candidates, sli, observed, provenance
    if method == "mmBARO":
        metric = _common_metric_adapter(
            _read_csv_source(paths["simple_metrics"], "simple_metrics"), dataset, anchor
        )
        traces = _trace_adapter(_read_csv_source(paths["traces"], "traces"), anchor)
        payload = {
            "metric": metric,
            "logs": _read_csv_source(paths["logs"], "logs"),
            "logts": _derived_adapter(_read_csv_source(paths["logts"], "logts"), anchor),
            "traces": traces,
            "tracets_err": _derived_adapter(
                _read_csv_source(paths["tracets_err"], "tracets_err"), anchor
            ),
            "tracets_lat": _derived_adapter(
                _read_csv_source(paths["tracets_lat"], "tracets_lat"), anchor
            ),
            "cluster_info": None,
        }
        validate_mmbaro_payload(payload)
        observed = _observed_metric_services(metric, candidates)
        observed.update(_observed_trace_services(traces, candidates))
        for key in ("logts", "tracets_err", "tracets_lat"):
            observed.update(_observed_metric_services(payload[key], candidates))
        return payload, anchor, candidates, sli, observed, provenance
    raise DataInputError("method is not authorized")


def invoke_predictive_method(
    method: str,
    dataset: str,
    case_id: str,
    anchor: int,
    telemetry: Any,
    candidates: Sequence[str],
    sli: str | None,
    *,
    synthetic: bool = False,
) -> tuple[Mapping[str, Any], tuple[str, ...], Path, DigestSink]:
    """Call only with frozen legal predictive fields; no path/root/fault input."""

    del case_id, candidates  # legal identity/registry fields are not needed by native callables
    native_dataset = {"re2ob": "re2-ob", "re2tt": "re2-tt"}[dataset]
    if method == "mmBARO":
        native_dataset = mmbaro_dataset_key(dataset)
    seed_in_process(CANONICAL_SEED, include_torch=method == "CausalRCA")
    if method == "CausalRCA":
        import torch

        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        if torch.cuda.is_available():
            raise RuntimeError("CausalRCA confirmatory worker must be CPU-only")
    function, module_path = _module_callable(method)
    sink = DigestSink()
    kwargs = {
        "inject_time": (
            trace_anchor_microseconds(anchor)
            if method in {"MicroRank", "TraceRCA"}
            else anchor
        ),
        "dataset": native_dataset,
        "dk_select_useful": False,
        "sli": sli,
        "verbose": False,
    }
    with synthetic_preflight_native_limits(method) if synthetic else nullcontext():
        with redirect_stdout(sink), redirect_stderr(sink):
            output = function(telemetry, **kwargs)
    input_columns: tuple[str, ...] = ()
    if isinstance(telemetry, pd.DataFrame):
        input_columns = tuple(column for column in telemetry.columns if column != "time")
        if method in {"CIRCA", "CausalRCA"}:
            preprocess = importlib.import_module("RCAEval.io.time_series").preprocess
            input_columns = tuple(
                preprocess(telemetry.copy(), dataset=native_dataset, dk_select_useful=False).columns
            )
    ranks = validate_native_output(method, output, input_columns)
    return output, ranks, module_path, sink


def _missing_reasons(
    method: str, candidates: Sequence[str], adapted: Sequence[str], observed: set[str],
    native_length: int,
) -> dict[str, str]:
    default = (
        "NATIVE_TOP_K_TRUNCATION"
        if method == "MicroRank" and native_length == 11
        else "ALGORITHM_FILTERED_INDICATOR"
    )
    return {
        candidate: ("NO_OBSERVED_TELEMETRY" if candidate not in observed else default)
        for candidate in candidates
        if candidate not in adapted
    }


def _generic_error(status: TerminalStatus, exc: BaseException) -> str:
    if status is TerminalStatus.DATA_FAILURE:
        return "frozen case input failed identity, digest, or schema validation"
    if status is TerminalStatus.ADAPTER_FAILURE:
        return "native output could not be legally projected or persisted"
    return f"native method failed with {type(exc).__name__}"


def execute_case(args: argparse.Namespace) -> dict[str, Any]:
    start_timestamp = utc_now()
    start = time.monotonic()
    native_type = NATIVE_OUTPUT_TYPES[args.method]
    native_length = 0
    native_digest: str | None = None
    duplicate_items: list[str] = []
    unmapped_items: list[str] = []
    source_provenance: list[dict[str, Any]] = []
    candidates: tuple[str, ...] = ()
    captured = DigestSink()
    terminal_status = TerminalStatus.SUCCESS
    error_type: str | None = None
    sanitized_error: str | None = None
    diagnostic_digest: str | None = None
    native_ranking: list[str] = []
    adapted_ranking: list[str] = []
    missing: dict[str, str] = {}
    module_source_digest: str | None = None
    try:
        telemetry, anchor, candidates, sli, observed, source_provenance = load_legal_case_input(
            args.method, args.dataset, args.case_id
        )
        output, ranks, module_path, captured = invoke_predictive_method(
            args.method, args.dataset, args.case_id, anchor, telemetry, candidates, sli
        )
        del output
        native_length = len(ranks)
        native_digest = canonical_payload_digest(list(ranks))
        module_source_digest = sha256_file(module_path)
        try:
            adapted = adapt_native_ranking(ranks, candidates)
        except AdapterError as exc:
            terminal_status = TerminalStatus.ADAPTER_FAILURE
            unmapped_items = list(ranks)
            missing = {candidate: "ADAPTER_MISMATCH" for candidate in candidates}
            error_type = type(exc).__name__
            sanitized_error = _generic_error(terminal_status, exc)
            diagnostic_digest = canonical_payload_digest(
                {"exception_type": type(exc).__name__, "native_output_digest": native_digest}
            )
        else:
            native_ranking = list(ranks)
            adapted_ranking = list(adapted.services)
            duplicate_items = list(adapted.duplicates)
            unmapped_items = list(adapted.unmapped)
            missing = _missing_reasons(
                args.method, candidates, adapted.services, observed, native_length
            )
    except DataInputError as exc:
        terminal_status = TerminalStatus.DATA_FAILURE
        error_type = type(exc).__name__
        sanitized_error = _generic_error(terminal_status, exc)
        diagnostic_digest = canonical_payload_digest({"exception_type": type(exc).__name__, "detail": str(exc)})
        missing = {candidate: "EXECUTION_FAILURE" for candidate in candidates}
    except (MethodOutputError, Exception) as exc:  # native exceptions are terminal METHOD_FAILURE
        terminal_status = TerminalStatus.METHOD_FAILURE
        error_type = type(exc).__name__
        sanitized_error = _generic_error(terminal_status, exc)
        diagnostic_digest = canonical_payload_digest(
            {
                "exception_type": type(exc).__name__,
                "detail": str(exc),
                "captured_output_digest": captured.hexdigest,
            }
        )
        missing = {candidate: "EXECUTION_FAILURE" for candidate in candidates}
    if terminal_status is not TerminalStatus.SUCCESS:
        native_ranking = []
        adapted_ranking = []
    payload = {
        "schema_version": "rca_baseline_case_record_v1",
        "protocol_version": PROTOCOL_VERSION,
        "protocol_digest": PROTOCOL_DIGEST,
        "method": args.method,
        "dataset": args.dataset,
        "case_id": args.case_id,
        "attempt_id": args.attempt_id,
        "ada_rca_commit": REQUIRED_STARTING_HEAD,
        "execution_commit": args.execution_commit,
        "execution_worker_count": getattr(args, "execution_worker_count", 1),
        "execution_worker_slot": getattr(args, "execution_worker_slot", 0),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "environment_digest": args.environment_digest,
        "input_manifest_digest": args.input_manifest_digest,
        "candidate_registry_digest": args.candidate_registry_digest,
        "source_record_digests": source_provenance,
        "method_source_digest": module_source_digest,
        "seed_state": {
            "canonical_seed": CANONICAL_SEED,
            "python_hash_seed": CANONICAL_SEED,
            "numpy_seed": CANONICAL_SEED,
            "torch_seed": CANONICAL_SEED if args.method == "CausalRCA" else None,
        },
        "timeout_seconds": CASE_TIMEOUT_SECONDS,
        "start_timestamp": start_timestamp,
        "end_timestamp": utc_now(),
        "wall_time_seconds": time.monotonic() - start,
        "window_semantics": "[t0-600s,t0+600s)",
        "native_output_type": native_type if terminal_status is not TerminalStatus.DATA_FAILURE else "NONE",
        "native_output_length": native_length,
        "adapted_output_length": len(adapted_ranking),
        "native_ranking": native_ranking,
        "adapted_ranking": adapted_ranking,
        "native_output_digest": native_digest,
        "duplicate_native_items": duplicate_items,
        "duplicate_count": len(duplicate_items),
        "unmapped_native_items": unmapped_items,
        "unmapped_count": len(unmapped_items),
        "missing_candidate_reasons": missing,
        "terminal_status": terminal_status.value,
        "error_type": error_type,
        "sanitized_error": sanitized_error,
        "diagnostic_digest": diagnostic_digest,
        "native_console_digest": captured.hexdigest,
        "native_console_character_count": captured.character_count,
    }
    assert_firewall_safe_record(payload)
    return payload


def _synthetic_metric(dataset: str) -> tuple[pd.DataFrame, int, tuple[str, ...], str]:
    rng = np.random.default_rng(CANONICAL_SEED)
    anchor = 1_700_000_600
    time_values = np.arange(anchor - 600, anchor + 600)
    x = rng.normal(size=len(time_values))
    y = 0.95 * x + rng.normal(scale=0.05, size=len(time_values))
    z = 0.85 * y + rng.normal(scale=0.08, size=len(time_values))
    shift = (time_values >= anchor).astype(float) * 4.0
    if dataset == "re2ob":
        candidates = ("frontend", "checkoutservice", "paymentservice")
        raw = pd.DataFrame({
            "time": time_values,
            "frontend_latency-90": x + shift,
            "checkoutservice_cpu": y + shift * 0.8,
            "paymentservice_mem": z + shift * 0.5,
            "frontend_latency-50": x,
        })
        sli = "frontend_latency"
    else:
        candidates = ("ts-ui-dashboard", "ts-order", "ts-payment-service")
        raw = pd.DataFrame({
            "time": time_values,
            "ts-ui-dashboard_latency-90": x + shift,
            "ts-order_cpu": y + shift * 0.8,
            "ts-payment-service_mem": z + shift * 0.5,
            "ignored_cpu": x,
        })
        sli = "ts-ui-dashboard_latency"
    return _common_metric_adapter(raw, dataset, anchor), anchor, candidates, sli


def _synthetic_traces(dataset: str) -> tuple[pd.DataFrame, int, tuple[str, ...]]:
    anchor = 1_700_000_600
    anchor_us = anchor * 1_000_000
    if dataset == "re2ob":
        candidates = ("frontend", "checkoutservice")
        services = ("frontendservice", "checkoutservice")
    else:
        candidates = ("ts-ui-dashboard", "ts-order")
        services = candidates
    rows: list[dict[str, Any]] = []
    for index in range(80):
        before = index < 40
        start = anchor_us + (-500 + index * 12) * 1_000_000
        if not before:
            start = anchor_us + (index - 40 + 1) * 10_000_000
        trace_id = f"trace-{index}"
        parent = f"span-{index}-0"
        for position, (service, operation) in enumerate(zip(services, ("GET", "CALL"))):
            duration = 1_000 + position * 300
            if not before and position == 1 and index % 2 == 0:
                duration = 20_000
            span_id = f"span-{index}-{position}"
            rows.append({
                "time": anchor,
                "traceID": trace_id,
                "spanID": span_id,
                "serviceName": service,
                "methodName": operation,
                "operationName": operation,
                "startTimeMillis": start // 1000,
                "startTime": start,
                "duration": duration,
                "statusCode": 0,
                "parentSpanID": "root" if position == 0 else parent,
            })
    return _trace_adapter(pd.DataFrame(rows), anchor), anchor, candidates


def _synthetic_mmbaro(dataset: str) -> tuple[dict[str, Any], int, tuple[str, ...]]:
    metric, anchor, candidates, _ = _synthetic_metric(dataset)
    trace, _, _ = _synthetic_traces(dataset)
    derived_time = np.arange(anchor - 600, anchor + 600, 15)
    prefix = candidates[0]
    derived = pd.DataFrame({"time": derived_time, f"{prefix}_count": np.sin(np.arange(len(derived_time)))})
    payload = {
        "metric": metric,
        "logs": pd.DataFrame({"time": derived_time, "message": ["synthetic"] * len(derived_time)}),
        "logts": derived.copy(),
        "traces": trace,
        "tracets_err": derived.copy(),
        "tracets_lat": derived.copy(),
        "cluster_info": None,
    }
    return payload, anchor, candidates


def synthetic_preflight(method: str) -> dict[str, Any]:
    fingerprints: list[dict[str, Any]] = []
    module_paths: list[str] = []
    for dataset in DATASET_ORDER:
        if method in {"MicroRank", "TraceRCA"}:
            telemetry, anchor, candidates = _synthetic_traces(dataset)
            sli = None
        elif method == "mmBARO":
            telemetry, anchor, candidates = _synthetic_mmbaro(dataset)
            sli = None
        else:
            telemetry, anchor, candidates, sli = _synthetic_metric(dataset)
        output, ranks, module_path, _sink = invoke_predictive_method(
            method,
            dataset,
            f"synthetic-{dataset}",
            anchor,
            telemetry,
            candidates,
            sli,
            synthetic=True,
        )
        del output
        adapted = adapt_native_ranking(ranks, candidates)
        if not adapted.services:
            raise RuntimeError("synthetic projection is empty")
        fingerprints.append({
            "dataset": dataset,
            "native_length": len(ranks),
            "adapted_length": len(adapted.services),
            "native_digest": canonical_payload_digest(list(ranks)),
            "adapted_digest": canonical_payload_digest(list(adapted.services)),
        })
        module_paths.append(str(module_path))
    return {
        "status": "PASS",
        "method": method,
        "native_output_kind": NATIVE_OUTPUT_TYPES[method],
        "fingerprint": canonical_payload_digest(fingerprints),
        "module_paths_within_clean_checkout": all(
            RCAEVAL_CLEAN.resolve() in Path(path).resolve().parents for path in module_paths
        ),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--method", choices=METHOD_ORDER, required=True)
    case = sub.add_parser("case")
    case.add_argument("--method", choices=METHOD_ORDER, required=True)
    case.add_argument("--dataset", choices=DATASET_ORDER, required=True)
    case.add_argument("--case-id", required=True)
    case.add_argument("--attempt-id", required=True)
    case.add_argument("--environment-digest", required=True)
    case.add_argument("--input-manifest-digest", required=True)
    case.add_argument("--candidate-registry-digest", required=True)
    case.add_argument("--execution-commit", required=True)
    case.add_argument("--execution-worker-count", type=int, default=1)
    case.add_argument("--execution-worker-slot", type=int, default=0)
    case.add_argument("--output", type=Path, required=True)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    random.seed(CANONICAL_SEED)
    np.random.seed(CANONICAL_SEED)
    if args.command == "preflight":
        sink = DigestSink()
        with redirect_stdout(sink), redirect_stderr(sink):
            result = synthetic_preflight(args.method)
        print(json.dumps(result, sort_keys=True))
        return 0
    expected_input_digest = sha256_file(PROJECT_ROOT / INPUT_MANIFEST_RELATIVE)
    if args.input_manifest_digest != expected_input_digest:
        raise DataInputError("worker input-manifest digest does not match frozen bytes")
    payload = execute_case(args)
    if args.output.exists():
        raise RuntimeError("worker refuses to overwrite a terminal record")
    atomic_write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
