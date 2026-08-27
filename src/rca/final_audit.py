"""Frozen adversarial controls for the final Ada-RCA scientific audit."""

from collections import Counter
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from .features import BIN_SECONDS, CHANNELS, PRE_BINS, _service_for_column
from .p4 import CandidateEvent, fit_predict_oof, rank_candidates
from .p4_stats import FAULT_ORDER, evaluate_predictions


S1_FEATURE_NAMES = tuple(
    "{}.{}".format(channel, field)
    for channel in CHANNELS
    for field in ("coverage", "channel_available")
)
S2_FEATURE_NAMES = tuple(
    "{}.{}".format(channel, field)
    for channel in CHANNELS
    for field in ("pre_mean_q", "pre_max_q", "pre_coverage", "pre_available")
)


def observability_event(case_id: str, candidates: Sequence[str], base: np.ndarray) -> CandidateEvent:
    base = np.asarray(base, dtype=np.float64)
    if base.shape != (len(candidates), len(CHANNELS), 8):
        raise ValueError("frozen Z1 base shape mismatch")
    values = base[:, :, (6, 7)].reshape(len(candidates), -1)
    if values.shape[1] != 8:
        raise ValueError("S1 must contain exactly 8 features")
    return CandidateEvent(case_id, tuple(candidates), values)


def _pre_binned_indicators(
    path: Path,
    timestamp_column: str,
    candidates: Sequence[str],
    channel: str,
    anchor_time: float,
) -> Dict[str, np.ndarray]:
    """Read only [t0-600,t0) and apply frozen binning/mapping semantics."""
    frame = pd.read_csv(path, low_memory=False)
    if timestamp_column not in frame.columns:
        raise ValueError("{} lacks timestamp column {}".format(path, timestamp_column))
    timestamps = pd.to_numeric(frame[timestamp_column], errors="coerce").to_numpy(dtype=float)
    indices = np.floor((timestamps - (float(anchor_time) - 600.0)) / BIN_SECONDS)
    valid_time = np.isfinite(indices) & (indices >= 0) & (indices < PRE_BINS)
    result: Dict[str, np.ndarray] = {}
    for column in frame.columns:
        if column == timestamp_column:
            continue
        if channel == "metric" and str(column).endswith("_latency-50"):
            continue
        service = _service_for_column(str(column), candidates, channel)
        if service is None:
            continue
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        valid = valid_time & np.isfinite(values)
        if not np.any(valid):
            continue
        sums = np.bincount(indices[valid].astype(np.int64), weights=values[valid], minlength=PRE_BINS)
        counts = np.bincount(indices[valid].astype(np.int64), minlength=PRE_BINS)
        binned = np.full(PRE_BINS, np.nan, dtype=np.float64)
        observed = counts > 0
        binned[observed] = sums[observed] / counts[observed]
        result["{}::{}".format(service, column)] = binned
    return result


def _pre_q_by_service(indicators: Mapping[str, np.ndarray], candidates: Sequence[str]) -> np.ndarray:
    """Frozen pre-normalization and service/bin Q90 using pre bins only."""
    q = np.full((len(candidates), PRE_BINS), np.nan, dtype=np.float64)
    for service_index, service in enumerate(candidates):
        series = [array for key, array in indicators.items() if key.startswith(service + "::")]
        if not series:
            continue
        matrix = np.asarray(series, dtype=np.float64)
        centers = np.full(matrix.shape[0], np.nan, dtype=np.float64)
        scales = np.full(matrix.shape[0], np.nan, dtype=np.float64)
        for index, values in enumerate(matrix):
            pre = values[np.isfinite(values)]
            if pre.size == 0:
                continue
            center = float(np.median(pre))
            scale = 1.4826 * float(np.median(np.abs(pre - center)))
            if scale < 1e-6:
                scale = float(np.percentile(pre, 75) - np.percentile(pre, 25)) / 1.349
            if scale >= 1e-6:
                centers[index] = center
                scales[index] = scale
        valid_indicators = np.isfinite(centers) & np.isfinite(scales)
        if not np.any(valid_indicators):
            continue
        deviations = np.full(matrix.shape, np.nan, dtype=np.float64)
        deviations[valid_indicators] = (
            matrix[valid_indicators] - centers[valid_indicators, None]
        ) / (scales[valid_indicators, None] + 1e-6)
        magnitudes = np.abs(deviations)
        for bin_index in range(PRE_BINS):
            observed = magnitudes[:, bin_index][np.isfinite(magnitudes[:, bin_index])]
            if observed.size:
                q[service_index, bin_index] = float(np.percentile(observed, 90))
    return q


def pre_event_only_event(
    case_id: str,
    candidates: Sequence[str],
    anchor_time: float,
    source: Mapping[str, object],
) -> CandidateEvent:
    paths = {
        "metric": (Path(str(source["simple_metrics_path"])), "time"),
        "log": (Path(str(source["logts_path"])), "time"),
        "trace-error": (Path(str(source["trace_error_path"])), "time"),
        "trace-latency": (Path(str(source["trace_latency_path"])), "time"),
    }
    channel_features = []
    for channel in CHANNELS:
        path, timestamp_column = paths[channel]
        indicators = _pre_binned_indicators(path, timestamp_column, candidates, channel, anchor_time)
        q = _pre_q_by_service(indicators, candidates)
        observed = np.isfinite(q)
        values = np.zeros((len(candidates), 4), dtype=np.float64)
        for candidate_index in range(len(candidates)):
            current = q[candidate_index][observed[candidate_index]]
            if current.size:
                values[candidate_index] = (
                    float(np.mean(current)),
                    float(np.max(current)),
                    float(current.size) / PRE_BINS,
                    1.0,
                )
        channel_features.append(values)
    features = np.stack(channel_features, axis=1).reshape(len(candidates), -1)
    if features.shape[1] != 16 or not np.all(np.isfinite(features)):
        raise ValueError("S2 must contain exactly 16 finite features")
    return CandidateEvent(case_id, tuple(candidates), features)


def s0_rankings(
    events: Mapping[str, CandidateEvent],
    roots: Mapping[str, str],
    assignments: Mapping[str, int],
) -> Tuple[Tuple[Mapping[str, object], ...], Tuple[Mapping[str, object], ...], Mapping[str, object]]:
    deterministic_rows = []
    expected_rows = []
    seen_sizes = {}
    for fold in (0, 1, 2):
        seen = tuple(sorted({roots[case_id] for case_id in roots if assignments[case_id] != fold}))
        seen_sizes[str(fold)] = {"size": len(seen), "services": list(seen)}
        seen_set = set(seen)
        for case_id in sorted(events):
            if assignments[case_id] != fold:
                continue
            event = events[case_id]
            scores = np.asarray([1.0 if candidate in seen_set else 0.0 for candidate in event.candidates])
            ranking = rank_candidates(event.candidates, scores)
            deterministic_rows.append({
                "case_id": case_id,
                "fold": fold,
                "candidate_scores": {candidate: float(scores[index]) for index, candidate in enumerate(event.candidates)},
                "ranking": list(ranking),
            })
            root = roots[case_id]
            root_score = 1.0 if root in seen_set else 0.0
            higher = sum(float(score) > root_score for score in scores)
            tied = sum(float(score) == root_score for score in scores)
            expected = {}
            for k in (1, 3, 5):
                expected["AC@{}".format(k)] = max(0, min(tied, k - higher)) / float(tied)
            expected["Avg@5"] = sum(max(0, min(tied, k - higher)) / float(tied) for k in range(1, 6)) / 5.0
            expected["MRR"] = sum(1.0 / float(higher + offset) for offset in range(1, tied + 1)) / float(tied)
            expected_rows.append({
                **expected,
                "case_id": case_id,
                "fold": fold,
                "tie_group_size": tied,
                "higher_score_count": higher,
            })
    return tuple(deterministic_rows), tuple(expected_rows), seen_sizes


def attach_labels(predictions, labels):
    rows = []
    for prediction in predictions:
        row = dict(prediction)
        row["fault_type"] = labels[row["case_id"]]["fault_type"]
        row["root_service"] = labels[row["case_id"]]["root_service"]
        rows.append(row)
    return tuple(rows)


def fit_control_oof(events, roots, assignments):
    return fit_predict_oof(
        events,
        roots,
        assignments,
        relative=False,
        l2_lambda=1.0,
        max_iter=1000,
        gradient_tolerance=1e-8,
    )


def aggregate_expected(rows: Sequence[Mapping[str, object]], labels: Mapping[str, Mapping[str, object]]):
    metrics = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")

    def aggregate(subset):
        return {metric: float(np.mean([float(row[metric]) for row in subset])) for metric in metrics}

    enriched = [
        {**row, "fault_type": labels[row["case_id"]]["fault_type"], "root_service": labels[row["case_id"]]["root_service"]}
        for row in rows
    ]
    return {
        "overall_cases": aggregate(enriched),
        "by_fault": {fault: aggregate([row for row in enriched if row["fault_type"] == fault]) for fault in FAULT_ORDER},
        "by_root": {root: aggregate([row for row in enriched if row["root_service"] == root]) for root in sorted({row["root_service"] for row in enriched})},
        "by_fold": {str(fold): aggregate([row for row in enriched if row["fold"] == fold]) for fold in (0, 1, 2)},
        "case_metrics": enriched,
    }


def comparison_bootstrap(
    final_by_dataset: Mapping[str, Sequence[Mapping[str, object]]],
    control_by_dataset: Mapping[str, Sequence[Mapping[str, object]]],
    metric: str,
    resamples: int = 10000,
    seed: int = 20260827,
) -> Mapping[str, object]:
    rng = np.random.RandomState(seed)
    dataset_reports = {}
    dataset_samples = {}
    for dataset in ("re2ob", "re2tt"):
        final = {str(row["case_id"]): row for row in final_by_dataset[dataset]}
        control = {str(row["case_id"]): row for row in control_by_dataset[dataset]}
        if set(final) != set(control):
            raise ValueError("paired comparison case IDs differ")
        arrays = {}
        for fault in FAULT_ORDER:
            case_ids = sorted(case_id for case_id in final if str(final[case_id]["fault_type"]) == fault)
            if len(case_ids) != 15:
                raise ValueError("expected 15 cases per fault")
            arrays[fault] = np.asarray(
                [float(final[case_id][metric]) - float(control[case_id][metric]) for case_id in case_ids],
                dtype=np.float64,
            )
        samples = np.empty(resamples, dtype=np.float64)
        for index in range(resamples):
            samples[index] = float(np.mean(np.concatenate([
                values[rng.randint(0, len(values), len(values))]
                for values in arrays.values()
            ])))
        point = float(np.mean(np.concatenate(list(arrays.values()))))
        dataset_reports[dataset] = {
            "point_delta": point,
            "ci95": [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))],
            "delta_by_fault": {fault: float(np.mean(values)) for fault, values in arrays.items()},
        }
        dataset_samples[dataset] = samples
    mean_samples = (dataset_samples["re2ob"] + dataset_samples["re2tt"]) / 2.0
    mean_point = (dataset_reports["re2ob"]["point_delta"] + dataset_reports["re2tt"]["point_delta"]) / 2.0
    state = (
        "CONTROL_SEPARATED"
        if dataset_reports["re2ob"]["point_delta"] > 0
        and dataset_reports["re2tt"]["point_delta"] > 0
        and float(np.percentile(mean_samples, 2.5)) > 0
        else "CONTROL_OVERLAP"
        if mean_point > 0
        else "CONTROL_MATCH_OR_EXCEED"
    )
    return {
        "metric": metric,
        "resamples": resamples,
        "seed": seed,
        "fault_stratified": True,
        "datasets": dataset_reports,
        "equal_dataset_mean": {
            "point_delta": mean_point,
            "ci95": [float(np.percentile(mean_samples, 2.5)), float(np.percentile(mean_samples, 97.5))],
        },
        "state": state if metric == "Avg@5" else None,
    }


def class_distribution(events: Mapping[str, CandidateEvent]) -> Mapping[str, int]:
    return dict(sorted(Counter(candidate for event in events.values() for candidate in event.candidates).items()))

