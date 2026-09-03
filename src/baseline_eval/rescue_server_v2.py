"""No-timeout, one-case-at-a-time server for the V2 rescue scheduler.

The server imports one pinned RCAEval callable once, then forks a fresh child
for each opaque case.  A child is never killed for elapsed wall time.  A
non-zero child exit is persisted as ``PROCESS_CRASH/OOM`` so that it cannot be
mistaken for a native method failure.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import multiprocessing
from pathlib import Path
import os
import sys
import time
from typing import Any, Mapping, Sequence

from src.baseline_eval import CANONICAL_SEED, assert_firewall_safe_record
from src.baseline_eval.confirmatory import (
    RCAEVAL_COMMIT,
    REQUIRED_STARTING_HEAD,
    atomic_write_json,
    canonical_payload_digest,
    sha256_file,
    utc_now,
)
from src.baseline_eval.worker import _module_callable, execute_case, _native_module_path


V2_PROCESS_FAILURE_STATUS = "PROCESS_CRASH/OOM"


def _child(request: Mapping[str, Any]) -> None:
    namespace = argparse.Namespace(**request)
    output = Path(namespace.output)
    if output.exists():
        raise RuntimeError("case child refuses to overwrite a terminal record")
    atomic_write_json(output, execute_case(namespace))


def _process_failure_record(request: Mapping[str, Any], start_timestamp: str, elapsed: float) -> dict[str, Any]:
    method = str(request["method"])
    module_path = _native_module_path(method)
    module_digest = request.get("native_module_digest")
    if not isinstance(module_digest, str):
        try:
            module_digest = sha256_file(module_path)
        except OSError:
            module_digest = None
    payload: dict[str, Any] = {
        "schema_version": "rca_baseline_rescue_case_record_v2",
        "protocol_version": request.get("protocol_version", "RCA_BASELINE_RESCUE_PROTOCOL_V2"),
        "protocol_digest": request["protocol_digest"],
        "method": method,
        "dataset": request["dataset"],
        "case_id": request["case_id"],
        "attempt_id": request["attempt_id"],
        "ada_rca_commit": REQUIRED_STARTING_HEAD,
        "execution_commit": request["execution_commit"],
        "execution_worker_count": request["execution_worker_count"],
        "execution_worker_slot": request["execution_worker_slot"],
        "worker_id": request["worker_id"],
        "requested_worker_count": request["requested_worker_count"],
        "available_cpu_count": request["available_cpu_count"],
        "pid": request.get("child_pid"),
        "rcaeval_commit": RCAEVAL_COMMIT,
        "environment_digest": request["environment_digest"],
        "input_manifest_digest": request["input_manifest_digest"],
        "candidate_registry_digest": request["candidate_registry_digest"],
        "source_record_digests": list(request.get("source_record_digests", [])),
        "method_source_digest": module_digest,
        "native_module_digest": module_digest,
        "seed_state": {
            "canonical_seed": CANONICAL_SEED,
            "python_hash_seed": CANONICAL_SEED,
            "numpy_seed": CANONICAL_SEED,
            "torch_seed": CANONICAL_SEED if method == "CausalRCA" else None,
        },
        "timeout_seconds": None,
        "start_timestamp": start_timestamp,
        "finish_timestamp": utc_now(),
        "end_timestamp": utc_now(),
        "elapsed_seconds": elapsed,
        "wall_time_seconds": elapsed,
        "cpu_time_seconds": None,
        "peak_rss_bytes": None,
        "window_semantics": "[t0-600s,t0+600s)",
        "native_output_type": "NONE",
        "native_output_length": 0,
        "adapted_output_length": 0,
        "native_ranking": [],
        "adapted_ranking": [],
        "native_output_digest": None,
        "adapted_output_digest": None,
        "duplicate_native_items": [],
        "duplicate_count": 0,
        "unmapped_native_items": [],
        "unmapped_count": 0,
        "missing_candidate_reasons": {"EXECUTION_FAILURE": "PROCESS_EXIT"},
        "terminal_status": V2_PROCESS_FAILURE_STATUS,
        "error_type": "PROCESS_EXIT_NONZERO",
        "sanitized_error": "case child exited before producing a terminal record",
        "diagnostic_digest": canonical_payload_digest({
            "status": V2_PROCESS_FAILURE_STATUS,
            "error_type": "PROCESS_EXIT_NONZERO",
        }),
        "native_console_digest": None,
        "native_console_character_count": 0,
    }
    if method == "CausalRCA":
        payload.update({
            "protocol_base_digest": request.get("protocol_base_digest"),
            "execution_device": request.get("execution_device"),
            "case_parallelism": request.get("case_parallelism"),
        })
    assert_firewall_safe_record(payload)
    return payload


def serve(method: str) -> int:
    # This import is a preflight only.  Actual calls are still isolated in a
    # fresh fork and execute_case reseeds Python and NumPy in that child.
    _module_callable(method)
    context = multiprocessing.get_context("fork")
    print(json.dumps({"status": "READY", "method": method}), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("command") == "stop":
            print(json.dumps({"status": "STOPPED"}), flush=True)
            return 0
        if request.get("method") != method:
            print(json.dumps({"status": "FRAMEWORK_ERROR", "case_id": request.get("case_id")}), flush=True)
            return 2
        start_timestamp = utc_now()
        start = time.monotonic()
        process = context.Process(target=_child, args=(request,))
        process.start()
        request = {**request, "child_pid": process.pid}
        print(json.dumps({
            "status": "STARTED",
            "case_id": request["case_id"],
            "pid": process.pid,
            "start_timestamp": start_timestamp,
        }), flush=True)
        # Deliberately no timeout argument.  V2's no-timeout policy is
        # structural: elapsed runtime is monitored by the parent scheduler,
        # never used as a kill condition here.
        process.join()
        elapsed = time.monotonic() - start
        output = Path(request["output"])
        if process.exitcode != 0 or not output.is_file():
            if not output.exists():
                atomic_write_json(output, _process_failure_record(request, start_timestamp, elapsed))
            print(json.dumps({
                "status": V2_PROCESS_FAILURE_STATUS,
                "case_id": request["case_id"],
                "pid": process.pid,
            }), flush=True)
            continue
        print(json.dumps({"status": "RECORDED", "case_id": request["case_id"], "pid": process.pid}), flush=True)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--method", required=True)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return serve(args.method)


if __name__ == "__main__":
    raise SystemExit(main())
