#!/usr/bin/env python3
"""Audit shifted-anchor data support without computing model performance."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFSETS = (-30, -15, 0, 15, 30)
SOURCES = {
    "metric": ("simple_metrics_path", "simple_metrics.csv", 1.0),
    "log": ("logts_path", "logts.csv", 15.0),
    "trace-error": ("trace_error_path", "tracets_err.csv", 15.0),
    "trace-latency": ("trace_latency_path", "tracets_lat.csv", 15.0),
}


def read_jsonl(path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit_source(path, anchor):
    frame = pd.read_csv(path, usecols=["time"], low_memory=False)
    raw = pd.to_numeric(frame["time"], errors="coerce").to_numpy(dtype=np.float64)
    timestamps = raw[np.isfinite(raw)]
    if timestamps.size == 0:
        return {
            "path": str(path), "rows": len(raw), "valid_timestamp_rows": 0,
            "malformed_timestamp_rows": int(len(raw)), "first_relative_seconds": None,
            "last_relative_seconds": None, "delta_seconds_distribution": {},
            "offsets": {str(offset): {"supported": False, "valid_rows_in_window": 0} for offset in OFFSETS},
        }
    timestamps.sort()
    deltas = np.diff(timestamps)
    delta_distribution = Counter(float(value) for value in deltas if np.isfinite(value))
    offsets = {}
    for offset in OFFSETS:
        start = float(anchor) + offset - 600.0
        end = float(anchor) + offset + 600.0
        offsets[str(offset)] = {
            "window_start_relative_seconds": float(start - anchor),
            "window_end_relative_seconds": float(end - anchor),
            "supported": bool(float(timestamps[0]) <= start and float(timestamps[-1]) >= end),
            "valid_rows_in_window": int(np.count_nonzero((timestamps >= start) & (timestamps < end))),
        }
    return {
        "path": str(path),
        "rows": int(len(raw)),
        "valid_timestamp_rows": int(timestamps.size),
        "malformed_timestamp_rows": int(len(raw) - timestamps.size),
        "first_relative_seconds": float(timestamps[0] - anchor),
        "last_relative_seconds": float(timestamps[-1] - anchor),
        "delta_seconds_distribution": {str(key): value for key, value in sorted(delta_distribution.items())},
        "offsets": offsets,
    }


def main():
    if subprocess.check_output(("git", "status", "--porcelain"), cwd=PROJECT_ROOT, text=True).strip():
        raise RuntimeError("anchor feasibility must be generated from a clean source commit")
    source_commit = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip()
    output = PROJECT_ROOT / "artifacts" / "final_audit" / "anchor_feasibility.json"
    if output.exists():
        raise FileExistsError(str(output))
    report = {
        "schema_version": "ada_rca_anchor_feasibility_v1",
        "source_commit": source_commit,
        "protocol": "docs/RCA_FINAL_METHOD_FREEZE_V1.0.md",
        "offsets_seconds": list(OFFSETS),
        "required_full_support_relative_seconds": [-630, 630],
        "window_width_seconds": 1200,
        "performance_computed": False,
        "official_derived_sources_only": True,
        "reconstruction_semantics": "src/rca/features.py extract_case_features with unchanged frozen mapping, binning, normalization, Q90, missingness, and Z2 rules",
        "datasets": {},
    }
    unsupported = []
    for dataset in ("re2ob", "re2tt"):
        inputs = {str(row["case_id"]): row for row in read_jsonl(PROJECT_ROOT / "artifacts" / "source" / dataset / "inputs.jsonl")}
        sources = {str(row["case_id"]): row for row in read_jsonl(PROJECT_ROOT / "artifacts" / "source" / dataset / "sources.jsonl")}
        cases = []
        for case_id in sorted(inputs):
            anchor = float(inputs[case_id]["anchor_time"])
            source_reports = {}
            for channel, (key, expected_name, expected_cadence) in SOURCES.items():
                path = Path(str(sources[case_id][key]))
                source_report = audit_source(path, anchor)
                source_report["expected_filename"] = expected_name
                source_report["expected_cadence_seconds"] = expected_cadence
                source_report["uses_frozen_derived_source"] = path.name == expected_name
                source_report["frozen_reconstruction_semantics"] = True
                source_reports[channel] = source_report
                for offset in OFFSETS:
                    if not source_report["offsets"][str(offset)]["supported"]:
                        unsupported.append({"dataset": dataset, "case_id": case_id, "channel": channel, "offset_seconds": offset, "reason": "timestamp_boundary_support"})
                    if not source_report["uses_frozen_derived_source"]:
                        unsupported.append({"dataset": dataset, "case_id": case_id, "channel": channel, "offset_seconds": offset, "reason": "unexpected_data_source"})
            cases.append({"case_id": case_id, "anchor_time": anchor, "sources": source_reports})
        report["datasets"][dataset] = {"case_count": len(cases), "cases": cases}
    report["unsupported"] = unsupported
    report["unsupported_count"] = len(unsupported)
    report["all_180_cases_supported"] = len(unsupported) == 0
    report["status"] = "ANCHOR_AUDIT_FEASIBLE_UNDER_FROZEN_PIPELINE" if not unsupported else "ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE"
    report["anchor_performance_authorized_by_feasibility"] = not unsupported
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["environment"] = {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}
    write_json(output, report)
    print(json.dumps({"status": report["status"], "unsupported_count": len(unsupported), "case_counts": {dataset: value["case_count"] for dataset, value in report["datasets"].items()}, "performance_computed": False}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

