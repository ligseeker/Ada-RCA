"""Candidate-case telemetry information-loss audit from frozen artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from .evidence_closure import FROZEN_COMMIT, load_jsonl, sha256_file


CHANNELS = ("Metric", "Log", "Trace Error", "Trace Latency")
CHANNEL_INDEX = {channel: index for index, channel in enumerate(CHANNELS)}
CHANNEL_SPECS = {
    "Metric": ("simple_metrics_path", "metric"),
    "Log": ("logts_path", "log"),
    "Trace Error": ("trace_error_path", "trace-error"),
    "Trace Latency": ("trace_latency_path", "trace-latency"),
}
N_BINS = 80
PRE_BINS = 40
BIN_SECONDS = 15.0
SCALE_THRESHOLD = 1e-6
DATASETS = ("re2ob", "re2tt")


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _matches_frozen_commit(root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ("git", "diff", "--quiet", FROZEN_COMMIT, "--", relative_path),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _service_for_column(column: str, candidates: Sequence[str], channel_key: str) -> str | None:
    name = str(column)
    if channel_key.startswith("trace") and name.startswith("frontendservice_"):
        name = "frontend_" + name[len("frontendservice_"):]
    matches = [candidate for candidate in candidates if name.startswith(candidate + "_")]
    return max(matches, key=len) if matches else None


def _binned_series(
    frame: pd.DataFrame,
    timestamps: np.ndarray,
    column: str,
    anchor_time: float,
) -> np.ndarray:
    indices = np.floor((timestamps - (float(anchor_time) - 600.0)) / BIN_SECONDS)
    valid_time = np.isfinite(indices) & (indices >= 0) & (indices < N_BINS)
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    valid = valid_time & np.isfinite(values)
    binned = np.full(N_BINS, np.nan, dtype=float)
    if not np.any(valid):
        return binned
    integer_indices = indices[valid].astype(np.int64)
    sums = np.bincount(integer_indices, weights=values[valid], minlength=N_BINS)
    counts = np.bincount(integer_indices, minlength=N_BINS)
    observed = counts > 0
    binned[observed] = sums[observed] / counts[observed]
    return binned


def indicator_diagnostics(series: np.ndarray) -> Dict[str, bool]:
    """Classify one already-binned indicator without generating a feature."""

    values = np.asarray(series, dtype=float)
    if values.shape != (N_BINS,):
        raise ValueError("indicator must contain exactly 80 event-relative bins")
    pre = values[:PRE_BINS][np.isfinite(values[:PRE_BINS])]
    post = values[PRE_BINS:][np.isfinite(values[PRE_BINS:])]
    if pre.size:
        center = float(np.median(pre))
        raw_mad = float(np.median(np.abs(pre - center)))
        raw_iqr = float(np.percentile(pre, 75) - np.percentile(pre, 25))
        mad_scale = 1.4826 * raw_mad
        iqr_scale = raw_iqr / 1.349
        scale_valid = mad_scale >= SCALE_THRESHOLD or iqr_scale >= SCALE_THRESHOLD
        pre_all_zero = bool(np.all(pre == 0.0))
        pre_constant = bool(np.ptp(pre) == 0.0)
        post_changed = bool(post.size and np.any(np.abs(post - center) > 1e-12))
    else:
        raw_mad = float("nan")
        raw_iqr = float("nan")
        scale_valid = False
        pre_all_zero = False
        pre_constant = False
        post_changed = False
    return {
        "window_observed": bool(pre.size or post.size),
        "pre_observed": bool(pre.size),
        "post_observed": bool(post.size),
        "pre_all_zero": pre_all_zero,
        "pre_constant": pre_constant,
        "post_positive": bool(post.size and np.any(post > 0.0)),
        "post_changed": post_changed,
        "MAD_pre_zero": bool(pre.size and raw_mad == 0.0),
        "IQR_pre_zero": bool(pre.size and raw_iqr == 0.0),
        "scale_valid": bool(scale_valid),
    }


def _candidate_pair_record(
    indicator_series: Sequence[np.ndarray],
    feature_active: bool,
    include_trace_diagnostics: bool,
) -> Dict[str, bool]:
    diagnostics = [indicator_diagnostics(series) for series in indicator_series]
    pre_diagnostics = [item for item in diagnostics if item["pre_observed"]]
    mapped = bool(diagnostics)
    window_observed = any(item["window_observed"] for item in diagnostics)
    pre_observed = bool(pre_diagnostics)
    post_observed_raw = any(item["post_observed"] for item in diagnostics)
    post_observed = pre_observed and post_observed_raw
    scale_valid_raw = any(item["scale_valid"] for item in diagnostics)
    scale_valid = post_observed and scale_valid_raw
    result = {
        "eligible": True,
        "mapped": mapped,
        "window_observed": window_observed,
        "pre_observed": pre_observed,
        "post_observed": post_observed,
        "scale_valid": scale_valid,
        "feature_active": bool(feature_active),
    }
    if include_trace_diagnostics:
        pre_all_zero = bool(pre_diagnostics) and all(item["pre_all_zero"] for item in pre_diagnostics)
        pre_constant = bool(pre_diagnostics) and all(item["pre_constant"] for item in pre_diagnostics)
        mad_zero = bool(pre_diagnostics) and all(item["MAD_pre_zero"] for item in pre_diagnostics)
        iqr_zero = bool(pre_diagnostics) and all(item["IQR_pre_zero"] for item in pre_diagnostics)
        post_positive = any(item["post_positive"] for item in diagnostics)
        post_changed = any(item["post_changed"] for item in diagnostics)
        rejected = pre_observed and not scale_valid_raw
        result.update(
            {
                "pre_all_zero": pre_all_zero,
                "pre_constant": pre_constant,
                "post_positive": post_positive,
                "post_changed": post_changed,
                "MAD_pre_zero": mad_zero,
                "IQR_pre_zero": iqr_zero,
                "rejected_by_scale": rejected,
                "pre_all_zero_AND_post_positive": pre_all_zero and post_positive,
                "pre_all_zero_AND_post_positive_AND_rejected_by_scale": (
                    pre_all_zero and post_positive and rejected
                ),
                "pre_constant_AND_post_changed": pre_constant and post_changed,
                "pre_constant_AND_post_changed_AND_rejected_by_scale": (
                    pre_constant and post_changed and rejected
                ),
            }
        )
    return result


def _load_feature_activity(root: Path, dataset: str, case_id: str) -> Tuple[List[str], np.ndarray]:
    path = root / f"artifacts/features/{dataset}/{case_id}.npz"
    with np.load(path, allow_pickle=False) as data:
        candidates = [str(value) for value in data["candidates"].tolist()]
        activity = np.asarray(data["morphology_active"], dtype=float)
    if activity.shape != (len(candidates), len(CHANNELS)):
        raise ValueError(f"{path}: invalid morphology_active shape {activity.shape}")
    return candidates, activity


def _audit_dataset(root: Path, dataset: str) -> Dict[str, Any]:
    inputs = {str(row["case_id"]): row for row in load_jsonl(root / f"artifacts/source/{dataset}/inputs.jsonl")}
    sources = {str(row["case_id"]): row for row in load_jsonl(root / f"artifacts/source/{dataset}/sources.jsonl")}
    if set(inputs) != set(sources) or len(inputs) != 90:
        raise ValueError(f"{dataset}: source case coverage mismatch")
    dataset_manifest_path = root / f"artifacts/source/{dataset}_dataset_manifest.json"
    dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    file_manifest = {
        (str(row["case_id"]), str(row["relative_path"])): row
        for row in dataset_manifest["files"]
    }
    used_file_records: List[Dict[str, Any]] = []
    pair_records: Dict[str, List[Dict[str, bool]]] = {channel: [] for channel in CHANNELS}
    trace_records: List[Dict[str, bool]] = []

    for case_id in sorted(inputs):
        input_row = inputs[case_id]
        source_row = sources[case_id]
        candidates = [str(value) for value in input_row["candidates"]]
        feature_candidates, activity = _load_feature_activity(root, dataset, case_id)
        if feature_candidates != candidates:
            raise ValueError(f"{dataset}/{case_id}: frozen feature candidate order mismatch")
        anchor_time = float(input_row["anchor_time"])
        for channel in CHANNELS:
            path_field, channel_key = CHANNEL_SPECS[channel]
            path = Path(str(source_row[path_field]))
            relative_path = f"{source_row['relative_directory']}/{path.name}"
            manifest_record = file_manifest.get((case_id, relative_path))
            if manifest_record is None:
                raise ValueError(f"{dataset}/{case_id}/{channel}: no canonical file record")
            observed_size = path.stat().st_size if path.exists() else None
            observed_sha256 = _stream_sha256(path) if path.exists() else None
            used_file_records.append(
                {
                    "case_id": case_id,
                    "channel": channel,
                    "relative_path": relative_path,
                    "expected_size": int(manifest_record["size"]),
                    "observed_size": observed_size,
                    "expected_sha256": str(manifest_record["sha256"]),
                    "observed_sha256": observed_sha256,
                    "status": (
                        "PASS"
                        if observed_size == int(manifest_record["size"])
                        and observed_sha256 == str(manifest_record["sha256"])
                        else "FAIL"
                    ),
                }
            )
            frame = pd.read_csv(path, low_memory=False)
            if "time" not in frame.columns:
                raise ValueError(f"{path}: missing time column")
            timestamps = pd.to_numeric(frame["time"], errors="coerce").to_numpy(dtype=float)
            columns_by_candidate: Dict[str, List[str]] = {candidate: [] for candidate in candidates}
            for column in frame.columns:
                if column == "time":
                    continue
                if channel_key == "metric" and str(column).endswith("_latency-50"):
                    continue
                candidate = _service_for_column(str(column), candidates, channel_key)
                if candidate is not None:
                    columns_by_candidate[candidate].append(str(column))
            for candidate_index, candidate in enumerate(candidates):
                series = [
                    _binned_series(frame, timestamps, column, anchor_time)
                    for column in columns_by_candidate[candidate]
                ]
                pair = _candidate_pair_record(
                    series,
                    bool(activity[candidate_index, CHANNEL_INDEX[channel]] > 0.5),
                    channel == "Trace Error",
                )
                pair_records[channel].append(pair)
                if channel == "Trace Error":
                    trace_records.append(pair)

    funnel: Dict[str, Any] = {}
    funnel_order = (
        "eligible",
        "mapped",
        "window_observed",
        "pre_observed",
        "post_observed",
        "scale_valid",
        "feature_active",
    )
    monotonic = True
    active_subset_scale_valid = True
    pair_digests: Dict[str, str] = {}
    for channel, records in pair_records.items():
        counts = {stage: sum(bool(row[stage]) for row in records) for stage in funnel_order}
        monotonic = monotonic and all(
            counts[funnel_order[index]] >= counts[funnel_order[index + 1]]
            for index in range(len(funnel_order) - 1)
        )
        active_subset_scale_valid = active_subset_scale_valid and all(
            not row["feature_active"] or row["scale_valid"] for row in records
        )
        funnel[channel] = {
            "statistical_unit": "candidate-case pair",
            "counts": counts,
            "rates_of_eligible": {
                stage: counts[stage] / float(counts["eligible"]) for stage in funnel_order
            },
        }
        payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        pair_digests[channel] = hashlib.sha256(payload).hexdigest()

    diagnostic_names = (
        "pre_all_zero",
        "pre_constant",
        "post_positive",
        "post_changed",
        "MAD_pre_zero",
        "IQR_pre_zero",
        "rejected_by_scale",
        "pre_all_zero_AND_post_positive",
        "pre_all_zero_AND_post_positive_AND_rejected_by_scale",
        "pre_constant_AND_post_changed",
        "pre_constant_AND_post_changed_AND_rejected_by_scale",
    )
    trace_counts = {name: sum(bool(row[name]) for row in trace_records) for name in diagnostic_names}
    trace_denominator = len(trace_records)
    source_files_pass = all(record["status"] == "PASS" for record in used_file_records)
    dataset_result = {
        "candidate_case_funnel": funnel,
        "trace_error_diagnostics": {
            "statistical_unit": "candidate-case pair",
            "eligible_pair_denominator": trace_denominator,
            "counts": trace_counts,
            "rates_of_eligible": {
                name: count / float(trace_denominator) for name, count in trace_counts.items()
            },
            "definitions": {
                "pre_all_zero": "All pre-observed mapped trace-error indicator series are exactly zero.",
                "pre_constant": "All pre-observed mapped trace-error indicator series are individually constant.",
                "post_positive": "At least one mapped trace-error indicator has a positive post-event value.",
                "post_changed": "At least one mapped indicator has a post-event value different from its pre median.",
                "MAD_pre_zero": "All pre-observed mapped indicators have raw pre-event MAD equal to zero.",
                "IQR_pre_zero": "All pre-observed mapped indicators have raw pre-event IQR equal to zero.",
                "rejected_by_scale": "Pre observations exist but no mapped indicator passes MAD or IQR scale threshold 1e-6.",
            },
        },
        "provenance": {
            "dataset_manifest": f"artifacts/source/{dataset}_dataset_manifest.json",
            "dataset_manifest_sha256": sha256_file(dataset_manifest_path),
            "dataset_tree_sha256": dataset_manifest["tree_sha256"],
            "used_canonical_derived_files": len(used_file_records),
            "all_used_files_match_recorded_size_and_sha256": source_files_pass,
            "source_file_mismatches": [
                record for record in used_file_records if record["status"] != "PASS"
            ],
            "feature_pair_record_sha256": pair_digests,
            "source_manifests_match_frozen_commit": all(
                _matches_frozen_commit(root, path)
                for path in (
                    f"artifacts/source/{dataset}/inputs.jsonl",
                    f"artifacts/source/{dataset}/sources.jsonl",
                    f"artifacts/source/{dataset}_dataset_manifest.json",
                )
            ),
            "feature_artifacts_match_frozen_commit": _matches_frozen_commit(
                root, f"artifacts/features/{dataset}"
            ),
        },
        "invariants": {
            "funnel_monotonic": "PASS" if monotonic else "FAIL",
            "feature_active_subset_of_scale_valid": "PASS" if active_subset_scale_valid else "FAIL",
            "canonical_derived_file_identity": "PASS" if source_files_pass else "FAIL",
        },
    }
    return dataset_result


def build_telemetry_information_loss_audit(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    datasets = {dataset: _audit_dataset(root, dataset) for dataset in DATASETS}
    pass_checks = all(
        value == "PASS"
        for dataset in datasets.values()
        for value in dataset["invariants"].values()
    ) and all(
        dataset["provenance"]["source_manifests_match_frozen_commit"]
        and dataset["provenance"]["feature_artifacts_match_frozen_commit"]
        for dataset in datasets.values()
    )
    return {
        "schema_version": "ada_rca_telemetry_information_loss_v1_1",
        "audit_type": "CANDIDATE_CASE_TELEMETRY_INFORMATION_LOSS_AUDIT",
        "scope": {
            "primary_statistical_unit": "candidate-case pair",
            "funnel": [
                "eligible",
                "mapped",
                "window observed",
                "pre observed",
                "post observed",
                "scale valid",
                "feature active",
            ],
            "modalities": list(CHANNELS),
            "raw_record_counts": "NOT_MIXED_WITH_CANDIDATE_CASE_FUNNEL",
            "model_fit": "NOT EXECUTED",
            "new_feature_or_sparse_optimization": "NOT EXECUTED",
        },
        "auditability": {
            "candidate_case_funnel": "AUDITABLE_FROM_HASH_BOUND_CANONICAL_DERIVED_INPUTS_AND_FROZEN_FEATURE_ARTIFACTS",
            "raw_record_to_derived_cell_lineage": "NOT_FULLY_AUDITABLE_FROM_AVAILABLE_CANONICAL_ARTIFACTS",
            "reason": (
                "Raw and derived files are hash-bound, but no committed per-record lineage maps raw log/span/metric rows "
                "to each derived wide-series cell; no such rejection cause is inferred."
            ),
        },
        "datasets": datasets,
        "gate_3": {
            "status": "PASS" if pass_checks else "FAIL",
            "provenance_authorization": "GATE_4_AUTHORIZED" if pass_checks else "STOP",
            "terminal_state_if_failed": "RCA_EVIDENCE_NOT_CLOSED" if not pass_checks else None,
        },
    }
