"""Frozen orchestration primitives for RCAEval confirmatory execution.

This module owns repository/integrity checks, the input manifest, environment
freezes, method ordering, subprocess isolation, and prediction locks.  It is
strictly label-free: post-lock label joins live in ``evaluation.py``.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import csv
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import select
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence

from src.baseline_eval import (
    CANONICAL_SEED,
    EXPECTED_CASES_PER_DATASET,
    TerminalStatus,
    assert_ada_rca_frozen_unchanged,
    assert_firewall_safe_record,
    audit_frozen_inputs,
)


REQUIRED_BRANCH = "evaluation/rcaeval-baselines"
REQUIRED_STARTING_HEAD = "54b403ff0441c318817818abeda13526652ae1d2"
FROZEN_EVIDENCE_HEAD = "9342e06db91945be2e44703437229ba45b18bda8"
SCIENTIFIC_V1_HEAD = "bed295326e567395e725caa82840a534dcc0b1de"
RCAEVAL_COMMIT = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
RCAEVAL_CLEAN = Path("/home/zhangll24/RCA_project/RCAEval-clean")
PROTOCOL_DIGEST = "aa4f03363e1347a4b4e3c6427fd846be80452f025c3a6d08042ed6f6de0a849e"
PROTOCOL_VERSION = "RCA_BASELINE_PROTOCOL_FREEZE_V1"
CASE_TIMEOUT_SECONDS = 3600
METHOD_ORDER = (
    "BARO",
    "CIRCA",
    "MicroCause",
    "MicroRank",
    "TraceRCA",
    "mmBARO",
    "CausalRCA",
)
DATASET_ORDER = ("re2ob", "re2tt")
DATASET_DISPLAY = {"re2ob": "RE2-OB", "re2tt": "RE2-TT"}

PROTOCOL_ARTIFACT_DIGESTS = {
    "docs/baseline_eval/RCA_BASELINE_PROTOCOL_FREEZE_V1.md": "f16ad5778a4df3c772461e06cb8f9aa59a750298364bf6b97af286466a71202f",
    "docs/baseline_eval/RCA_BASELINE_ADAPTER_SPEC_V1.md": "51ce1d706e6c4108d6b07f6cc43d1fad51e773ed95061ea5f4ccdf022c5d60cd",
    "docs/baseline_eval/RCA_BASELINE_EXECUTION_MATRIX_V1.md": "54357b24dacaabc67108869b65812b32ab2a13557bead51caed0026dea1950a2",
    "docs/baseline_eval/RCA_BASELINE_FAILURE_POLICY_V1.md": "23821ceb6afa18709c01e1c9d94ed08d4b528004a44bb68f4addcc92798982f6",
    "docs/baseline_eval/RCA_BASELINE_PERFORMANCE_FIREWALL_V1.md": "b88439740c1c60066246e9e5be8dd1ad469e49e694ca48364165d365bf4f9408",
    "artifacts/baseline_eval/protocol_freeze_v1.json": PROTOCOL_DIGEST,
    "artifacts/baseline_eval/execution_matrix_v1.json": "40e039e4d0c2d5e8714a7e33ab969d16690a37836319e207a9e8063a8a57fdbb",
    "artifacts/baseline_eval/provenance_v1.json": "031c28ca38349a82cf2aa72193fe83f7c9dd6e50f382dd2eea35a7fa85729f49",
    "artifacts/baseline_eval/timestamp_audit_v1.json": "f9624185245b72cdbfee441397fbee0b94af6e474f439bc6ab9daceeedbc4899",
}

RCAEVAL_SOURCE_DIGESTS = {
    "RCAEval/e2e/baro.py": "ddaae58b4b03453a812c4af33eb0053d803bcb6132453dd37bfa1f5e675b72c4",
    "RCAEval/e2e/circa.py": "2e7c0a4fc860f3401dc1b0b002cb3e3b5d2553d8f79914d942d3041d90984324",
    "RCAEval/e2e/microcause.py": "373bbe69b71a7608889169d8b114ed7234b71f70cb31157d195475c3b276855f",
    "RCAEval/e2e/microrank.py": "717be27e7fbe631c9606b8f917c0fb58484c49d37af5fdcd87bdc054660021f8",
    "RCAEval/e2e/tracerca.py": "1ef420e4430a7ad0379689c1d18eee9dd7fb0d15ac4371f6ff968900a22b0946",
    "RCAEval/e2e/causalrca.py": "74aebfb9f8211db3a48385a73ae577e9673a432d719f859771bbf66dc2a008f0",
}

INPUT_ROLES = {
    "inject_time": "inject_time_path",
    "simple_metrics": "simple_metrics_path",
    "traces": "traces_path",
    "logs": "logs_path",
    "logts": "logts_path",
    "tracets_err": "trace_error_path",
    "tracets_lat": "trace_latency_path",
}

EXECUTION_ROOT_RELATIVE = Path("artifacts/baseline_eval/execution_v1")
INPUT_MANIFEST_RELATIVE = EXECUTION_ROOT_RELATIVE / "input_manifest_v1.json"
GLOBAL_LOCK_RELATIVE = EXECUTION_ROOT_RELATIVE / "prediction_lock_v1.json"
PROCESS_LOCK_PATH = Path("/tmp/ada_rca_rcaeval_confirmatory_execution.lock")

FIXED_WORKER_ENV = {
    "PYTHONHASHSEED": str(CANONICAL_SEED),
    "PYTHONDONTWRITEBYTECODE": "1",
    "CUDA_VISIBLE_DEVICES": "",
    "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


class ConfirmatoryError(RuntimeError):
    """The frozen B2 execution contract would be violated."""


class PreflightError(ConfirmatoryError):
    """A global or method-level preflight failed."""


class SequenceError(ConfirmatoryError):
    """A method attempted to run outside the frozen sequence."""


class FrameworkError(ConfirmatoryError):
    """The execution framework failed outside a baseline case outcome."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def canonical_payload_digest(payload: Any) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args), cwd=root, check=check, text=True, capture_output=True
    )


def require_clean_git(root: Path) -> None:
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all").stdout
    if status:
        raise PreflightError("Ada-RCA worktree must be clean before this transition")


def require_committed_file(root: Path, relative: Path) -> None:
    rel = relative.as_posix()
    if not (root / relative).is_file():
        raise PreflightError(f"required artifact is missing: {rel}")
    exists = git(root, "cat-file", "-e", f"HEAD:{rel}", check=False)
    if exists.returncode != 0:
        raise PreflightError(f"required artifact is not committed: {rel}")
    committed = git(root, "show", f"HEAD:{rel}").stdout.encode("utf-8")
    if committed != (root / relative).read_bytes():
        raise PreflightError(f"required artifact differs from committed bytes: {rel}")


def verify_rcaeval_clean() -> dict[str, Any]:
    head = git(RCAEVAL_CLEAN, "rev-parse", "HEAD").stdout.strip()
    status = git(RCAEVAL_CLEAN, "status", "--porcelain=v1", "--untracked-files=all").stdout
    if head != RCAEVAL_COMMIT:
        raise PreflightError(f"RCAEval-clean HEAD mismatch: {head}")
    if status:
        raise PreflightError("RCAEval-clean is dirty")
    source_digests: dict[str, str] = {}
    for relative, expected in RCAEVAL_SOURCE_DIGESTS.items():
        observed = sha256_file(RCAEVAL_CLEAN / relative)
        if observed != expected:
            raise PreflightError(f"frozen RCAEval source digest mismatch: {relative}")
        source_digests[relative] = observed
    return {"head": head, "clean": True, "source_digests": source_digests}


def protocol_bundle_digest(root: Path) -> str:
    rows = [f"{path}\t{digest}\n" for path, digest in sorted(PROTOCOL_ARTIFACT_DIGESTS.items())]
    return sha256_bytes("".join(rows).encode("utf-8"))


def verify_protocol_artifacts(root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in PROTOCOL_ARTIFACT_DIGESTS.items():
        digest = sha256_file(root / relative)
        if digest != expected:
            raise PreflightError(f"B0/B1 protocol digest mismatch: {relative}")
        observed[relative] = digest
    return observed


def verify_frozen_inputs(root: Path) -> dict[str, dict[str, Any]]:
    audit = audit_frozen_inputs(root)
    for dataset in DATASET_ORDER:
        row = audit[dataset]
        required_true = (
            "case_ids_aligned",
            "anchors_match_sources",
            "registry_identical_across_cases",
            "roots_in_registry",
        )
        if row["case_count"] != EXPECTED_CASES_PER_DATASET or row["unique_case_count"] != EXPECTED_CASES_PER_DATASET:
            raise PreflightError(f"{dataset} canonical denominator differs from 90")
        if not all(row[field] for field in required_true):
            raise PreflightError(f"{dataset} frozen identity audit failed")
    return audit


def global_preflight(root: Path, *, require_exact_head: bool = False) -> dict[str, Any]:
    branch = git(root, "branch", "--show-current").stdout.strip()
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    if branch != REQUIRED_BRANCH:
        raise PreflightError(f"required branch is {REQUIRED_BRANCH}, observed {branch}")
    if require_exact_head and head != REQUIRED_STARTING_HEAD:
        raise PreflightError(f"required starting HEAD is {REQUIRED_STARTING_HEAD}, observed {head}")
    ancestor = git(root, "merge-base", "--is-ancestor", REQUIRED_STARTING_HEAD, head, check=False)
    if ancestor.returncode != 0:
        raise PreflightError("current HEAD is not descended from the required starting HEAD")
    require_clean_git(root)
    protocol = verify_protocol_artifacts(root)
    rcaeval = verify_rcaeval_clean()
    frozen_inputs = verify_frozen_inputs(root)
    assert_ada_rca_frozen_unchanged(root)
    return {
        "branch": branch,
        "head": head,
        "starting_head": REQUIRED_STARTING_HEAD,
        "protocol_artifacts": protocol,
        "protocol_bundle_digest": protocol_bundle_digest(root),
        "rcaeval": rcaeval,
        "frozen_inputs": frozen_inputs,
        "ada_rca_frozen_paths_unchanged": True,
    }


@contextmanager
def exclusive_execution_lock(path: Path = PROCESS_LOCK_PATH) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SequenceError("another baseline execution process is active") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def environment_relative(method: str) -> Path:
    require_method(method)
    return EXECUTION_ROOT_RELATIVE / "environments" / f"{method.lower()}.json"


def method_lock_relative(method: str) -> Path:
    require_method(method)
    return EXECUTION_ROOT_RELATIVE / "locks" / f"{method.lower()}_prediction_lock.json"


def method_records_relative(method: str, attempt_id: str, dataset: str) -> Path:
    require_method(method)
    require_attempt_id(attempt_id)
    require_dataset(dataset)
    return EXECUTION_ROOT_RELATIVE / "records" / method.lower() / attempt_id / dataset


def require_method(method: str) -> None:
    if method not in METHOD_ORDER:
        raise SequenceError(f"method is not in the frozen authorized order: {method}")


def require_dataset(dataset: str) -> None:
    if dataset not in DATASET_ORDER:
        raise ConfirmatoryError(f"unsupported dataset: {dataset}")


def require_attempt_id(attempt_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", attempt_id):
        raise ConfirmatoryError("attempt ID must be an opaque safe slug")


def prior_method(method: str) -> str | None:
    require_method(method)
    index = METHOD_ORDER.index(method)
    return METHOD_ORDER[index - 1] if index else None


def assert_method_sequence_ready(root: Path, method: str, *, require_current_absent: bool = True) -> None:
    require_method(method)
    previous = prior_method(method)
    if previous is not None:
        require_committed_file(root, method_lock_relative(previous))
        previous_lock = read_json(root / method_lock_relative(previous))
        if previous_lock["method"] != previous or previous_lock["disposition"] not in {
            "EXECUTION_COMPLETE",
            "ENVIRONMENT_BLOCKED",
            "PREEXECUTION_BLOCKED",
        }:
            raise SequenceError(f"previous method {previous} has no valid terminal lock")
    current_path = root / method_lock_relative(method)
    if require_current_absent and current_path.exists():
        raise SequenceError(f"{method} already has a method-level lock")
    for later in METHOD_ORDER[METHOD_ORDER.index(method) + 1 :]:
        if (root / method_lock_relative(later)).exists():
            raise SequenceError(f"later method lock exists before {method}: {later}")


def _manifest_record(dataset: str, case: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    if case["case_id"] != source["case_id"]:
        raise PreflightError(f"case/source identity mismatch in {dataset}")
    sources: list[dict[str, Any]] = []
    for role, source_key in INPUT_ROLES.items():
        path = Path(source[source_key])
        if not path.is_file():
            raise PreflightError(f"missing telemetry for {dataset} {case['case_id']} role={role}")
        sources.append({
            "logical_source_role": role,
            "byte_size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {"case_id": case["case_id"], "dataset": dataset, "sources": sources}


def build_input_manifest(root: Path) -> dict[str, Any]:
    """Hash every file that any authorized method receives or resolves.

    Source paths stay confined to this trusted resolver and are not serialized.
    ``logs`` is included even though mmBARO only binds (and does not inspect)
    that native payload key.
    """

    global_preflight(root)
    cases: list[dict[str, Any]] = []
    for dataset in DATASET_ORDER:
        bundle = root / "artifacts" / "source" / dataset
        inputs = read_jsonl(bundle / "inputs.jsonl")
        sources = read_jsonl(bundle / "sources.jsonl")
        for case, source in zip(inputs, sources):
            cases.append(_manifest_record(dataset, case, source))
    payload = {
        "schema_version": "rca_baseline_input_manifest_v1",
        "protocol_version": PROTOCOL_VERSION,
        "ada_rca_starting_commit": REQUIRED_STARTING_HEAD,
        "rcaeval_commit": RCAEVAL_COMMIT,
        "protocol_digest": PROTOCOL_DIGEST,
        "datasets": list(DATASET_ORDER),
        "case_count": len(cases),
        "source_record_count": sum(len(row["sources"]) for row in cases),
        "logical_source_roles": list(INPUT_ROLES),
        "contains_root_or_fault_metadata": False,
        "cases": cases,
    }
    assert_firewall_safe_record(payload)
    return payload


def write_input_manifest(root: Path) -> Path:
    path = root / INPUT_MANIFEST_RELATIVE
    if path.exists():
        raise PreflightError("input manifest already exists; frozen inputs are not regenerated")
    atomic_write_json(path, build_input_manifest(root))
    return path


def fixed_worker_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(FIXED_WORKER_ENV)
    env["PYTHONPATH"] = os.pathsep.join((str(RCAEVAL_CLEAN), str(root)))
    return env


def _python_json(python: Path, code: str, root: Path) -> Any:
    completed = subprocess.run(
        (str(python), "-c", code),
        cwd=root,
        env=fixed_worker_environment(root),
        check=False,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if completed.returncode != 0:
        raise PreflightError(f"environment inspection failed with exit {completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PreflightError("environment inspection did not return JSON") from exc


def collect_environment_identity(root: Path, python: Path) -> dict[str, Any]:
    python = python.expanduser()
    if not python.is_absolute():
        python = root / python
    python = Path(os.path.abspath(python))
    if not python.is_file():
        raise PreflightError(f"Python executable does not exist: {python}")
    code = r'''
import importlib.metadata, json, os, platform, sys
packages = sorted(
    ({"name": d.metadata.get("Name", d.name), "version": d.version} for d in importlib.metadata.distributions()),
    key=lambda row: (row["name"].lower(), row["version"]),
)
print(json.dumps({
    "executable": os.path.realpath(sys.executable),
    "python_version": platform.python_version(),
    "python_implementation": platform.python_implementation(),
    "packages": packages,
}, sort_keys=True))
'''
    inspected = _python_json(python, code, root)
    dependency_manifest_digest = canonical_payload_digest(inspected["packages"])
    identity = {
        "python_executable": str(python),
        "runtime_python_executable": inspected["executable"],
        "python_version": inspected["python_version"],
        "python_implementation": inspected["python_implementation"],
        "environment_path": str(python.parent.parent),
        "environment_type": "venv" if (python.parent.parent / "pyvenv.cfg").is_file() else "python-environment",
        "packages": inspected["packages"],
        "dependency_manifest_digest": dependency_manifest_digest,
        "os": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "worker_environment": {**FIXED_WORKER_ENV, "PYTHONPATH": f"{RCAEVAL_CLEAN}{os.pathsep}{root}"},
        "rcaeval_commit": RCAEVAL_COMMIT,
        "rcaeval_source_digests": RCAEVAL_SOURCE_DIGESTS,
    }
    return identity


def schema_preflight(root: Path, dataset: str) -> dict[str, Any]:
    require_dataset(dataset)
    input_rows = read_jsonl(root / "artifacts" / "source" / dataset / "inputs.jsonl")
    source_rows = read_jsonl(root / "artifacts" / "source" / dataset / "sources.jsonl")
    required_metric = {"time"}
    required_trace = {
        "serviceName",
        "methodName",
        "operationName",
        "startTime",
        "startTimeMillis",
        "duration",
    }
    required_derived = {"time"}
    metric_header: set[str] | None = None
    trace_header: set[str] | None = None
    derived_headers: dict[str, set[str]] = {}
    for case, source in zip(input_rows, source_rows):
        anchor = int(case["anchor_time"])
        if int(Path(source["inject_time_path"]).read_text(encoding="utf-8").strip()) != anchor:
            raise PreflightError(f"{dataset} inject-time identity mismatch")
        with Path(source["simple_metrics_path"]).open(encoding="utf-8", newline="") as handle:
            header = set(next(csv.reader(handle)))
        if not required_metric.issubset(header):
            raise PreflightError(f"{dataset} simple metric schema mismatch")
        metric_header = header if metric_header is None else metric_header
        with Path(source["traces_path"]).open(encoding="utf-8", newline="") as handle:
            header = set(next(csv.reader(handle)))
        if not required_trace.issubset(header):
            raise PreflightError(f"{dataset} raw trace schema mismatch")
        trace_header = header if trace_header is None else trace_header
        for role, key in (("logts", "logts_path"), ("tracets_err", "trace_error_path"), ("tracets_lat", "trace_latency_path")):
            with Path(source[key]).open(encoding="utf-8", newline="") as handle:
                header = set(next(csv.reader(handle)))
            if not required_derived.issubset(header):
                raise PreflightError(f"{dataset} {role} schema mismatch")
            derived_headers.setdefault(role, header)
    return {
        "dataset": dataset,
        "case_count": len(input_rows),
        "metric_column_count": len(metric_header or ()),
        "trace_column_count": len(trace_header or ()),
        "derived_column_counts": {role: len(header) for role, header in sorted(derived_headers.items())},
        "status": "PASS",
    }


def _run_synthetic_preflight(root: Path, python: Path, method: str) -> dict[str, Any]:
    completed = subprocess.run(
        (str(python), "-m", "src.baseline_eval.worker", "preflight", "--method", method),
        cwd=root,
        env=fixed_worker_environment(root),
        check=False,
        text=True,
        capture_output=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise PreflightError(f"{method} synthetic preflight failed with exit {completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{method} synthetic preflight returned invalid JSON") from exc
    if result.get("status") != "PASS" or result.get("method") != method:
        raise PreflightError(f"{method} synthetic preflight did not pass")
    if result.get("module_paths_within_clean_checkout") is not True:
        raise PreflightError(f"{method} synthetic preflight imported outside RCAEval-clean")
    fingerprint = result.get("fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise PreflightError(f"{method} synthetic preflight returned an invalid fingerprint")
    return result


def _environment_preflight_details(
    root: Path, method: str, python: Path
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Resolve one environment with synthetic data only and without writing artifacts."""

    identity = collect_environment_identity(root, python)
    first = _run_synthetic_preflight(root, python, method)
    second = _run_synthetic_preflight(root, python, method)
    if first["fingerprint"] != second["fingerprint"]:
        raise PreflightError(f"{method} synthetic executions are not deterministic")
    schema = [schema_preflight(root, dataset) for dataset in DATASET_ORDER]
    return identity, first, schema


def preflight_environment(root: Path, method: str, python: Path) -> dict[str, Any]:
    """Read-only environment resolution for a current or later baseline.

    This deliberately does not enforce the method execution sequence and does
    not create an environment manifest. It is safe to use while an earlier
    method is incomplete, but it never authorizes a real case run.
    """

    require_method(method)
    verify_protocol_artifacts(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    require_committed_file(root, INPUT_MANIFEST_RELATIVE)
    identity, synthetic, schema = _environment_preflight_details(root, method, python)
    return {
        "schema_version": "rca_baseline_environment_preflight_v1",
        "method": method,
        "datasets": list(DATASET_ORDER),
        "environment": {
            "python_executable": identity["python_executable"],
            "runtime_python_executable": identity["runtime_python_executable"],
            "python_version": identity["python_version"],
            "python_implementation": identity["python_implementation"],
            "environment_path": identity["environment_path"],
            "environment_type": identity["environment_type"],
            "dependency_manifest_digest": identity["dependency_manifest_digest"],
        },
        "protocol_digest": PROTOCOL_DIGEST,
        "input_manifest_digest": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "synthetic_preflight": {
            "status": "PASS",
            "fingerprint": synthetic["fingerprint"],
            "native_output_kind": synthetic["native_output_kind"],
            "runs": 2,
        },
        "schema_preflight": schema,
        "writes_artifacts": False,
        "authorizes_real_execution": False,
    }


def freeze_environment(root: Path, method: str, python: Path) -> Path:
    require_clean_git(root)
    verify_protocol_artifacts(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    assert_method_sequence_ready(root, method)
    require_committed_file(root, INPUT_MANIFEST_RELATIVE)
    path = root / environment_relative(method)
    if path.exists():
        raise PreflightError(f"environment freeze already exists for {method}")
    identity, first, schema = _environment_preflight_details(root, method, python)
    stable = {
        "schema_version": "rca_baseline_environment_v1",
        "method": method,
        "datasets": list(DATASET_ORDER),
        "identity": identity,
        "protocol_digest": PROTOCOL_DIGEST,
        "protocol_bundle_digest": protocol_bundle_digest(root),
        "input_manifest_digest": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        "ada_rca_starting_commit": REQUIRED_STARTING_HEAD,
        "execution_harness_commit": git(root, "rev-parse", "HEAD").stdout.strip(),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "synthetic_preflight": {
            "status": "PASS",
            "fingerprint": first["fingerprint"],
            "native_output_kind": first["native_output_kind"],
            "runs": 2,
        },
        "schema_preflight": schema,
        "deterministic_controls": {
            "canonical_seed": CANONICAL_SEED,
            "python_hash_seed": CANONICAL_SEED,
            "cpu_only": method == "CausalRCA",
            "torch_deterministic_algorithms": method == "CausalRCA",
        },
    }
    payload = {**stable, "environment_digest": canonical_payload_digest(stable), "frozen_at": utc_now()}
    atomic_write_json(path, payload)
    return path


def verify_environment_current(root: Path, method: str) -> dict[str, Any]:
    path = root / environment_relative(method)
    manifest = read_json(path)
    stored_digest = manifest["environment_digest"]
    stable = {key: value for key, value in manifest.items() if key not in {"environment_digest", "frozen_at"}}
    if canonical_payload_digest(stable) != stored_digest:
        raise PreflightError(f"{method} environment manifest digest is invalid")
    python = Path(manifest["identity"]["python_executable"])
    current = collect_environment_identity(root, python)
    if current != manifest["identity"]:
        raise PreflightError(f"{method} frozen environment has changed")
    return manifest


def expected_case_ids(root: Path, dataset: str) -> tuple[str, ...]:
    require_dataset(dataset)
    rows = read_jsonl(root / "artifacts" / "source" / dataset / "inputs.jsonl")
    ids = tuple(row["case_id"] for row in rows)
    if len(ids) != EXPECTED_CASES_PER_DATASET or len(set(ids)) != len(ids):
        raise PreflightError(f"{dataset} expected IDs are not exactly 90 unique cases")
    return ids


def record_path(root: Path, method: str, attempt_id: str, dataset: str, case_id: str) -> Path:
    if not re.fullmatch(r"re2(?:ob|tt)-[0-9a-f]{16}", case_id):
        raise ConfirmatoryError("case ID is not a frozen opaque identifier")
    return root / method_records_relative(method, attempt_id, dataset) / f"{case_id}.json"


def validate_terminal_record(
    payload: Mapping[str, Any], *, method: str, dataset: str, case_id: str, environment_digest: str,
    input_manifest_digest: str,
) -> None:
    assert_firewall_safe_record(payload)
    expected = {
        "method": method,
        "dataset": dataset,
        "case_id": case_id,
        "environment_digest": environment_digest,
        "input_manifest_digest": input_manifest_digest,
        "protocol_digest": PROTOCOL_DIGEST,
        "rcaeval_commit": RCAEVAL_COMMIT,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise FrameworkError(f"terminal record provenance mismatch: {key}")
    try:
        status = TerminalStatus(payload["terminal_status"])
    except (KeyError, ValueError) as exc:
        raise FrameworkError("terminal record has an invalid status") from exc
    native = payload.get("native_ranking", [])
    adapted = payload.get("adapted_ranking", [])
    if status is TerminalStatus.SUCCESS:
        if not native or not adapted or len(adapted) != len(set(adapted)):
            raise FrameworkError("SUCCESS record has invalid rankings")
    elif native or adapted:
        raise FrameworkError("failure record contains a fallback ranking")


def format_case_status(payload: Mapping[str, Any]) -> str:
    return (
        f"{payload['case_id']} {payload['terminal_status']} "
        f"native_len={payload['native_output_length']} "
        f"adapted_len={payload['adapted_output_length']} "
        f"wall={float(payload['wall_time_seconds']):.3f}s"
    )


def _timeout_record(
    root: Path, method: str, dataset: str, case_id: str, attempt_id: str,
    environment_digest: str, input_manifest_digest: str, candidate_registry_digest: str,
    execution_commit: str, start: str, wall_time: float,
) -> dict[str, Any]:
    payload = {
        "schema_version": "rca_baseline_case_record_v1",
        "protocol_version": PROTOCOL_VERSION,
        "protocol_digest": PROTOCOL_DIGEST,
        "method": method,
        "dataset": dataset,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "ada_rca_commit": REQUIRED_STARTING_HEAD,
        "execution_commit": execution_commit,
        "rcaeval_commit": RCAEVAL_COMMIT,
        "environment_digest": environment_digest,
        "input_manifest_digest": input_manifest_digest,
        "candidate_registry_digest": candidate_registry_digest,
        "seed_state": {"canonical_seed": CANONICAL_SEED, "python_hash_seed": CANONICAL_SEED},
        "timeout_seconds": CASE_TIMEOUT_SECONDS,
        "start_timestamp": start,
        "end_timestamp": utc_now(),
        "wall_time_seconds": wall_time,
        "window_semantics": "[t0-600s,t0+600s)",
        "native_output_type": "NONE",
        "native_output_length": 0,
        "adapted_output_length": 0,
        "native_ranking": [],
        "adapted_ranking": [],
        "native_output_digest": None,
        "duplicate_native_items": [],
        "duplicate_count": 0,
        "unmapped_native_items": [],
        "unmapped_count": 0,
        "missing_candidate_reasons": {"EXECUTION_FAILURE": "ALL_LEGAL_CANDIDATES"},
        "terminal_status": TerminalStatus.TIMEOUT.value,
        "error_type": "TIMEOUT",
        "sanitized_error": f"worker exceeded frozen {CASE_TIMEOUT_SECONDS}-second deadline",
        "diagnostic_digest": None,
    }
    assert_firewall_safe_record(payload)
    return payload


def validate_attempt_is_new(root: Path, method: str, attempt_id: str) -> None:
    require_attempt_id(attempt_id)
    base = root / EXECUTION_ROOT_RELATIVE / "records" / method.lower() / attempt_id
    if base.exists() and any(base.rglob("*.json")):
        raise SequenceError("a new attempt must begin from case 1 with an empty record directory")


def _load_existing_attempt_records(
    root: Path, method: str, attempt_id: str, environment_digest: str, input_manifest_digest: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for dataset in DATASET_ORDER:
        for case_id in expected_case_ids(root, dataset):
            path = record_path(root, method, attempt_id, dataset, case_id)
            if not path.exists():
                continue
            payload = read_json(path)
            validate_terminal_record(
                payload,
                method=method,
                dataset=dataset,
                case_id=case_id,
                environment_digest=environment_digest,
                input_manifest_digest=input_manifest_digest,
            )
            records[(dataset, case_id)] = payload
    return records


def _candidate_registry_digest(root: Path, dataset: str) -> str:
    return sha256_file(root / "artifacts" / "source" / dataset / "service_registry.json")


def _persist_parent_record(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FrameworkError("refusing to overwrite an existing terminal case record")
    atomic_write_json(path, payload)


def run_method(root: Path, method: str, attempt_id: str, *, resume: bool = False) -> Path:
    require_method(method)
    require_attempt_id(attempt_id)
    require_clean_git(root) if not resume else None
    verify_protocol_artifacts(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    assert_method_sequence_ready(root, method)
    require_committed_file(root, INPUT_MANIFEST_RELATIVE)
    require_committed_file(root, environment_relative(method))
    environment = verify_environment_current(root, method)
    python = Path(environment["identity"]["python_executable"])
    environment_digest = environment["environment_digest"]
    input_manifest_digest = sha256_file(root / INPUT_MANIFEST_RELATIVE)
    execution_commit = git(root, "rev-parse", "HEAD").stdout.strip()
    if resume:
        existing = _load_existing_attempt_records(
            root, method, attempt_id, environment_digest, input_manifest_digest
        )
        if not existing:
            raise SequenceError("resume requested but this attempt has no persisted records")
    else:
        validate_attempt_is_new(root, method, attempt_id)
        existing = {}

    with exclusive_execution_lock():
        server = subprocess.Popen(
            (str(python), "-m", "src.baseline_eval.server", "--method", method),
            cwd=root,
            env=fixed_worker_environment(root),
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            if server.stdin is None or server.stdout is None:
                raise FrameworkError("method server pipes are unavailable")
            ready, _, _ = select.select([server.stdout], [], [], 900)
            if not ready:
                raise FrameworkError("method server did not finish its import preflight within 900 seconds")
            handshake = json.loads(server.stdout.readline())
            if handshake != {"status": "READY", "method": method}:
                raise FrameworkError("method server returned an invalid readiness handshake")
            for dataset in DATASET_ORDER:
                candidate_digest = _candidate_registry_digest(root, dataset)
                for case_id in expected_case_ids(root, dataset):
                    if (dataset, case_id) in existing:
                        continue
                    path = record_path(root, method, attempt_id, dataset, case_id)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    request = {
                        "command": "case",
                        "method": method,
                        "dataset": dataset,
                        "case_id": case_id,
                        "attempt_id": attempt_id,
                        "environment_digest": environment_digest,
                        "input_manifest_digest": input_manifest_digest,
                        "candidate_registry_digest": candidate_digest,
                        "execution_commit": execution_commit,
                        "output": str(path),
                    }
                    start_timestamp = utc_now()
                    start = time.monotonic()
                    server.stdin.write(json.dumps(request, sort_keys=True) + "\n")
                    server.stdin.flush()
                    ready, _, _ = select.select([server.stdout], [], [], CASE_TIMEOUT_SECONDS + 30)
                    if not ready:
                        raise FrameworkError(
                            f"method server failed to enforce the frozen deadline for {case_id}"
                        )
                    response = json.loads(server.stdout.readline())
                    if response.get("case_id") != case_id:
                        raise FrameworkError("method server response case identity mismatch")
                    if response.get("status") == "TIMEOUT":
                        payload = _timeout_record(
                            root, method, dataset, case_id, attempt_id, environment_digest,
                            input_manifest_digest, candidate_digest, execution_commit,
                            start_timestamp, time.monotonic() - start,
                        )
                        _persist_parent_record(path, payload)
                    elif response.get("status") != "RECORDED" or not path.is_file():
                        raise FrameworkError(
                            f"worker framework failure for {case_id}; retain this attempt and start a new attempt"
                        )
                    payload = read_json(path)
                    validate_terminal_record(
                        payload,
                        method=method,
                        dataset=dataset,
                        case_id=case_id,
                        environment_digest=environment_digest,
                        input_manifest_digest=input_manifest_digest,
                    )
                    print(format_case_status(payload), flush=True)
            server.stdin.write(json.dumps({"command": "stop"}) + "\n")
            server.stdin.flush()
            ready, _, _ = select.select([server.stdout], [], [], 30)
            if not ready or json.loads(server.stdout.readline()).get("status") != "STOPPED":
                raise FrameworkError("method server did not stop cleanly")
            if server.wait(timeout=30) != 0:
                raise FrameworkError("method server exited nonzero")
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)

        records = _load_existing_attempt_records(
            root, method, attempt_id, environment_digest, input_manifest_digest
        )
        if len(records) != len(DATASET_ORDER) * EXPECTED_CASES_PER_DATASET:
            raise FrameworkError("method attempt does not contain 180 terminal records")
        verify_environment_current(root, method)
        verify_rcaeval_clean()
        assert_ada_rca_frozen_unchanged(root)
        lock_path = root / method_lock_relative(method)
        if lock_path.exists():
            raise SequenceError(f"method lock already exists for {method}")
        terminal_records: list[dict[str, Any]] = []
        counts: dict[str, dict[str, int]] = {}
        for dataset in DATASET_ORDER:
            dataset_records = [records[(dataset, case_id)] for case_id in expected_case_ids(root, dataset)]
            counter = Counter(row["terminal_status"] for row in dataset_records)
            counts[dataset] = {status.value: counter.get(status.value, 0) for status in TerminalStatus}
            for row in dataset_records:
                path = record_path(root, method, attempt_id, dataset, row["case_id"])
                terminal_records.append({
                    "dataset": dataset,
                    "case_id": row["case_id"],
                    "sha256": sha256_file(path),
                })
        lock = {
            "schema_version": "rca_baseline_method_prediction_lock_v1",
            "method": method,
            "attempt_id": attempt_id,
            "disposition": "EXECUTION_COMPLETE",
            "environment_digest": environment_digest,
            "protocol_digest": PROTOCOL_DIGEST,
            "protocol_bundle_digest": protocol_bundle_digest(root),
            "input_manifest_digest": input_manifest_digest,
            "rcaeval_commit": RCAEVAL_COMMIT,
            "datasets": list(DATASET_ORDER),
            "expected_case_ids": {
                dataset: list(expected_case_ids(root, dataset)) for dataset in DATASET_ORDER
            },
            "terminal_record_digests": terminal_records,
            "record_counts": {dataset: EXPECTED_CASES_PER_DATASET for dataset in DATASET_ORDER},
            "status_counts": counts,
            "contains_evaluation": False,
            "locked_at": utc_now(),
        }
        assert_firewall_safe_record(lock)
        atomic_write_json(lock_path, lock)
        return lock_path


def record_method_block(
    root: Path, method: str, disposition: str, environment_attempts: Sequence[Mapping[str, Any]], cause: str,
) -> Path:
    if disposition not in {"ENVIRONMENT_BLOCKED", "PREEXECUTION_BLOCKED"}:
        raise ConfirmatoryError("invalid method-level block disposition")
    require_clean_git(root)
    assert_method_sequence_ready(root, method)
    lock_path = root / method_lock_relative(method)
    payload = {
        "schema_version": "rca_baseline_method_prediction_lock_v1",
        "method": method,
        "attempt_id": None,
        "disposition": disposition,
        "environment_attempts": list(environment_attempts),
        "technical_cause": cause,
        "source_modification_rejected": True,
        "protocol_digest": PROTOCOL_DIGEST,
        "input_manifest_digest": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "record_counts": {},
        "status_counts": {},
        "contains_evaluation": False,
        "locked_at": utc_now(),
    }
    assert_firewall_safe_record(payload)
    atomic_write_json(lock_path, payload)
    return lock_path


def verify_method_lock(root: Path, method: str, *, require_committed: bool = True) -> dict[str, Any]:
    relative = method_lock_relative(method)
    if require_committed:
        require_committed_file(root, relative)
    lock = read_json(root / relative)
    if lock.get("method") != method or lock.get("protocol_digest") != PROTOCOL_DIGEST:
        raise PreflightError(f"invalid method lock for {method}")
    if lock["disposition"] == "EXECUTION_COMPLETE":
        expected_pairs = {
            (dataset, case_id)
            for dataset in DATASET_ORDER
            for case_id in expected_case_ids(root, dataset)
        }
        observed_pairs: set[tuple[str, str]] = set()
        for row in lock["terminal_record_digests"]:
            pair = (row["dataset"], row["case_id"])
            if pair in observed_pairs:
                raise PreflightError(f"duplicate terminal record in {method} lock")
            observed_pairs.add(pair)
            path = record_path(root, method, lock["attempt_id"], row["dataset"], row["case_id"])
            if sha256_file(path) != row["sha256"]:
                raise PreflightError(f"terminal record digest mismatch in {method} lock")
        if observed_pairs != expected_pairs:
            raise PreflightError(f"{method} lock does not cover both 90-case datasets")
    elif lock["disposition"] not in {"ENVIRONMENT_BLOCKED", "PREEXECUTION_BLOCKED"}:
        raise PreflightError(f"invalid disposition in {method} lock")
    return lock


def create_global_prediction_lock(root: Path) -> Path:
    require_clean_git(root)
    verify_protocol_artifacts(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    require_committed_file(root, INPUT_MANIFEST_RELATIVE)
    path = root / GLOBAL_LOCK_RELATIVE
    if path.exists():
        raise PreflightError("global prediction lock already exists")
    methods = []
    for method in METHOD_ORDER:
        lock = verify_method_lock(root, method, require_committed=True)
        methods.append({
            "method": method,
            "disposition": lock["disposition"],
            "method_lock_path": method_lock_relative(method).as_posix(),
            "method_lock_sha256": sha256_file(root / method_lock_relative(method)),
            "attempt_id": lock.get("attempt_id"),
            "record_counts": lock.get("record_counts", {}),
            "status_counts": lock.get("status_counts", {}),
        })
    payload = {
        "schema_version": "rca_baseline_global_prediction_lock_v1",
        "protocol_version": PROTOCOL_VERSION,
        "protocol_digest": PROTOCOL_DIGEST,
        "protocol_bundle_digest": protocol_bundle_digest(root),
        "input_manifest_digest": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        "ada_rca_starting_commit": REQUIRED_STARTING_HEAD,
        "scientific_v1_reference": SCIENTIFIC_V1_HEAD,
        "evidence_closure_reference": FROZEN_EVIDENCE_HEAD,
        "rcaeval_commit": RCAEVAL_COMMIT,
        "method_order": list(METHOD_ORDER),
        "dataset_order": list(DATASET_ORDER),
        "methods": methods,
        "labels_joined": False,
        "contains_evaluation": False,
        "locked_at": utc_now(),
    }
    assert_firewall_safe_record(payload)
    atomic_write_json(path, payload)
    return path


def verify_global_prediction_lock(root: Path, *, require_committed: bool = True) -> dict[str, Any]:
    if require_committed:
        require_committed_file(root, GLOBAL_LOCK_RELATIVE)
    lock = read_json(root / GLOBAL_LOCK_RELATIVE)
    if lock.get("method_order") != list(METHOD_ORDER) or lock.get("labels_joined") is not False:
        raise PreflightError("global prediction lock is invalid")
    if lock.get("protocol_digest") != PROTOCOL_DIGEST:
        raise PreflightError("global prediction lock protocol mismatch")
    for method in METHOD_ORDER:
        verify_method_lock(root, method, require_committed=True)
    return lock


def command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("global-preflight")
    preflight.add_argument("--require-exact-head", action="store_true")
    environment_preflight = sub.add_parser("preflight-environment")
    environment_preflight.add_argument("--method", choices=METHOD_ORDER, required=True)
    environment_preflight.add_argument("--python", type=Path, required=True)
    sub.add_parser("build-input-manifest")
    freeze = sub.add_parser("freeze-environment")
    freeze.add_argument("--method", choices=METHOD_ORDER, required=True)
    freeze.add_argument("--python", type=Path, required=True)
    run = sub.add_parser("run-method")
    run.add_argument("--method", choices=METHOD_ORDER, required=True)
    run.add_argument("--attempt-id", required=True)
    run.add_argument("--resume", action="store_true")
    sub.add_parser("create-global-lock")
    sub.add_parser("evaluate")
    sub.add_parser("report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = command_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if args.command == "global-preflight":
        result = global_preflight(root, require_exact_head=args.require_exact_head)
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "preflight-environment":
        result = preflight_environment(root, args.method, args.python)
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "build-input-manifest":
        print(write_input_manifest(root).relative_to(root))
    elif args.command == "freeze-environment":
        print(freeze_environment(root, args.method, args.python).relative_to(root))
    elif args.command == "run-method":
        print(run_method(root, args.method, args.attempt_id, resume=args.resume).relative_to(root))
    elif args.command == "create-global-lock":
        print(create_global_prediction_lock(root).relative_to(root))
    elif args.command == "evaluate":
        from src.baseline_eval.evaluation import evaluate_locked_predictions

        print(evaluate_locked_predictions(root).relative_to(root))
    elif args.command == "report":
        from src.baseline_eval.evaluation import write_report

        print(write_report(root).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
