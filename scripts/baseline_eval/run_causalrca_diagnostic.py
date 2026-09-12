#!/usr/bin/env python3
"""Human-invoked, non-mutating CausalRCA PageRank diagnostic runner.

This file is prepared for manual use only.  It is intentionally not imported
by the audit generator or its tests, and it writes only to the caller-selected
diagnostic output path.  It does not resume or modify confirmatory records or
prediction locks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.baseline_eval.causalrca_diagnostic import (  # noqa: E402
    PageRankRecorder,
    classify_causalrca_output,
    instrument_pagerank,
)
from src.baseline_eval.confirmatory import (  # noqa: E402
    RCAEVAL_CLEAN,
    atomic_write_json,
    expected_case_ids,
    read_json,
    sha256_file,
)
from src.baseline_eval.rescue_v2 import (  # noqa: E402
    CAUSALRCA_CPU_ATTEMPT_ID,
    CAUSALRCA_CPU_PROTOCOL_DIGEST,
)
from src.baseline_eval.worker import (  # noqa: E402
    _module_callable,
    invoke_predictive_method,
    load_legal_case_input,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an explicitly selected CausalRCA diagnostic case; never a confirmatory record."
    )
    parser.add_argument("--dataset", choices=("re2ob", "re2tt"), required=True)
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--case-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _case_ids(args: argparse.Namespace) -> list[str]:
    values = list(args.case_ids or [])
    if args.case_file is not None:
        payload = json.loads(args.case_file.read_text(encoding="utf-8"))
        values.extend(
            row["case_id"]
            for row in payload.get("case_selection", [])
            if row.get("dataset") == args.dataset
        )
    expected = set(expected_case_ids(PROJECT_ROOT, args.dataset))
    if not values or len(values) != len(set(values)) or not set(values).issubset(expected):
        raise SystemExit("provide one or more unique frozen --case-id values for the selected dataset")
    return values


def run_case(dataset: str, case_id: str) -> dict[str, Any]:
    import sknetwork.ranking

    telemetry, anchor, candidates, sli, _observed, _provenance = load_legal_case_input(
        "CausalRCA", dataset, case_id, drop_nonfinite_time=True
    )
    recorder = PageRankRecorder()
    _function, _module_path = _module_callable("CausalRCA")
    with instrument_pagerank(sknetwork.ranking.PageRank, recorder):
        output, ranks, _module_path, _sink = invoke_predictive_method(
            "CausalRCA", dataset, case_id, anchor, telemetry, candidates, sli
        )
    events = recorder.events
    exceptions = [event for event in events if event["event"] == "pagerank_exception"]
    classification = classify_causalrca_output(
        returned_ranks=output.get("ranks", ranks),
        node_names=output.get("node_names", []),
        adjacency=output.get("adj", []),
        pagerank_exception_observed=bool(exceptions),
    )
    adjacency = output.get("adj", [])
    try:
        adjacency_shape = list(getattr(adjacency, "shape", ()))
        adjacency_nonzero = int((adjacency != 0).sum()) if adjacency_shape else None
    except (AttributeError, TypeError, ValueError):
        adjacency_shape = None
        adjacency_nonzero = None
    return {
        "dataset": dataset,
        "case_id": case_id,
        "attempt_id": CAUSALRCA_CPU_ATTEMPT_ID,
        "protocol_digest": CAUSALRCA_CPU_PROTOCOL_DIGEST,
        "rcaeval_commit": "5e96b700445bfb5c599e505ecf37d53bf847bbeb",
        "native_module_path": str(_module_path),
        "native_module_sha256": sha256_file(_module_path),
        "pagerank_events": events,
        "returned_node_names": list(output.get("node_names", [])),
        "returned_ranks": list(output.get("ranks", ranks)),
        "returned_ranks_digest": _digest(output.get("ranks", ranks)),
        "returned_adjacency_shape": adjacency_shape,
        "returned_adjacency_nonzero_count": adjacency_nonzero,
        "classification": classification,
    }


def _digest(value: Any) -> str:
    return __import__("hashlib").sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":"))).encode("utf-8")
    ).hexdigest()


def main() -> None:
    args = _parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing diagnostic output: {args.output}")
    case_ids = _case_ids(args)
    payload = {
        "schema_version": "rca_baseline_causalrca_runtime_diagnostic_v1",
        "status": "EXECUTED_BY_MANUAL_OPERATOR",
        "codex_runs_executed": 0,
        "selection": {"dataset": args.dataset, "case_ids": case_ids},
        "rcaeval_checkout": str(RCAEVAL_CLEAN),
        "rcaeval_commit": "5e96b700445bfb5c599e505ecf37d53bf847bbeb",
        "records": [run_case(args.dataset, case_id) for case_id in case_ids],
    }
    atomic_write_json(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
