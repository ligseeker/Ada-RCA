"""RCAEval Five-Baseline Completion Rescue & Unified Evaluation V2.

This module is the V2 execution coordinator.  It deliberately lives beside,
not inside, the frozen V1 runner: old A1/A2 records and locks remain
read-only, while every V2 attempt has its own method-scoped paths and lock
schema.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import select
import subprocess
import tempfile
import threading
import time
from typing import Any, Iterator, Mapping, Sequence

from src.baseline_eval import (
    CANONICAL_SEED,
    EXPECTED_CASES_PER_DATASET,
    assert_ada_rca_frozen_unchanged,
    assert_firewall_safe_record,
    frozen_microcause_sli,
)
from src.baseline_eval.confirmatory import (
    DATASET_DISPLAY,
    DATASET_ORDER,
    FIXED_WORKER_ENV,
    INPUT_MANIFEST_RELATIVE,
    INPUT_ROLES,
    RCAEVAL_CLEAN,
    RCAEVAL_COMMIT,
    RCAEVAL_SOURCE_DIGESTS,
    REQUIRED_STARTING_HEAD,
    PreflightError,
    SequenceError,
    atomic_write_json,
    canonical_payload_digest,
    collect_environment_identity,
    expected_case_ids,
    exclusive_method_execution_lock,
    fixed_worker_environment,
    git,
    git_common_execution_lock_root,
    read_json,
    read_jsonl,
    resolve_frozen_worker_environment,
    schema_preflight,
    sha256_file,
    utc_now,
    verify_rcaeval_clean,
    global_preflight,
    _environment_preflight_details,
    _candidate_registry_digest,
    require_committed_file,
    require_clean_git,
    require_attempt_id,
)
from src.baseline_eval.worker import (
    METHOD_INPUT_ROLES,
    NATIVE_OUTPUT_TYPES,
    _native_module_path,
    _read_csv_source,
    _trace_adapter,
    _common_metric_adapter,
    _derived_adapter,
    load_legal_case_input,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

V2_PROTOCOL_VERSION = "RCA_BASELINE_RESCUE_PROTOCOL_V2"
V2_PROTOCOL_RELATIVE = Path("artifacts/baseline_eval/rescue_protocol_v2.json")
V2_PROTOCOL_DIGEST = "dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de"
V2_EXECUTION_ROOT_RELATIVE = Path("artifacts/baseline_eval/execution_v2")
V2_GLOBAL_LOCK_RELATIVE = V2_EXECUTION_ROOT_RELATIVE / "prediction_lock_v2.json"
V2_EVALUATION_ROOT_RELATIVE = V2_EXECUTION_ROOT_RELATIVE / "evaluation"
V2_METHODS = ("CIRCA", "MicroCause", "MicroRank", "TraceRCA", "mmBARO")
V2_ATTEMPT_IDS = {
    "CIRCA": "circa-a3-rescue-v2",
    "MicroCause": "microcause-a3-rescue-v2",
    "MicroRank": "microrank-a3-rescue-v2",
    "TraceRCA": "tracerca-a3-rescue-v2",
    "mmBARO": "mmbaro-a3-rescue-v2",
}
V2_ALLOWED_WORKERS = (1, 4, 10, 20)
V2_NO_TIMEOUT_SECONDS = None
V2_CASE_SCHEMA = "rca_baseline_rescue_case_record_v2"
V2_ATTEMPT_SCHEMA = "rca_baseline_rescue_attempt_v2"
V2_ENVIRONMENT_SCHEMA = "rca_baseline_rescue_environment_v2"
V2_RUNTIME_SCHEMA = "rca_baseline_rescue_runtime_v2"
V2_METHOD_LOCK_SCHEMA = "rca_baseline_rescue_method_prediction_lock_v2"
V2_GLOBAL_LOCK_SCHEMA = "rca_baseline_rescue_global_prediction_lock_v2"
V2_STATUS_VALUES = (
    "SUCCESS",
    "METHOD_FAILURE",
    "DATA_FAILURE",
    "ADAPTER_FAILURE",
    "ENVIRONMENT_FAILURE",
    "INPUT_INTEGRITY_FAILURE",
    "PROCESS_CRASH/OOM",
    "TIMEOUT",
)
V2_METHOD_ZERO_STATUS = "METHOD_FAILURE"
V2_BLOCKING_STATUSES = frozenset(
    {
        "DATA_FAILURE",
        "ADAPTER_FAILURE",
        "ENVIRONMENT_FAILURE",
        "INPUT_INTEGRITY_FAILURE",
        "PROCESS_CRASH/OOM",
        "TIMEOUT",
    }
)
V2_SERVICE_REGISTRY_DIGESTS = {
    dataset: None for dataset in DATASET_ORDER
}
V2_TRACE_CLOSURE_ADOPTED = False
V2_EXTENDED_NORMAL_HISTORY_ADOPTED = False
MICROCAUSE_NATIVE_RANDOM_WALK_EPOCHS = 1000
MICROCAUSE_NATIVE_RANDOM_WALK_STEPS = 1000


def microcause_native_execution_parameters() -> dict[str, int]:
    """Expose the pinned real-case contract without editing RCAEval source."""

    return {
        "random_walk_epochs": MICROCAUSE_NATIVE_RANDOM_WALK_EPOCHS,
        "random_walk_steps": MICROCAUSE_NATIVE_RANDOM_WALK_STEPS,
    }


def v2_execution_validity(
    blocking_status_counts: Mapping[str, Mapping[str, int]],
) -> str:
    """Classify a V2 attempt from nonzero blocking statuses.

    The dataset keys themselves are always present, so checking the outer
    mapping's truthiness would incorrectly invalidate every complete attempt.
    """

    has_blocking_status = any(
        count
        for dataset_counts in blocking_status_counts.values()
        for count in dataset_counts.values()
    )
    return "INTEGRITY_INVALID" if has_blocking_status else "INTEGRITY_VALID"


def _v2_blocking_status_counts(
    status_counts: Mapping[str, Mapping[str, int]],
) -> dict[str, dict[str, int]]:
    return {
        dataset: {
            status: count
            for status, count in dataset_counts.items()
            if status in V2_BLOCKING_STATUSES and count
        }
        for dataset, dataset_counts in status_counts.items()
    }


class RescueV2Error(RuntimeError):
    """A V2 protocol, scheduler, or evidence-integrity transition failed."""


class V2EvaluationBlocked(RescueV2Error):
    """A method-by-dataset result cannot be joined to labels yet."""


def _require_v2_method(method: str) -> None:
    if method not in V2_METHODS:
        raise SequenceError(f"method is outside the V2 rescue scope: {method}")


def _require_v2_attempt(method: str, attempt_id: str) -> None:
    if attempt_id != V2_ATTEMPT_IDS[method]:
        raise SequenceError(
            f"V2 {method} execution must use the frozen attempt ID "
            f"{V2_ATTEMPT_IDS[method]}"
        )


def _require_dataset_scope(datasets: Sequence[str]) -> tuple[str, ...]:
    observed = tuple(datasets)
    if observed != DATASET_ORDER:
        raise SequenceError("V2 real execution must cover RE2-OB then RE2-TT exactly")
    return observed


def available_cpu_count() -> int:
    """Return CPUs available to this process/container, never host total only."""

    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, int(os.cpu_count() or 1))


def actual_worker_count(requested_workers: int, *, available: int | None = None) -> int:
    if isinstance(requested_workers, bool) or requested_workers not in V2_ALLOWED_WORKERS:
        raise SequenceError(f"V2 workers must be one of {V2_ALLOWED_WORKERS}")
    available_count = available_cpu_count() if available is None else max(1, int(available))
    return min(requested_workers, available_count)


def parse_dataset_scope(value: str) -> tuple[str, ...]:
    return _require_dataset_scope(tuple(part.strip() for part in value.split(",") if part.strip()))


def v2_environment_relative(method: str) -> Path:
    _require_v2_method(method)
    return V2_EXECUTION_ROOT_RELATIVE / "environments" / f"{method.lower()}.json"


def v2_attempt_relative(method: str, attempt_id: str) -> Path:
    _require_v2_method(method)
    require_attempt_id(attempt_id)
    return V2_EXECUTION_ROOT_RELATIVE / "attempts" / method.lower() / f"{attempt_id}.json"


def v2_record_relative(method: str, attempt_id: str, dataset: str, case_id: str) -> Path:
    _require_v2_method(method)
    require_attempt_id(attempt_id)
    if dataset not in DATASET_ORDER:
        raise SequenceError(f"unsupported V2 dataset: {dataset}")
    if not re.fullmatch(r"re2(?:ob|tt)-[0-9a-f]{16}", case_id):
        raise SequenceError("case ID is not a frozen opaque identifier")
    return (
        V2_EXECUTION_ROOT_RELATIVE
        / "records"
        / method.lower()
        / attempt_id
        / dataset
        / f"{case_id}.json"
    )


def v2_runtime_relative(method: str, attempt_id: str) -> Path:
    _require_v2_method(method)
    require_attempt_id(attempt_id)
    return V2_EXECUTION_ROOT_RELATIVE / "runtimes" / method.lower() / f"{attempt_id}.json"


def v2_method_lock_relative(method: str) -> Path:
    _require_v2_method(method)
    return V2_EXECUTION_ROOT_RELATIVE / "locks" / f"{method.lower()}_prediction_lock.json"


def v2_method_lock_reissued_relative(method: str) -> Path:
    """Return the immutable sidecar path used to re-attest a V2 method lock."""

    _require_v2_method(method)
    return V2_EXECUTION_ROOT_RELATIVE / "locks" / f"{method.lower()}_prediction_lock_reissued.json"


def v2_method_lock_reissued_v2_relative(method: str) -> Path:
    """Return the corrected re-attestation path for a V2 method lock."""

    _require_v2_method(method)
    return V2_EXECUTION_ROOT_RELATIVE / "locks" / f"{method.lower()}_prediction_lock_reissued_v2.json"


def active_v2_method_lock_relative(root: Path, method: str) -> Path:
    """Select a reissued lock when one exists, otherwise the original lock."""

    corrected = root / v2_method_lock_reissued_v2_relative(method)
    if corrected.is_file():
        return v2_method_lock_reissued_v2_relative(method)
    reissued = root / v2_method_lock_reissued_relative(method)
    if reissued.is_file():
        return v2_method_lock_reissued_relative(method)
    return v2_method_lock_relative(method)


def _v2_protocol(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    path = root / V2_PROTOCOL_RELATIVE
    if not path.is_file() or sha256_file(path) != V2_PROTOCOL_DIGEST:
        raise PreflightError("V2 rescue protocol digest or file is invalid")
    payload = read_json(path)
    if payload.get("schema_version") != "rca_baseline_rescue_protocol_v2":
        raise PreflightError("V2 rescue protocol schema is invalid")
    if tuple(payload.get("methods", ())) != V2_METHODS:
        raise PreflightError("V2 rescue method registry is invalid")
    execution = payload.get("execution", {})
    if execution.get("no_timeout") is not True or execution.get("timeout_seconds") is not None:
        raise PreflightError("V2 rescue protocol still has a finite timeout")
    return payload


def verify_v2_protocol(root: Path, *, require_committed: bool = True) -> dict[str, Any]:
    path = root / V2_PROTOCOL_RELATIVE
    if require_committed:
        require_committed_file(root, V2_PROTOCOL_RELATIVE)
    observed = sha256_file(path)
    if observed != V2_PROTOCOL_DIGEST:
        raise PreflightError("V2 protocol bytes differ from the frozen rescue amendment")
    return _v2_protocol(root)


def v2_source_manifest_digest(root: Path) -> str:
    observed = sha256_file(root / INPUT_MANIFEST_RELATIVE)
    expected = "b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec"
    if observed != expected:
        raise PreflightError("V2 input manifest digest differs from the frozen manifest")
    return observed


def _v2_source_record_digests(
    root: Path, method: str, dataset: str, case_id: str
) -> list[dict[str, Any]]:
    """Return manifest-bound source identities for one opaque method case."""

    _require_v2_method(method)
    manifest = read_json(root / INPUT_MANIFEST_RELATIVE)
    for case in manifest.get("cases", []):
        if case.get("dataset") != dataset or case.get("case_id") != case_id:
            continue
        by_role = {
            row.get("logical_source_role"): row
            for row in case.get("sources", [])
        }
        try:
            return [
                {
                    "logical_source_role": role,
                    "byte_size": by_role[role]["byte_size"],
                    "sha256": by_role[role]["sha256"],
                }
                for role in METHOD_INPUT_ROLES[method]
            ]
        except (KeyError, TypeError) as exc:
            raise PreflightError(
                f"V2 input manifest lacks a required source role for {method} {case_id}"
            ) from exc
    raise PreflightError(f"V2 input manifest lacks opaque case {dataset}/{case_id}")


def _v2_candidate_digests(root: Path) -> dict[str, str]:
    return {dataset: _candidate_registry_digest(root, dataset) for dataset in DATASET_ORDER}


def _v2_native_module_digest(method: str) -> str:
    path = _native_module_path(method)
    if not path.is_file():
        raise PreflightError(f"pinned native module is unavailable for {method}")
    return sha256_file(path)


def _python_path(value: Path) -> Path:
    value = value.expanduser()
    return Path(os.path.abspath(value))


def freeze_v2_environment(root: Path, method: str, python: Path) -> Path:
    """Freeze one V2 method environment after synthetic-only preflight."""

    _require_v2_method(method)
    require_clean_git(root)
    global_preflight(root)
    verify_v2_protocol(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    v2_source_manifest_digest(root)
    path = root / v2_environment_relative(method)
    if path.exists():
        raise PreflightError(f"V2 environment freeze already exists for {method}")
    python = _python_path(python)
    identity, synthetic, schema = _environment_preflight_details(
        root,
        method,
        python,
        reuse_historical_manifest=False,
        synthetic_timeout_seconds=None,
    )
    stable = {
        "schema_version": V2_ENVIRONMENT_SCHEMA,
        "protocol_version": V2_PROTOCOL_VERSION,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method": method,
        "datasets": list(DATASET_ORDER),
        "identity": identity,
        "input_manifest_digest": v2_source_manifest_digest(root),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "rcaeval_source_digests": RCAEVAL_SOURCE_DIGESTS,
        "candidate_registry_digests": _v2_candidate_digests(root),
        "native_module_digest": _v2_native_module_digest(method),
        "synthetic_preflight": {
            "status": "PASS",
            "fingerprint": synthetic["fingerprint"],
            "native_output_kind": synthetic["native_output_kind"],
            "runs": 2,
        },
        "schema_preflight": schema,
        "deterministic_controls": {
            "canonical_seed": CANONICAL_SEED,
            "python_hash_seed": CANONICAL_SEED,
            "per_case_reseed": True,
            "thread_caps": {
                key: value
                for key, value in FIXED_WORKER_ENV.items()
                if key.endswith("NUM_THREADS")
            },
        },
        "execution_policy": {
            "timeout_seconds": None,
            "no_timeout": True,
            "retry": False,
            "resume": "missing-terminal-records-only",
        },
    }
    payload = {
        **stable,
        "environment_digest": canonical_payload_digest(stable),
        "frozen_at": utc_now(),
    }
    atomic_write_json(path, payload)
    return path


def verify_v2_environment(root: Path, method: str) -> dict[str, Any]:
    _require_v2_method(method)
    path = root / v2_environment_relative(method)
    require_committed_file(root, v2_environment_relative(method))
    manifest = read_json(path)
    stable = {
        key: value
        for key, value in manifest.items()
        if key not in {"environment_digest", "frozen_at"}
    }
    if manifest.get("schema_version") != V2_ENVIRONMENT_SCHEMA:
        raise PreflightError(f"invalid V2 environment schema for {method}")
    if canonical_payload_digest(stable) != manifest.get("environment_digest"):
        raise PreflightError(f"V2 environment digest is invalid for {method}")
    if manifest.get("protocol_digest") != V2_PROTOCOL_DIGEST:
        raise PreflightError(f"V2 environment protocol mismatch for {method}")
    if manifest.get("input_manifest_digest") != v2_source_manifest_digest(root):
        raise PreflightError(f"V2 environment input-manifest mismatch for {method}")
    resolve_frozen_worker_environment(root, manifest)
    return manifest


def protocol_preflight_v2(root: Path, method: str, python: Path) -> dict[str, Any]:
    _require_v2_method(method)
    global_preflight(root)
    protocol = verify_v2_protocol(root)
    manifest_digest = v2_source_manifest_digest(root)
    python = _python_path(python)
    # This performs only synthetic native calls and schema validation.  It is
    # intentionally not a real-case authorization or prediction lock.
    identity, synthetic, schema = _environment_preflight_details(
        root,
        method,
        python,
        reuse_historical_manifest=False,
        synthetic_timeout_seconds=None,
    )
    return {
        "schema_version": "rca_baseline_rescue_protocol_preflight_v2",
        "method": method,
        "datasets": list(DATASET_ORDER),
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "input_manifest_digest": manifest_digest,
        "rcaeval_commit": RCAEVAL_COMMIT,
        "native_module_digest": _v2_native_module_digest(method),
        "environment": {
            "python_executable": identity["python_executable"],
            "runtime_python_executable": identity["runtime_python_executable"],
            "dependency_manifest_digest": identity["dependency_manifest_digest"],
        },
        "synthetic_preflight": {
            "status": "PASS",
            "fingerprint": synthetic["fingerprint"],
            "runs": 2,
        },
        "schema_preflight": schema,
        "real_execution_authorized": False,
        "labels_joined": False,
    }


def _parse_iso(value: Any, key: str) -> datetime:
    if not isinstance(value, str):
        raise PreflightError(f"V2 record has invalid {key}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PreflightError(f"V2 record has invalid {key}") from exc
    if parsed.tzinfo is None:
        raise PreflightError(f"V2 record has timezone-free {key}")
    return parsed


def validate_v2_record(
    payload: Mapping[str, Any],
    *,
    root: Path,
    method: str,
    dataset: str,
    case_id: str,
    attempt: Mapping[str, Any],
) -> None:
    """Validate a terminal V2 record without using labels or correctness."""

    _require_v2_method(method)
    assert_firewall_safe_record(payload)
    expected = {
        "schema_version": V2_CASE_SCHEMA,
        "protocol_version": V2_PROTOCOL_VERSION,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method": method,
        "dataset": dataset,
        "case_id": case_id,
        "attempt_id": attempt["attempt_id"],
        "ada_rca_commit": REQUIRED_STARTING_HEAD,
        "execution_commit": attempt["execution_commit"],
        "rcaeval_commit": RCAEVAL_COMMIT,
        "environment_digest": attempt["environment_digest"],
        "input_manifest_digest": attempt["input_manifest_digest"],
        "candidate_registry_digest": _candidate_registry_digest(root, dataset),
        "timeout_seconds": None,
        "window_semantics": "[t0-600s,t0+600s)",
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise PreflightError(f"V2 record provenance mismatch: {key}")
    if payload.get("terminal_status") not in V2_STATUS_VALUES:
        raise PreflightError("V2 record has an invalid terminal status")
    if payload.get("native_module_digest") != attempt["native_module_digest"]:
        raise PreflightError("V2 record native-module digest mismatch")
    if payload.get("native_module_digest") != payload.get("method_source_digest"):
        raise PreflightError("V2 record source digest fields disagree")
    if payload.get("source_record_digests") != _v2_source_record_digests(
        root, method, dataset, case_id
    ):
        raise PreflightError("V2 record source digest binding is invalid")
    if payload.get("seed_state", {}).get("canonical_seed") != CANONICAL_SEED:
        raise PreflightError("V2 record canonical seed mismatch")
    if payload.get("seed_state", {}).get("python_hash_seed") != CANONICAL_SEED:
        raise PreflightError("V2 record Python hash seed mismatch")
    if payload.get("requested_worker_count") != attempt["requested_worker_count"]:
        raise PreflightError("V2 record requested worker count mismatch")
    if payload.get("execution_worker_count") != attempt["actual_worker_count"]:
        raise PreflightError("V2 record actual worker count mismatch")
    slot = payload.get("execution_worker_slot")
    if not isinstance(slot, int) or not 0 <= slot < attempt["actual_worker_count"]:
        raise PreflightError("V2 record worker slot is invalid")
    start = _parse_iso(payload.get("start_timestamp"), "start_timestamp")
    finish = _parse_iso(payload.get("finish_timestamp"), "finish_timestamp")
    if finish < start:
        raise PreflightError("V2 record timestamps are reversed")
    elapsed = payload.get("elapsed_seconds")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed < 0:
        raise PreflightError("V2 record elapsed time is invalid")
    native = payload.get("native_ranking", [])
    adapted = payload.get("adapted_ranking", [])
    if not isinstance(native, list) or not isinstance(adapted, list):
        raise PreflightError("V2 rankings must be lists")
    if payload.get("native_output_length") != len(native):
        raise PreflightError("V2 native output length does not match its record")
    if payload.get("adapted_output_length") != len(adapted):
        raise PreflightError("V2 adapted output length does not match its record")
    status = payload["terminal_status"]
    if status == "SUCCESS":
        if not native or not adapted:
            raise PreflightError("V2 SUCCESS record has an empty ranking")
        if payload.get("native_output_digest") != canonical_payload_digest(native):
            raise PreflightError("V2 native output digest mismatch")
        if payload.get("adapted_output_digest") != canonical_payload_digest(adapted):
            raise PreflightError("V2 adapted output digest mismatch")
    else:
        if native or adapted or payload.get("native_output_digest") is not None or payload.get("adapted_output_digest") is not None:
            raise PreflightError("V2 failure record contains a ranking or digest")


def _attempt_payload(
    root: Path,
    method: str,
    attempt_id: str,
    environment: Mapping[str, Any],
    requested_workers: int,
    available: int,
    actual: int,
) -> dict[str, Any]:
    _require_v2_attempt(method, attempt_id)
    execution_commit = git(root, "rev-parse", "HEAD").stdout.strip()
    stable = {
        "schema_version": V2_ATTEMPT_SCHEMA,
        "protocol_version": V2_PROTOCOL_VERSION,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method": method,
        "attempt_id": attempt_id,
        "datasets": list(DATASET_ORDER),
        "execution_commit": execution_commit,
        "environment_digest": environment["environment_digest"],
        "input_manifest_digest": v2_source_manifest_digest(root),
        "candidate_registry_digests": _v2_candidate_digests(root),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "native_module_digest": _v2_native_module_digest(method),
        "requested_worker_count": requested_workers,
        "available_cpu_count": available,
        "actual_worker_count": actual,
        "parallel_case_processes": True,
        "timeout_seconds": None,
        "no_timeout": True,
        "retry": False,
        "resume_policy": "missing-terminal-records-only",
        "seed": CANONICAL_SEED,
        "created_at": utc_now(),
        "labels_joined": False,
    }
    return {**stable, "attempt_digest": canonical_payload_digest(stable)}


def _verify_attempt_payload(root: Path, payload: Mapping[str, Any], method: str, attempt_id: str) -> None:
    _require_v2_method(method)
    _require_v2_attempt(method, attempt_id)
    if payload.get("schema_version") != V2_ATTEMPT_SCHEMA or payload.get("method") != method:
        raise PreflightError("V2 attempt metadata schema/method mismatch")
    if payload.get("attempt_id") != attempt_id:
        raise PreflightError("V2 attempt ID mismatch")
    stable = {key: value for key, value in payload.items() if key != "attempt_digest"}
    if canonical_payload_digest(stable) != payload.get("attempt_digest"):
        raise PreflightError("V2 attempt metadata digest is invalid")
    if payload.get("protocol_digest") != V2_PROTOCOL_DIGEST or payload.get("timeout_seconds") is not None:
        raise PreflightError("V2 attempt violates protocol provenance")
    if tuple(payload.get("datasets", ())) != DATASET_ORDER:
        raise PreflightError("V2 attempt dataset scope is invalid")
    if payload.get("input_manifest_digest") != v2_source_manifest_digest(root):
        raise PreflightError("V2 attempt input manifest mismatch")
    if payload.get("rcaeval_commit") != RCAEVAL_COMMIT:
        raise PreflightError("V2 attempt RCAEval commit mismatch")
    if payload.get("no_timeout") is not True or payload.get("retry") is not False:
        raise PreflightError("V2 attempt execution policy is invalid")


def _load_v2_attempt(root: Path, method: str, attempt_id: str) -> dict[str, Any]:
    path = root / v2_attempt_relative(method, attempt_id)
    if not path.is_file():
        raise SequenceError(f"V2 attempt metadata is missing: {path}")
    payload = read_json(path)
    _verify_attempt_payload(root, payload, method, attempt_id)
    return payload


def _load_v2_records(root: Path, attempt: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    method = str(attempt["method"])
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for dataset in DATASET_ORDER:
        for case_id in expected_case_ids(root, dataset):
            path = root / v2_record_relative(method, attempt["attempt_id"], dataset, case_id)
            if not path.is_file():
                continue
            payload = read_json(path)
            validate_v2_record(
                payload,
                root=root,
                method=method,
                dataset=dataset,
                case_id=case_id,
                attempt=attempt,
            )
            records[(dataset, case_id)] = payload
    return records


def pending_v2_cases(
    root: Path, attempt: Mapping[str, Any]
) -> tuple[tuple[str, str], ...]:
    """Return only cases without a valid terminal record; failures are not retried."""

    existing = _load_v2_records(root, attempt)
    return tuple(pair for pair in _case_pairs(root) if pair not in existing)


def _persist_record(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise RescueV2Error("V2 scheduler refuses to overwrite a terminal record")
    atomic_write_json(path, payload)


def _case_pairs(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (dataset, case_id)
        for dataset in DATASET_ORDER
        for case_id in expected_case_ids(root, dataset)
    )


def _partition(cases: Sequence[tuple[str, str]], workers: int) -> tuple[tuple[tuple[str, str], ...], ...]:
    if not cases:
        return ()
    active = min(workers, len(cases))
    return tuple(tuple(cases[index::active]) for index in range(active))


class _Heartbeat:
    def __init__(self, path: Path, interval: float) -> None:
        self.path = path
        self.interval = max(0.1, interval)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.cases: dict[str, dict[str, Any]] = {}
        self.thread = threading.Thread(target=self._run, name="rescue-v2-heartbeat", daemon=True)

    def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.thread.start()

    def update(self, key: str, values: Mapping[str, Any]) -> None:
        with self.lock:
            self.cases[key] = dict(values)

    def remove(self, key: str) -> None:
        with self.lock:
            self.cases.pop(key, None)

    def close(self) -> None:
        self.stop.set()
        self.thread.join(timeout=min(self.interval + 1, 10))

    def _run(self) -> None:
        while not self.stop.wait(self.interval):
            with self.lock:
                rows = [dict(value) for value in self.cases.values()]
            now = time.monotonic()
            for row in rows:
                row["heartbeat_timestamp"] = utc_now()
                row["elapsed_seconds"] = max(0.0, now - float(row.pop("monotonic_start", now)))
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")


def _start_v2_server(root: Path, python: Path, method: str, env: Mapping[str, str]) -> subprocess.Popen[str]:
    server = subprocess.Popen(
        (str(python), "-m", "src.baseline_eval.rescue_server_v2", "--method", method),
        cwd=root,
        env=dict(env),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        if server.stdout is None:
            raise RescueV2Error("V2 server stdout pipe is unavailable")
        ready, _, _ = select.select([server.stdout], [], [], None)
        if not ready:
            raise RescueV2Error("V2 server did not finish native import preflight")
        handshake = json.loads(server.stdout.readline())
        if handshake != {"status": "READY", "method": method}:
            raise RescueV2Error("V2 server readiness handshake is invalid")
        return server
    except BaseException:
        _terminate_v2_server(server)
        raise


def _terminate_v2_server(server: subprocess.Popen[str]) -> None:
    if server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


def _stop_v2_server(server: subprocess.Popen[str]) -> None:
    if server.stdin is None or server.stdout is None:
        raise RescueV2Error("V2 server pipes are unavailable")
    server.stdin.write(json.dumps({"command": "stop"}) + "\n")
    server.stdin.flush()
    ready, _, _ = select.select([server.stdout], [], [], 30)
    if not ready or json.loads(server.stdout.readline()).get("status") != "STOPPED":
        raise RescueV2Error("V2 server did not stop cleanly")
    if server.wait(timeout=30) != 0:
        raise RescueV2Error("V2 server exited nonzero")


def _read_server_json(
    server: subprocess.Popen[str],
    *,
    heartbeat: _Heartbeat | None,
    heartbeat_key: str,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    if server.stdout is None:
        raise RescueV2Error("V2 server stdout is unavailable")
    while True:
        ready, _, _ = select.select([server.stdout], [], [], 1.0)
        if ready:
            line = server.stdout.readline()
            if not line:
                raise RescueV2Error("V2 server exited before its terminal response")
            return json.loads(line)
        if heartbeat is not None:
            heartbeat.update(heartbeat_key, state)


def _run_v2_shard(
    *,
    root: Path,
    method: str,
    attempt: Mapping[str, Any],
    shard: Sequence[tuple[str, str]],
    worker_slot: int,
    python: Path,
    env: Mapping[str, str],
    heartbeat: _Heartbeat,
    stop_event: threading.Event,
) -> int:
    server = _start_v2_server(root, python, method, env)
    processed = 0
    try:
        if server.stdin is None:
            raise RescueV2Error("V2 server stdin is unavailable")
        for dataset, case_id in shard:
            if stop_event.is_set():
                break
            path = root / v2_record_relative(method, attempt["attempt_id"], dataset, case_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            key = f"{dataset}/{case_id}"
            start = time.monotonic()
            request = {
                "command": "case",
                "execution_profile": "v2",
                "record_protocol_version": V2_PROTOCOL_VERSION,
                "record_protocol_digest": V2_PROTOCOL_DIGEST,
                "method": method,
                "dataset": dataset,
                "case_id": case_id,
                "attempt_id": attempt["attempt_id"],
                "environment_digest": attempt["environment_digest"],
                "input_manifest_digest": attempt["input_manifest_digest"],
                "candidate_registry_digest": attempt["candidate_registry_digests"][dataset],
                "execution_commit": attempt["execution_commit"],
                "execution_worker_count": attempt["actual_worker_count"],
                "execution_worker_slot": worker_slot,
                "worker_id": f"{method.lower()}-worker-{worker_slot}",
                "requested_worker_count": attempt["requested_worker_count"],
                "available_cpu_count": attempt["available_cpu_count"],
                "native_module_digest": attempt["native_module_digest"],
                "source_record_digests": _v2_source_record_digests(
                    root, method, dataset, case_id
                ),
                "output": str(path),
            }
            server.stdin.write(json.dumps(request, sort_keys=True) + "\n")
            server.stdin.flush()
            initial = _read_server_json(
                server,
                heartbeat=heartbeat,
                heartbeat_key=key,
                state={
                    "method": method,
                    "dataset": dataset,
                    "case_id": case_id,
                    "attempt_id": attempt["attempt_id"],
                    "worker_id": request["worker_id"],
                    "pid": None,
                    "start_timestamp": utc_now(),
                    "monotonic_start": start,
                    "terminal_status": "RUNNING",
                },
            )
            if initial.get("status") != "STARTED" or initial.get("case_id") != case_id:
                raise RescueV2Error("V2 server STARTED response is invalid")
            state = {
                "method": method,
                "dataset": dataset,
                "case_id": case_id,
                "attempt_id": attempt["attempt_id"],
                "worker_id": request["worker_id"],
                "pid": initial.get("pid"),
                "start_timestamp": initial.get("start_timestamp"),
                "monotonic_start": start,
                "terminal_status": "RUNNING",
            }
            heartbeat.update(key, state)
            response = _read_server_json(
                server,
                heartbeat=heartbeat,
                heartbeat_key=key,
                state=state,
            )
            if response.get("case_id") != case_id or response.get("status") not in {
                "RECORDED",
                "PROCESS_CRASH/OOM",
            }:
                raise RescueV2Error("V2 server terminal response is invalid")
            if not path.is_file():
                raise RescueV2Error("V2 server reported a case without a record")
            payload = read_json(path)
            validate_v2_record(
                payload,
                root=root,
                method=method,
                dataset=dataset,
                case_id=case_id,
                attempt=attempt,
            )
            print(
                f"method={method} dataset={dataset} case={case_id} "
                f"status={payload['terminal_status']} native_len={payload['native_output_length']} "
                f"adapted_len={payload['adapted_output_length']} wall={payload['elapsed_seconds']:.3f}s "
                f"native_digest={payload.get('native_output_digest')} adapted_digest={payload.get('adapted_output_digest')}",
                flush=True,
            )
            heartbeat.remove(key)
            processed += 1
        _stop_v2_server(server)
        return processed
    except BaseException:
        stop_event.set()
        raise
    finally:
        _terminate_v2_server(server)


def _runtime_summary(
    *,
    root: Path,
    attempt: Mapping[str, Any],
    records: Mapping[tuple[str, str], Mapping[str, Any]],
    started_at: str,
    finished_at: str,
    wall: float,
) -> dict[str, Any]:
    ordered = _case_pairs(root)
    timings = []
    status_counts = {dataset: {status: 0 for status in V2_STATUS_VALUES} for dataset in DATASET_ORDER}
    for dataset, case_id in ordered:
        row = records[(dataset, case_id)]
        status = row["terminal_status"]
        status_counts[dataset][status] += 1
        timings.append({
            "dataset": dataset,
            "case_id": case_id,
            "terminal_status": status,
            "worker_id": row["worker_id"],
            "pid": row.get("pid"),
            "start_timestamp": row["start_timestamp"],
            "finish_timestamp": row["finish_timestamp"],
            "elapsed_seconds": row["elapsed_seconds"],
        })
    stable = {
        "schema_version": V2_RUNTIME_SCHEMA,
        "protocol_version": V2_PROTOCOL_VERSION,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method": attempt["method"],
        "attempt_id": attempt["attempt_id"],
        "execution_commit": attempt["execution_commit"],
        "requested_worker_count": attempt["requested_worker_count"],
        "actual_worker_count": attempt["actual_worker_count"],
        "available_cpu_count": attempt["available_cpu_count"],
        "timeout_seconds": None,
        "no_timeout": True,
        "attempt_start_timestamp": started_at,
        "attempt_finish_timestamp": finished_at,
        "attempt_wall_time_seconds": wall,
        "terminal_case_count": len(timings),
        "status_counts": status_counts,
        "case_timings": timings,
        "labels_joined": False,
    }
    return {**stable, "runtime_digest": canonical_payload_digest(stable)}


def _build_v2_method_lock(
    root: Path,
    attempt: Mapping[str, Any],
    records: Mapping[tuple[str, str], Mapping[str, Any]],
    runtime_path: Path,
) -> dict[str, Any]:
    status_counts = {
        dataset: {
            status: Counter(
                row["terminal_status"]
                for (row_dataset, _), row in records.items()
                if row_dataset == dataset
            ).get(status, 0)
            for status in V2_STATUS_VALUES
        }
        for dataset in DATASET_ORDER
    }
    record_digests = [
        {
            "dataset": dataset,
            "case_id": case_id,
            "sha256": sha256_file(root / v2_record_relative(attempt["method"], attempt["attempt_id"], dataset, case_id)),
        }
        for dataset, case_id in _case_pairs(root)
    ]
    blocking = _v2_blocking_status_counts(status_counts)
    stable = {
        "schema_version": V2_METHOD_LOCK_SCHEMA,
        "protocol_version": V2_PROTOCOL_VERSION,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method": attempt["method"],
        "attempt_id": attempt["attempt_id"],
        "execution_commit": attempt["execution_commit"],
        "environment_digest": attempt["environment_digest"],
        "input_manifest_digest": attempt["input_manifest_digest"],
        "candidate_registry_digests": attempt["candidate_registry_digests"],
        "native_module_digest": attempt["native_module_digest"],
        "rcaeval_commit": RCAEVAL_COMMIT,
        "datasets": list(DATASET_ORDER),
        "expected_case_ids": {
            dataset: list(expected_case_ids(root, dataset)) for dataset in DATASET_ORDER
        },
        "record_counts": {dataset: EXPECTED_CASES_PER_DATASET for dataset in DATASET_ORDER},
        "status_counts": status_counts,
        "blocking_status_counts": blocking,
        "execution_validity": v2_execution_validity(blocking),
        "requested_worker_count": attempt["requested_worker_count"],
        "actual_worker_count": attempt["actual_worker_count"],
        "available_cpu_count": attempt["available_cpu_count"],
        "timeout_seconds": None,
        "no_timeout": True,
        "retry": False,
        "terminal_record_digests": record_digests,
        "runtime_summary": {
            "path": str(runtime_path.relative_to(root)),
            "sha256": sha256_file(runtime_path),
        },
        "contains_evaluation": False,
        "labels_joined": False,
        "locked_at": utc_now(),
    }
    payload = {**stable, "lock_digest": canonical_payload_digest(stable)}
    assert_firewall_safe_record(payload)
    return payload


def _start_heartbeat(log_file: Path, interval: float) -> _Heartbeat:
    heartbeat = _Heartbeat(log_file, interval)
    heartbeat.start()
    return heartbeat


def _run_pending_v2_cases(
    *,
    root: Path,
    method: str,
    attempt: Mapping[str, Any],
    pending: Sequence[tuple[str, str]],
    python: Path,
    env: Mapping[str, str],
    log_file: Path,
    heartbeat_seconds: float,
) -> None:
    shards = _partition(pending, int(attempt["actual_worker_count"]))
    if not shards:
        return
    heartbeat = _start_heartbeat(log_file, heartbeat_seconds)
    stop_event = threading.Event()
    pool = ThreadPoolExecutor(max_workers=len(shards), thread_name_prefix="rescue-v2-case-shard")
    futures = [
        pool.submit(
            _run_v2_shard,
            root=root,
            method=method,
            attempt=attempt,
            shard=shard,
            worker_slot=slot,
            python=python,
            env=env,
            heartbeat=heartbeat,
            stop_event=stop_event,
        )
        for slot, shard in enumerate(shards)
    ]
    try:
        for future in futures:
            future.result()
    except BaseException:
        stop_event.set()
        raise
    finally:
        heartbeat.close()
        if stop_event.is_set():
            pool.shutdown(wait=False, cancel_futures=True)
        else:
            pool.shutdown(wait=True)


def _write_v2_attempt_metadata(root: Path, attempt: Mapping[str, Any]) -> Path:
    path = root / v2_attempt_relative(attempt["method"], attempt["attempt_id"])
    if path.exists():
        raise SequenceError("V2 attempt metadata already exists")
    atomic_write_json(path, attempt)
    return path


def run_v2(
    root: Path,
    method: str,
    attempt_id: str,
    *,
    python: Path,
    requested_workers: int,
    resume: bool = False,
    resume_policy: str = "fresh",
    datasets: Sequence[str] = DATASET_ORDER,
    no_timeout: bool = False,
    log_file: Path,
    heartbeat_seconds: float = 30.0,
) -> Path | None:
    """Run one method across both datasets, resuming only missing records."""

    _require_v2_method(method)
    require_attempt_id(attempt_id)
    _require_v2_attempt(method, attempt_id)
    _require_dataset_scope(datasets)
    if not no_timeout:
        raise SequenceError("V2 real execution requires the explicit --no-timeout flag")
    if resume_policy not in {"fresh", "missing-only"}:
        raise SequenceError("V2 resume policy must be fresh or missing-only")
    if resume and resume_policy != "missing-only":
        raise SequenceError("--resume requires --resume-policy missing-only")
    if not resume and resume_policy != "fresh":
        raise SequenceError("a new V2 attempt requires --resume-policy fresh")
    if (root / V2_GLOBAL_LOCK_RELATIVE).exists():
        raise SequenceError("V2 global prediction lock already exists")
    require_clean_git(root) if not resume else None
    if not resume:
        global_preflight(root)
    else:
        # An interrupted container necessarily leaves its newly written V2
        # records uncommitted. Resume audits the frozen external state and the
        # exact attempt commit below without requiring a clean worktree.
        verify_v2_protocol(root)
        verify_rcaeval_clean()
        assert_ada_rca_frozen_unchanged(root)
    verify_v2_protocol(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    manifest_digest = v2_source_manifest_digest(root)
    environment = verify_v2_environment(root, method)
    expected_python = _python_path(Path(environment["identity"]["python_executable"]))
    python = _python_path(python)
    if python != expected_python:
        raise PreflightError(
            f"V2 run interpreter differs from the frozen method environment: {python} != {expected_python}"
        )
    available = available_cpu_count()
    actual = actual_worker_count(requested_workers, available=available)
    attempt_path = root / v2_attempt_relative(method, attempt_id)
    method_lock = root / v2_method_lock_relative(method)
    reissued_method_lock = root / v2_method_lock_reissued_relative(method)
    if method_lock.exists() or reissued_method_lock.exists():
        raise SequenceError(f"V2 method lock already exists for {method}")
    if resume:
        attempt = _load_v2_attempt(root, method, attempt_id)
        if attempt["execution_commit"] != git(root, "rev-parse", "HEAD").stdout.strip():
            raise SequenceError("V2 resume requires the original execution commit")
        if attempt["environment_digest"] != environment["environment_digest"]:
            raise PreflightError("V2 resume environment digest differs from the attempt")
        if attempt["requested_worker_count"] != requested_workers or attempt["actual_worker_count"] != actual:
            raise SequenceError("V2 resume requires the original worker configuration")
        _load_v2_records(root, attempt)
    else:
        if attempt_path.exists():
            raise SequenceError("a fresh V2 attempt cannot reuse existing attempt metadata")
        attempt = _attempt_payload(
            root,
            method,
            attempt_id,
            environment,
            requested_workers,
            available,
            actual,
        )
        _write_v2_attempt_metadata(root, attempt)
        existing = {}
    # The shared Git-common-directory lock prevents a V1/V2 or two-container
    # execution of the same method from overlapping, without sharing a Git
    # index or method output directory.
    with exclusive_method_execution_lock(
        method, lock_root=git_common_execution_lock_root(root)
    ):
        existing = _load_v2_records(root, attempt)
        pending = pending_v2_cases(root, attempt)
        if pending:
            run_start = time.monotonic()
            run_start_timestamp = utc_now()
            env = resolve_frozen_worker_environment(root, environment)
            try:
                _run_pending_v2_cases(
                    root=root,
                    method=method,
                    attempt=attempt,
                    pending=pending,
                    python=python,
                    env=env,
                    log_file=log_file,
                    heartbeat_seconds=heartbeat_seconds,
                )
            except BaseException:
                # Records already atomically committed by completed children are
                # retained.  No runtime summary or method lock is written for
                # an interrupted/incomplete attempt.
                raise
            run_wall = time.monotonic() - run_start
            run_end_timestamp = utc_now()
        else:
            run_wall = 0.0
            run_start_timestamp = utc_now()
            run_end_timestamp = run_start_timestamp
        records = _load_v2_records(root, attempt)
        if len(records) != len(_case_pairs(root)):
            return None
        runtime_path = root / v2_runtime_relative(method, attempt_id)
        if runtime_path.exists():
            raise SequenceError("V2 runtime summary already exists")
        runtime = _runtime_summary(
            root=root,
            attempt=attempt,
            records=records,
            started_at=run_start_timestamp,
            finished_at=run_end_timestamp,
            wall=run_wall,
        )
        atomic_write_json(runtime_path, runtime)
        lock_path = root / v2_method_lock_relative(method)
        if lock_path.exists():
            raise SequenceError("V2 method lock appeared during execution")
        lock = _build_v2_method_lock(root, attempt, records, runtime_path)
        atomic_write_json(lock_path, lock)
        return lock_path


def verify_v2_method_lock(
    root: Path,
    method: str,
    *,
    require_committed: bool = True,
    lock_relative: Path | None = None,
    enforce_validity: bool = True,
) -> dict[str, Any]:
    _require_v2_method(method)
    relative = lock_relative or active_v2_method_lock_relative(root, method)
    if require_committed:
        require_committed_file(root, relative)
    path = root / relative
    if not path.is_file():
        raise PreflightError(f"V2 method lock is missing for {method}")
    lock = read_json(path)
    if lock.get("schema_version") != V2_METHOD_LOCK_SCHEMA:
        raise PreflightError(f"V2 method lock schema is invalid for {method}")
    if lock.get("method") != method:
        raise PreflightError(f"V2 method lock method identity is invalid for {method}")
    _require_v2_attempt(method, str(lock.get("attempt_id")))
    stable = {key: value for key, value in lock.items() if key != "lock_digest"}
    if canonical_payload_digest(stable) != lock.get("lock_digest"):
        raise PreflightError(f"V2 method lock digest is invalid for {method}")
    attempt = _load_v2_attempt(root, method, lock["attempt_id"])
    if lock.get("execution_commit") != attempt.get("execution_commit"):
        raise PreflightError(f"V2 method lock execution commit mismatch for {method}")
    if lock.get("environment_digest") != attempt.get("environment_digest"):
        raise PreflightError(f"V2 method lock environment mismatch for {method}")
    if lock.get("input_manifest_digest") != v2_source_manifest_digest(root):
        raise PreflightError(f"V2 method lock input manifest mismatch for {method}")
    if lock.get("candidate_registry_digests") != _v2_candidate_digests(root):
        raise PreflightError(f"V2 method lock candidate registry mismatch for {method}")
    expected_pairs = set(_case_pairs(root))
    observed_pairs: set[tuple[str, str]] = set()
    for item in lock.get("terminal_record_digests", []):
        pair = (item.get("dataset"), item.get("case_id"))
        if pair in observed_pairs:
            raise PreflightError(f"duplicate V2 record in {method} lock")
        observed_pairs.add(pair)
        record_path = root / v2_record_relative(method, lock["attempt_id"], pair[0], pair[1])
        if sha256_file(record_path) != item.get("sha256"):
            raise PreflightError(f"V2 record digest mismatch for {method} {pair}")
        validate_v2_record(
            read_json(record_path),
            root=root,
            method=method,
            dataset=pair[0],
            case_id=pair[1],
            attempt=attempt,
        )
    if observed_pairs != expected_pairs:
        raise PreflightError(f"V2 method lock does not cover 180 cases for {method}")
    observed_counts = {
        dataset: {
            status: sum(
                1
                for item in lock["terminal_record_digests"]
                if item["dataset"] == dataset
                and read_json(
                    root / v2_record_relative(method, lock["attempt_id"], item["dataset"], item["case_id"])
                )["terminal_status"]
                == status
            )
            for status in V2_STATUS_VALUES
        }
        for dataset in DATASET_ORDER
    }
    if lock.get("status_counts") != observed_counts:
        raise PreflightError(f"V2 status counts are invalid for {method}")
    observed_blocking = _v2_blocking_status_counts(observed_counts)
    if lock.get("blocking_status_counts") != observed_blocking:
        raise PreflightError(f"V2 blocking status counts are invalid for {method}")
    expected_validity = v2_execution_validity(observed_blocking)
    if enforce_validity and lock.get("execution_validity") != expected_validity:
        raise PreflightError(f"V2 execution validity is inconsistent for {method}")
    if lock.get("record_counts") != {dataset: EXPECTED_CASES_PER_DATASET for dataset in DATASET_ORDER}:
        raise PreflightError(f"V2 record counts are invalid for {method}")
    if lock.get("timeout_seconds") is not None or lock.get("no_timeout") is not True:
        raise PreflightError(f"V2 method lock timeout policy is invalid for {method}")
    runtime_binding = lock.get("runtime_summary")
    if not isinstance(runtime_binding, Mapping):
        raise PreflightError(f"V2 runtime summary binding is missing for {method}")
    runtime_path = root / runtime_binding["path"]
    if require_committed:
        require_committed_file(root, Path(runtime_binding["path"]))
    if sha256_file(runtime_path) != runtime_binding.get("sha256"):
        raise PreflightError(f"V2 runtime summary digest mismatch for {method}")
    if relative in {
        v2_method_lock_reissued_relative(method),
        v2_method_lock_reissued_v2_relative(method),
    }:
        if lock.get("supersedes_lock_path") != v2_method_lock_relative(method).as_posix():
            raise PreflightError(f"V2 reissued lock supersession path is invalid for {method}")
        superseded = root / v2_method_lock_relative(method)
        superseded_payload = read_json(superseded) if superseded.is_file() else {}
        if superseded_payload.get("lock_digest") != lock.get("supersedes_lock_digest"):
            raise PreflightError(f"V2 reissued lock no longer binds the original lock for {method}")
    return lock


def reissue_v2_method_lock(root: Path, method: str, attempt_id: str) -> Path:
    """Create a new lock attestation without changing an existing lock file."""

    _require_v2_method(method)
    _require_v2_attempt(method, attempt_id)
    require_clean_git(root)
    global_preflight(root)
    verify_v2_protocol(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    canonical_relative = v2_method_lock_relative(method)
    reissued_relative = v2_method_lock_reissued_v2_relative(method)
    canonical = root / canonical_relative
    reissued = root / reissued_relative
    if not canonical.is_file():
        raise PreflightError(f"original V2 method lock is missing for {method}")
    if reissued.exists():
        raise SequenceError(f"V2 reissued method lock already exists for {method}")
    old = verify_v2_method_lock(
        root,
        method,
        require_committed=True,
        lock_relative=canonical_relative,
        enforce_validity=False,
    )
    if old.get("attempt_id") != attempt_id:
        raise SequenceError(f"original V2 method lock attempt mismatch for {method}")
    if old.get("execution_validity") == "INTEGRITY_VALID":
        raise SequenceError(f"V2 method lock is already integrity-valid for {method}")
    attempt = _load_v2_attempt(root, method, attempt_id)
    records = _load_v2_records(root, attempt)
    expected_count = len(_case_pairs(root))
    if len(records) != expected_count:
        raise PreflightError(f"V2 method lock reissue requires all {expected_count} records for {method}")
    runtime_path = root / v2_runtime_relative(method, attempt_id)
    if not runtime_path.is_file():
        raise PreflightError(f"V2 runtime summary is missing for {method}")
    candidate = _build_v2_method_lock(root, attempt, records, runtime_path)
    if candidate["execution_validity"] != "INTEGRITY_VALID":
        raise V2EvaluationBlocked(f"cannot reissue {method}: blocking terminal status remains")
    ignored = {"execution_validity", "locked_at", "lock_digest"}
    old_comparable = {key: value for key, value in old.items() if key not in ignored}
    candidate_comparable = {key: value for key, value in candidate.items() if key not in ignored}
    if old_comparable != candidate_comparable:
        raise PreflightError(f"V2 reissue would change immutable execution evidence for {method}")
    stable = {
        **{key: value for key, value in candidate.items() if key != "lock_digest"},
        "supersedes_lock_path": canonical_relative.as_posix(),
        "supersedes_lock_digest": old["lock_digest"],
        "lock_reissue_reason": "repair outer-dictionary truthiness in execution-validity classification",
        "lock_reissue_commit": git(root, "rev-parse", "HEAD").stdout.strip(),
        "locked_at": utc_now(),
    }
    payload = {**stable, "lock_digest": canonical_payload_digest(stable)}
    assert_firewall_safe_record(payload)
    atomic_write_json(reissued, payload)
    return reissued


def create_v2_global_prediction_lock(root: Path) -> Path:
    require_clean_git(root)
    global_preflight(root)
    verify_v2_protocol(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    manifest_digest = v2_source_manifest_digest(root)
    path = root / V2_GLOBAL_LOCK_RELATIVE
    if path.exists():
        raise PreflightError("V2 global prediction lock already exists")
    method_rows = []
    for method in V2_METHODS:
        lock_relative = active_v2_method_lock_relative(root, method)
        lock = verify_v2_method_lock(
            root, method, require_committed=True, lock_relative=lock_relative
        )
        if lock.get("execution_validity") != "INTEGRITY_VALID":
            raise V2EvaluationBlocked(
                f"cannot create V2 global lock: {method} has invalid execution evidence"
            )
        if any(lock.get("blocking_status_counts", {}).values()):
            raise V2EvaluationBlocked(
                f"cannot create V2 global lock: {method} has blocking terminal statuses"
            )
        method_rows.append({
            "method": method,
            "attempt_id": lock["attempt_id"],
            "method_lock_path": lock_relative.as_posix(),
            "method_lock_sha256": sha256_file(root / lock_relative),
            "record_digest": canonical_payload_digest(lock["terminal_record_digests"]),
            "environment_digest": lock["environment_digest"],
            "status_counts": lock["status_counts"],
            "requested_worker_count": lock["requested_worker_count"],
            "actual_worker_count": lock["actual_worker_count"],
        })
    stable = {
        "schema_version": V2_GLOBAL_LOCK_SCHEMA,
        "protocol_version": V2_PROTOCOL_VERSION,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method_order": list(V2_METHODS),
        "dataset_order": list(DATASET_ORDER),
        "datasets_case_counts": {dataset: EXPECTED_CASES_PER_DATASET for dataset in DATASET_ORDER},
        "attempt_ids": {row["method"]: row["attempt_id"] for row in method_rows},
        "methods": method_rows,
        "input_manifest_digest": manifest_digest,
        "candidate_registry_digests": _v2_candidate_digests(root),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "ada_rca_frozen_starting_commit": REQUIRED_STARTING_HEAD,
        "adapter_version": V2_PROTOCOL_VERSION,
        "parallel_worker_configuration": {
            "allowed_requested_workers": list(V2_ALLOWED_WORKERS),
            "per_method": {
                row["method"]: {
                    "requested": row["requested_worker_count"],
                    "actual": row["actual_worker_count"],
                }
                for row in method_rows
            },
        },
        "timeout_policy": {"no_timeout": True, "timeout_seconds": None, "retry": False},
        "labels_joined": False,
        "contains_evaluation": False,
        "locked_at": utc_now(),
    }
    payload = {**stable, "lock_digest": canonical_payload_digest(stable)}
    assert_firewall_safe_record(payload)
    atomic_write_json(path, payload)
    return path


def verify_v2_global_prediction_lock(root: Path, *, require_committed: bool = True) -> dict[str, Any]:
    verify_v2_protocol(root)
    verify_rcaeval_clean()
    path = root / V2_GLOBAL_LOCK_RELATIVE
    if require_committed:
        require_committed_file(root, V2_GLOBAL_LOCK_RELATIVE)
    if not path.is_file():
        raise PreflightError("V2 global prediction lock is missing")
    lock = read_json(path)
    stable = {key: value for key, value in lock.items() if key != "lock_digest"}
    if canonical_payload_digest(stable) != lock.get("lock_digest"):
        raise PreflightError("V2 global prediction lock digest is invalid")
    if lock.get("schema_version") != V2_GLOBAL_LOCK_SCHEMA:
        raise PreflightError("V2 global prediction lock schema is invalid")
    if tuple(lock.get("method_order", ())) != V2_METHODS or tuple(lock.get("dataset_order", ())) != DATASET_ORDER:
        raise PreflightError("V2 global prediction lock registry is invalid")
    if lock.get("labels_joined") is not False or lock.get("contains_evaluation") is not False:
        raise PreflightError("V2 global prediction lock is not pre-evaluation")
    if lock.get("protocol_digest") != V2_PROTOCOL_DIGEST or lock.get("rcaeval_commit") != RCAEVAL_COMMIT:
        raise PreflightError("V2 global prediction lock provenance is invalid")
    if lock.get("input_manifest_digest") != v2_source_manifest_digest(root):
        raise PreflightError("V2 global prediction lock input manifest mismatch")
    for method in V2_METHODS:
        method_row = next((row for row in lock.get("methods", []) if row.get("method") == method), None)
        if method_row is None:
            raise PreflightError(f"V2 global lock is missing {method}")
        lock_path_value = method_row.get("method_lock_path")
        if not isinstance(lock_path_value, str):
            raise PreflightError(f"V2 global lock method-lock path is missing for {method}")
        lock_relative = Path(lock_path_value)
        if lock_relative not in {
            v2_method_lock_relative(method),
            v2_method_lock_reissued_relative(method),
            v2_method_lock_reissued_v2_relative(method),
        }:
            raise PreflightError(f"V2 global lock method-lock path is invalid for {method}")
        method_lock = verify_v2_method_lock(
            root,
            method,
            require_committed=True,
            lock_relative=lock_relative,
        )
        if method_lock.get("execution_validity") != "INTEGRITY_VALID":
            raise PreflightError(f"V2 global lock binds invalid {method} evidence")
        if method_row.get("method_lock_sha256") != sha256_file(root / lock_relative):
            raise PreflightError(f"V2 global lock method-lock digest mismatch for {method}")
        if method_row.get("record_digest") != canonical_payload_digest(method_lock["terminal_record_digests"]):
            raise PreflightError(f"V2 global lock record digest mismatch for {method}")
    return lock


V2_MMBARO_RESCUE_CASES = (
    "re2ob-505f802370635ec3",
    "re2ob-1d9a0d1641171551",
)
V1_DIAGNOSTIC_ATTEMPTS = {
    "MicroRank": "microrank-a2-20260901",
    "TraceRCA": "tracerca-a2-20260901",
}


def _manifest_source_expectation(root: Path, dataset: str, case_id: str) -> dict[str, dict[str, Any]]:
    manifest = read_json(root / INPUT_MANIFEST_RELATIVE)
    for case in manifest["cases"]:
        if case["dataset"] == dataset and case["case_id"] == case_id:
            return {row["logical_source_role"]: row for row in case["sources"]}
    raise PreflightError("diagnostic case is absent from the frozen input manifest")


def _source_case_row(root: Path, dataset: str, case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = root / "artifacts" / "source" / dataset
    inputs = {row["case_id"]: row for row in read_jsonl(bundle / "inputs.jsonl")}
    sources = {row["case_id"]: row for row in read_jsonl(bundle / "sources.jsonl")}
    try:
        return inputs[case_id], sources[case_id]
    except KeyError as exc:
        raise PreflightError("diagnostic case is absent from the frozen source index") from exc


def _csv_schema_diagnostic(path: Path, role: str) -> dict[str, Any]:
    parser_name = "python" if role == "traces" else "pandas-default"
    try:
        frame = _read_csv_source(path, role)
        numeric = {
            column: bool(__import__("pandas").api.types.is_numeric_dtype(frame[column]))
            for column in frame.columns
        }
        finite = {}
        for column in frame.columns:
            if numeric[column]:
                finite[column] = bool(__import__("numpy").isfinite(frame[column].to_numpy()).all())
        return {
            "parser": parser_name,
            "readable": True,
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "columns": sorted(str(column) for column in frame.columns),
            "dtypes": {str(column): str(frame[column].dtype) for column in frame.columns},
            "numeric_columns": numeric,
            "finite_numeric_columns": finite,
        }
    except Exception as exc:
        return {
            "parser": parser_name,
            "readable": False,
            "row_count": None,
            "column_count": None,
            "columns": [],
            "dtypes": {},
            "numeric_columns": {},
            "finite_numeric_columns": {},
            "error_category": type(exc).__name__,
        }


def diagnose_mmbaro_input(
    root: Path,
    case_ids: Sequence[str] = V2_MMBARO_RESCUE_CASES,
) -> dict[str, Any]:
    """Audit the two historical mmBARO DATA_FAILURE sources label-free."""

    verify_rcaeval_clean()
    v2_source_manifest_digest(root)
    results = []
    for case_id in case_ids:
        if not case_id.startswith("re2ob-"):
            raise PreflightError("mmBARO rescue diagnostic is scoped to RE2-OB cases")
        case, source = _source_case_row(root, "re2ob", case_id)
        expected = _manifest_source_expectation(root, "re2ob", case_id)
        roles = []
        for role in METHOD_INPUT_ROLES["mmBARO"]:
            source_key = INPUT_ROLES[role]
            path = Path(source[source_key])
            exists = path.is_file()
            observed_size = path.stat().st_size if exists else None
            observed_sha = sha256_file(path) if exists else None
            schema = _csv_schema_diagnostic(path, role) if exists and role != "inject_time" else {
                "parser": "text" if role == "inject_time" else ("python" if role == "traces" else "pandas-default"),
                "readable": exists,
                "row_count": None,
                "column_count": None,
                "columns": [],
                "dtypes": {},
                "numeric_columns": {},
                "finite_numeric_columns": {},
            }
            expected_row = expected.get(role, {})
            roles.append({
                "role": role,
                "path": str(path),
                "exists": exists,
                "byte_size": observed_size,
                "sha256": observed_sha,
                "expected_byte_size": expected_row.get("byte_size"),
                "expected_sha256": expected_row.get("sha256"),
                "manifest_match": exists
                and observed_size == expected_row.get("byte_size")
                and observed_sha == expected_row.get("sha256"),
                "schema": schema,
            })
        adapter_checks: dict[str, Any] = {}
        try:
            telemetry, anchor, candidates, _sli, _observed, _provenance = load_legal_case_input(
                "mmBARO", "re2ob", case_id, drop_nonfinite_time=True
            )
            adapter_checks = {
                "legal_case_input": True,
                "canonical_metric_non_empty": bool(not telemetry["metric"].empty),
                "canonical_trace_non_empty": bool(not telemetry["traces"].empty),
                "anchor_seconds": anchor,
                "candidate_count": len(candidates),
                "derived_telemetry_compatible": True,
            }
        except Exception as exc:
            adapter_checks = {
                "legal_case_input": False,
                "canonical_metric_non_empty": False,
                "canonical_trace_non_empty": False,
                "derived_telemetry_compatible": False,
                "error_category": type(exc).__name__,
            }
        results.append({
            "dataset": "re2ob",
            "case_id": case_id,
            "anchor_time": int(case["anchor_time"]),
            "roles": roles,
            "adapter_checks": adapter_checks,
            "diagnostic_scope": "path, existence, bytes, SHA256, manifest, parser, schema, dtype, numeric/finiteness, timestamp, window, derived compatibility",
        })
    all_manifest_match = all(
        role["manifest_match"]
        for case in results
        for role in case["roles"]
    )
    nonfinite_metric_time = any(
        role["role"] == "simple_metrics"
        and role["schema"].get("finite_numeric_columns", {}).get("time") is False
        for case in results
        for role in case["roles"]
    )
    if all_manifest_match and nonfinite_metric_time:
        classification = "PROJECT_SIDE_VALIDATOR_ASYMMETRY_NONFINITE_METRIC_TIME"
    elif all_manifest_match:
        classification = "CURRENT_SOURCES_MATCH_FROZEN_MANIFEST"
    else:
        classification = "SOURCE_OR_MANIFEST_MISMATCH"
    return {
        "schema_version": "rca_baseline_rescue_mmbaro_input_diagnostic_v2",
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "method": "mmBARO",
        "cases": results,
        "all_sources_match_frozen_manifest": all_manifest_match,
        "classification": classification,
        "source_recovery_action": "NONE_PERMITTED_WHILE_MATCHING" if all_manifest_match else "DO_NOT_REGENERATE_MANIFEST",
        "labels_joined": False,
    }


def _trace_operation_sets(root: Path, dataset: str, case_id: str) -> dict[str, Any]:
    case, source = _source_case_row(root, dataset, case_id)
    anchor = int(case["anchor_time"])
    anchor_us = anchor * 1_000_000
    observation_start = anchor_us - 600_000_000
    observation_end = anchor_us + 600_000_000
    trace_path = Path(source["traces_path"])
    pre_ops: set[str] = set()
    post_ops: set[str] = set()
    trace_bounds: dict[str, tuple[int, int]] = {}
    canonical_count = 0
    with trace_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            trace_id = str(row["traceID"])
            start_time = int(row["startTime"])
            end_time = start_time + int(row["duration"])
            old_bounds = trace_bounds.get(trace_id, (start_time, end_time))
            trace_bounds[trace_id] = (
                min(start_time, old_bounds[0]),
                max(end_time, old_bounds[1]),
            )
            if observation_start <= end_time < observation_end:
                canonical_count += 1
                if end_time < anchor_us:
                    pre_ops.add(str(row["operationName"]))
                else:
                    post_ops.add(str(row["operationName"]))
    intersecting_trace_ids = {
        trace_id
        for trace_id, (minimum_start, maximum_end) in trace_bounds.items()
        if minimum_start < observation_end and maximum_end >= observation_start
    }
    closure_count = 0
    closure_pre_ops: set[str] = set()
    closure_post_ops: set[str] = set()
    with trace_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row["traceID"]) not in intersecting_trace_ids:
                continue
            closure_count += 1
            end_time = int(row["startTime"]) + int(row["duration"])
            if end_time < anchor_us:
                closure_pre_ops.add(str(row["operationName"]))
            else:
                closure_post_ops.add(str(row["operationName"]))
    return {
        "case_id": case_id,
        "canonical_trace_count": canonical_count,
        "canonical_pre_operation_count": len(pre_ops),
        "canonical_post_operation_count": len(post_ops),
        "canonical_unseen_post_operation_count": len(post_ops - pre_ops),
        "canonical_operation_digest": canonical_payload_digest({
            "pre": sorted(pre_ops), "post": sorted(post_ops)
        }),
        "closure_extra_span_count": int(max(0, closure_count - canonical_count)),
        "closure_pre_operation_count": len(closure_pre_ops),
        "closure_post_operation_count": len(closure_post_ops),
        "closure_unseen_post_operation_count": len(closure_post_ops - closure_pre_ops),
        "closure_operation_digest": canonical_payload_digest({
            "pre": sorted(closure_pre_ops), "post": sorted(closure_post_ops)
        }),
        "unseen_post_operations_persist": bool((closure_post_ops - closure_pre_ops)),
    }


def diagnose_operation_sets(root: Path) -> dict[str, Any]:
    """Compare the opaque TT KeyError set and audit trace closure semantics."""

    from src.baseline_eval.confirmatory import record_path

    failures: dict[str, dict[str, Any]] = {}
    for method in ("MicroRank", "TraceRCA"):
        attempt = V1_DIAGNOSTIC_ATTEMPTS[method]
        rows = []
        for case_id in expected_case_ids(root, "re2tt"):
            path = record_path(root, method, attempt, "re2tt", case_id)
            if not path.is_file():
                continue
            record = read_json(path)
            if record.get("terminal_status") == "METHOD_FAILURE":
                rows.append({"case_id": case_id, "error_type": record.get("error_type")})
        failures[method] = {
            "attempt_id": attempt,
            "failure_case_ids": sorted(row["case_id"] for row in rows),
            "failure_count": len(rows),
            "error_types": dict(Counter(row["error_type"] for row in rows)),
            "failure_set_digest": canonical_payload_digest(sorted(row["case_id"] for row in rows)),
        }
    common_ids = sorted(
        set(failures["MicroRank"]["failure_case_ids"])
        & set(failures["TraceRCA"]["failure_case_ids"])
    )
    op_rows = [_trace_operation_sets(root, "re2tt", case_id) for case_id in common_ids]
    return {
        "schema_version": "rca_baseline_rescue_operation_diagnostic_v2",
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "failure_sets_equal": failures["MicroRank"]["failure_case_ids"] == failures["TraceRCA"]["failure_case_ids"],
        "common_failure_case_ids": common_ids,
        "failures": failures,
        "operation_set_rows": op_rows,
        "trace_closure_adopted": V2_TRACE_CLOSURE_ADOPTED,
        "extended_normal_history_adopted": V2_EXTENDED_NORMAL_HISTORY_ADOPTED,
        "decision": "RETAIN_NATIVE_TRACE_AND_NORMAL_SLO_SEMANTICS; PRESERVE_LEGITIMATE_KEYERROR_METHOD_FAILURE",
        "labels_joined": False,
    }


def deterministic_case_subset(root: Path, cases_per_dataset: int) -> tuple[tuple[str, str], ...]:
    if isinstance(cases_per_dataset, bool) or cases_per_dataset < 1:
        raise SequenceError("determinism preflight subset size must be positive")
    selected: list[tuple[str, str]] = []
    for dataset in DATASET_ORDER:
        ids = sorted(
            expected_case_ids(root, dataset),
            key=lambda case_id: hashlib.sha256(case_id.encode("utf-8")).hexdigest(),
        )
        selected.extend((dataset, case_id) for case_id in ids[:cases_per_dataset])
    return tuple(selected)


def assert_determinism_equal(
    baseline: Mapping[tuple[str, str], Mapping[str, Any]],
    candidate: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    baseline_workers: int,
    candidate_workers: int,
) -> None:
    """Fail closed when worker-count changes alter status or output digests."""

    if set(baseline) != set(candidate):
        raise PreflightError(
            f"determinism case coverage differs between workers={baseline_workers} and workers={candidate_workers}"
        )
    fields = ("status", "native_output_digest", "adapted_output_digest")
    for case in sorted(baseline):
        left = {field: baseline[case].get(field) for field in fields}
        right = {field: candidate[case].get(field) for field in fields}
        if left != right:
            raise PreflightError(
                f"determinism mismatch for opaque case {case[1]} at workers={candidate_workers}"
            )


def _run_determinism_group(
    *,
    root: Path,
    method: str,
    attempt: Mapping[str, Any],
    requested_workers: int,
    cases: Sequence[tuple[str, str]],
    python: Path,
    env: Mapping[str, str],
    available: int | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Run only opaque preflight cases in a scratch output directory."""

    available = available_cpu_count() if available is None else max(1, int(available))
    actual = min(requested_workers, available)
    # Keep idle slots in the preflight so workers=20 actually exercises the
    # requested scheduler configuration even when the opaque subset is small.
    shards = tuple(tuple(cases[index::actual]) for index in range(actual))
    results: dict[tuple[str, str], dict[str, Any]] = {}
    result_lock = threading.Lock()
    servers = [_start_v2_server(root, python, method, env) for _ in shards]
    scratch = tempfile.TemporaryDirectory(prefix=f"ada-rca-rescue-v2-{method.lower()}-")
    stop_event = threading.Event()

    def run(slot: int, shard: Sequence[tuple[str, str]]) -> None:
        server = servers[slot]
        if server.stdin is None:
            raise RescueV2Error("V2 determinism server stdin is unavailable")
        try:
            for dataset, case_id in shard:
                if stop_event.is_set():
                    return
                output = Path(scratch.name) / f"{dataset}-{case_id}.json"
                request = {
                    "command": "case",
                    "execution_profile": "v2",
                    "record_protocol_version": V2_PROTOCOL_VERSION,
                    "record_protocol_digest": V2_PROTOCOL_DIGEST,
                    "method": method,
                    "dataset": dataset,
                    "case_id": case_id,
                    "attempt_id": "determinism-preflight-v2",
                    "environment_digest": attempt["environment_digest"],
                    "input_manifest_digest": attempt["input_manifest_digest"],
                    "candidate_registry_digest": attempt["candidate_registry_digests"][dataset],
                    "execution_commit": attempt["execution_commit"],
                    "execution_worker_count": actual,
                    "execution_worker_slot": slot,
                    "worker_id": f"determinism-{requested_workers}-{slot}",
                    "requested_worker_count": requested_workers,
                    "available_cpu_count": available,
                    "native_module_digest": attempt["native_module_digest"],
                    "source_record_digests": _v2_source_record_digests(
                        root, method, dataset, case_id
                    ),
                    "output": str(output),
                }
                server.stdin.write(json.dumps(request, sort_keys=True) + "\n")
                server.stdin.flush()
                started = _read_server_json(
                    server,
                    heartbeat=None,
                    heartbeat_key="",
                    state={},
                )
                if started.get("status") != "STARTED":
                    raise RescueV2Error("determinism preflight STARTED response is invalid")
                response = _read_server_json(
                    server,
                    heartbeat=None,
                    heartbeat_key="",
                    state={},
                )
                if response.get("status") not in {"RECORDED", "PROCESS_CRASH/OOM"} or not output.is_file():
                    raise RescueV2Error("determinism preflight terminal response is invalid")
                row = read_json(output)
                with result_lock:
                    results[(dataset, case_id)] = {
                        "status": row.get("terminal_status"),
                        "native_output_digest": row.get("native_output_digest"),
                        "adapted_output_digest": row.get("adapted_output_digest"),
                        "elapsed_seconds": row.get("elapsed_seconds"),
                        "worker_count": actual,
                    }
            _stop_v2_server(server)
        except BaseException:
            stop_event.set()
            raise
        finally:
            _terminate_v2_server(server)

    pool = ThreadPoolExecutor(max_workers=len(shards), thread_name_prefix="rescue-v2-determinism")
    futures = [pool.submit(run, slot, shard) for slot, shard in enumerate(shards)]
    try:
        for future in futures:
            future.result()
    except BaseException:
        stop_event.set()
        for server in servers:
            _terminate_v2_server(server)
        raise
    finally:
        pool.shutdown(wait=not stop_event.is_set(), cancel_futures=True)
        scratch.cleanup()
    if set(results) != set(cases):
        raise RescueV2Error("determinism preflight did not cover its opaque subset")
    return results


def run_determinism_preflight(
    root: Path,
    method: str,
    *,
    python: Path,
    cases_per_dataset: int = 5,
    requested_workers: Sequence[int] = (1, 10, 20),
) -> dict[str, Any]:
    """Check status/native/adapted digests at worker counts 1/10/20."""

    _require_v2_method(method)
    requested_workers = tuple(requested_workers)
    if not requested_workers or any(value not in V2_ALLOWED_WORKERS for value in requested_workers):
        raise SequenceError(f"determinism worker counts must be selected from {V2_ALLOWED_WORKERS}")
    global_preflight(root)
    verify_v2_protocol(root)
    environment = verify_v2_environment(root, method)
    python = _python_path(python)
    if python != _python_path(Path(environment["identity"]["python_executable"])):
        raise PreflightError("determinism preflight interpreter differs from frozen environment")
    attempt = {
        "environment_digest": environment["environment_digest"],
        "input_manifest_digest": v2_source_manifest_digest(root),
        "candidate_registry_digests": _v2_candidate_digests(root),
        "execution_commit": git(root, "rev-parse", "HEAD").stdout.strip(),
        "native_module_digest": _v2_native_module_digest(method),
    }
    cases = deterministic_case_subset(root, cases_per_dataset)
    env = resolve_frozen_worker_environment(root, environment)
    available = available_cpu_count()
    runs: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for requested in requested_workers:
        runs[str(requested)] = _run_determinism_group(
            root=root,
            method=method,
            attempt=attempt,
            requested_workers=requested,
            cases=cases,
            python=python,
            env=env,
            available=available,
        )
    baseline = runs[str(requested_workers[0])]
    comparisons = []
    for requested in requested_workers[1:]:
        current = runs[str(requested)]
        assert_determinism_equal(
            baseline,
            current,
            baseline_workers=requested_workers[0],
            candidate_workers=requested,
        )
        comparisons.append({
            "baseline_workers": requested_workers[0],
            "workers": requested,
            "status_and_digest_equal": True,
        })
    return {
        "schema_version": "rca_baseline_rescue_determinism_preflight_v2",
        "method": method,
        "protocol_digest": V2_PROTOCOL_DIGEST,
        "cases_per_dataset": cases_per_dataset,
        "opaque_cases": [{"dataset": dataset, "case_id": case_id} for dataset, case_id in cases],
        "requested_workers": list(requested_workers),
        "actual_workers": {
            str(requested): min(requested, available)
            for requested in requested_workers
        },
        "runs": {
            requested: [
                {"dataset": dataset, "case_id": case_id, **row}
                for (dataset, case_id), row in sorted(result.items())
            ]
            for requested, result in runs.items()
        },
        "comparisons": comparisons,
        "status_and_native_and_adapted_digest_equal": True,
        "labels_joined": False,
    }


def _parse_worker_counts(value: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not values or any(value not in V2_ALLOWED_WORKERS for value in values):
        raise argparse.ArgumentTypeError(
            f"worker counts must be selected from {V2_ALLOWED_WORKERS}"
        )
    return values


def _write_stdout_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("protocol-preflight", "freeze-environment"):
        command = sub.add_parser(name)
        command.add_argument("--method", choices=V2_METHODS, required=True)
        command.add_argument("--python", type=Path, required=True)

    mmbaro = sub.add_parser("diagnose-mmbaro-input")
    mmbaro.add_argument("--case-id", action="append", dest="case_ids")
    mmbaro.add_argument("--output", type=Path)

    operation = sub.add_parser("diagnose-operation-sets")
    operation.add_argument("--output", type=Path)

    deterministic = sub.add_parser("determinism-preflight")
    deterministic.add_argument("--method", choices=V2_METHODS, required=True)
    deterministic.add_argument("--python", type=Path, required=True)
    deterministic.add_argument("--cases-per-dataset", type=int, default=5)
    deterministic.add_argument(
        "--worker-counts", type=_parse_worker_counts, default=(1, 10, 20)
    )

    run = sub.add_parser("run")
    run.add_argument("--method", choices=V2_METHODS, required=True)
    run.add_argument("--python", type=Path, required=True)
    run.add_argument("--attempt-id", required=True)
    run.add_argument("--workers", type=int, choices=V2_ALLOWED_WORKERS, required=True)
    run.add_argument("--datasets", type=parse_dataset_scope, default=DATASET_ORDER)
    run.add_argument("--resume", action="store_true")
    run.add_argument(
        "--resume-policy", choices=("fresh", "missing-only"), default="fresh"
    )
    timeout = run.add_mutually_exclusive_group(required=True)
    timeout.add_argument("--no-timeout", action="store_true")
    timeout.add_argument(
        "--case-timeout",
        choices=("none",),
    )
    run.add_argument("--log-file", type=Path, required=True)
    run.add_argument("--heartbeat-seconds", type=float, default=30.0)

    verify_method = sub.add_parser("verify-method-lock")
    verify_method.add_argument("--method", choices=V2_METHODS, required=True)
    verify_method.add_argument("--attempt-id", required=True)
    verify_method.add_argument("--allow-uncommitted", action="store_true")

    reissue_method = sub.add_parser("reissue-method-lock")
    reissue_method.add_argument("--method", choices=V2_METHODS, required=True)
    reissue_method.add_argument("--attempt-id", required=True)

    sub.add_parser("create-global-lock-v2")
    sub.add_parser("verify-global-lock-v2")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = command_parser().parse_args(argv)
    root = PROJECT_ROOT
    if args.command == "protocol-preflight":
        _write_stdout_json(protocol_preflight_v2(root, args.method, args.python))
        return 0
    if args.command == "freeze-environment":
        print(freeze_v2_environment(root, args.method, args.python))
        return 0
    if args.command == "diagnose-mmbaro-input":
        result = diagnose_mmbaro_input(root, tuple(args.case_ids or V2_MMBARO_RESCUE_CASES))
        if args.output:
            atomic_write_json(args.output, result)
            print(args.output)
        else:
            _write_stdout_json(result)
        return 0
    if args.command == "diagnose-operation-sets":
        result = diagnose_operation_sets(root)
        if args.output:
            atomic_write_json(args.output, result)
            print(args.output)
        else:
            _write_stdout_json(result)
        return 0
    if args.command == "determinism-preflight":
        _write_stdout_json(
            run_determinism_preflight(
                root,
                args.method,
                python=args.python,
                cases_per_dataset=args.cases_per_dataset,
                requested_workers=args.worker_counts,
            )
        )
        return 0
    if args.command == "run":
        result = run_v2(
            root,
            args.method,
            args.attempt_id,
            python=args.python,
            requested_workers=args.workers,
            resume=args.resume,
            resume_policy=args.resume_policy,
            datasets=args.datasets,
            no_timeout=args.no_timeout or args.case_timeout == "none",
            log_file=args.log_file,
            heartbeat_seconds=args.heartbeat_seconds,
        )
        print(result if result is not None else "V2 attempt remains incomplete; records retained for --resume")
        return 0
    if args.command == "verify-method-lock":
        lock = verify_v2_method_lock(
            root,
            args.method,
            require_committed=not args.allow_uncommitted,
        )
        _write_stdout_json({
            "method": args.method,
            "attempt_id": args.attempt_id,
            "lock_digest": lock["lock_digest"],
            "execution_validity": lock["execution_validity"],
        })
        if lock["attempt_id"] != args.attempt_id:
            raise SequenceError("requested attempt ID does not match the method lock")
        if lock["execution_validity"] != "INTEGRITY_VALID":
            return 2
        return 0
    if args.command == "reissue-method-lock":
        print(reissue_v2_method_lock(root, args.method, args.attempt_id))
        return 0
    if args.command == "create-global-lock-v2":
        print(create_v2_global_prediction_lock(root))
        return 0
    if args.command == "verify-global-lock-v2":
        _write_stdout_json(verify_v2_global_prediction_lock(root))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
