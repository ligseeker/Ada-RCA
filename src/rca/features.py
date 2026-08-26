"""Frozen event-relative telemetry representation for P3-A0.5.

This module accepts prediction-visible case data plus a trusted telemetry source
reference. It never accepts or reads a root/fault label.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .rcaeval import CaseSource


CHANNELS = ("metric", "log", "trace-error", "trace-latency")
N_BINS = 80
BIN_SECONDS = 15.0
PRE_BINS = 40
POST_BINS = 40
ONSET_THRESHOLD = 3.0
ONSET_SENTINEL = 600.0


@dataclass(frozen=True)
class CaseFeatureSet:
    case_id: str
    candidates: Tuple[str, ...]
    a: np.ndarray
    base: np.ndarray
    z: np.ndarray
    q_mask: np.ndarray
    morphology_active: np.ndarray
    z2: np.ndarray
    z3: np.ndarray


def _service_for_column(column: str, candidates: Sequence[str], channel: str) -> Optional[str]:
    name = str(column)
    if channel.startswith("trace") and name.startswith("frontendservice_"):
        name = "frontend_" + name[len("frontendservice_"):]
    matches = [candidate for candidate in candidates if name.startswith(candidate + "_")]
    return max(matches, key=len) if matches else None


def _binned_indicators(
    path: Path,
    timestamp_column: str,
    candidates: Sequence[str],
    channel: str,
    anchor_time: float,
) -> Dict[str, np.ndarray]:
    frame = pd.read_csv(path, low_memory=False)
    if timestamp_column not in frame.columns:
        raise ValueError("{} lacks timestamp column {}".format(path, timestamp_column))
    timestamps = pd.to_numeric(frame[timestamp_column], errors="coerce").to_numpy(dtype=float)
    indices = np.floor((timestamps - (float(anchor_time) - 600.0)) / BIN_SECONDS)
    valid_time = np.isfinite(indices) & (indices >= 0) & (indices < N_BINS)
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
        sums = np.bincount(indices[valid].astype(np.int64), weights=values[valid], minlength=N_BINS)
        counts = np.bincount(indices[valid].astype(np.int64), minlength=N_BINS)
        binned = np.full(N_BINS, np.nan, dtype=float)
        observed = counts > 0
        binned[observed] = sums[observed] / counts[observed]
        key = "{}::{}".format(service, column)
        result[key] = binned
    return result


def _q_by_service(indicators: Mapping[str, np.ndarray], candidates: Sequence[str]) -> Tuple[np.ndarray, np.ndarray]:
    q = np.full((len(candidates), N_BINS), np.nan, dtype=float)
    for service_index, service in enumerate(candidates):
        values = [array for key, array in indicators.items() if key.startswith(service + "::")]
        if not values:
            continue
        matrix = np.asarray(values, dtype=float)
        centers = np.full(matrix.shape[0], np.nan, dtype=float)
        scales = np.full(matrix.shape[0], np.nan, dtype=float)
        for index, series in enumerate(matrix):
            pre = series[:PRE_BINS][np.isfinite(series[:PRE_BINS])]
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
        deviations = np.full(matrix.shape, np.nan, dtype=float)
        deviations[valid_indicators] = (
            matrix[valid_indicators] - centers[valid_indicators, None]
        ) / (scales[valid_indicators, None] + 1e-6)
        magnitudes = np.abs(deviations)
        for bin_index in range(N_BINS):
            observed = magnitudes[:, bin_index][np.isfinite(magnitudes[:, bin_index])]
            if observed.size:
                q[service_index, bin_index] = float(np.percentile(observed, 90))
    return q, np.isfinite(q)


def _base_and_morphology(q: np.ndarray, q_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_services = q.shape[0]
    base = np.zeros((n_services, len(CHANNELS), 8), dtype=float)
    z = np.zeros((n_services, len(CHANNELS), N_BINS), dtype=float)
    masks = q_mask.astype(float)
    active = np.zeros((n_services, len(CHANNELS)), dtype=float)
    z2 = np.zeros((n_services, len(CHANNELS), 9), dtype=float)
    for service_index in range(n_services):
        for channel_index in range(len(CHANNELS)):
            values = q[service_index, channel_index]
            observed = q_mask[service_index, channel_index]
            pre_observed = observed[:PRE_BINS]
            post_observed = observed[PRE_BINS:]
            post_values = values[PRE_BINS:][post_observed]
            pre_values = values[:PRE_BINS][pre_observed]
            coverage = float(np.count_nonzero(observed)) / N_BINS
            available = bool(pre_values.size and post_values.size)
            magnitude = float(np.max(post_values)) if post_values.size else 0.0
            mean_impact = float(np.mean(post_values)) if post_values.size else 0.0
            pre_mean = float(np.mean(pre_values)) if pre_values.size else 0.0
            post_mean = mean_impact
            persistence = float(np.mean(post_values >= ONSET_THRESHOLD)) if post_values.size else 0.0
            onset = ONSET_SENTINEL
            onset_missing = 1.0
            for index in range(PRE_BINS, N_BINS - 1):
                if q_mask[service_index, channel_index, index] and q_mask[service_index, channel_index, index + 1]:
                    if values[index] >= ONSET_THRESHOLD and values[index + 1] >= ONSET_THRESHOLD:
                        onset = (index - PRE_BINS) * BIN_SECONDS
                        onset_missing = 0.0
                        break
            if not available:
                base[service_index, channel_index] = (
                    0.0, 0.0, 0.0, 0.0, 1.0, 0.0, coverage, 0.0,
                )
                continue
            base[service_index, channel_index] = (
                magnitude, mean_impact, post_mean - pre_mean, onset,
                onset_missing, persistence, coverage, 1.0,
            )
            maximum = float(np.max(values[observed])) if np.any(observed) else 0.0
            if maximum < 1e-6:
                continue
            active[service_index, channel_index] = 1.0
            normalized = values / (maximum + 1e-6)
            z[service_index, channel_index, observed] = normalized[observed]
            post_indices = np.flatnonzero(post_observed)
            post_z = normalized[PRE_BINS:][post_observed]
            pre_z = normalized[:PRE_BINS][pre_observed]
            pre_z_mean = float(np.mean(pre_z)) if pre_z.size else 0.0
            post_z_mean = float(np.mean(post_z)) if post_z.size else 0.0
            peak_positions = np.flatnonzero(post_observed)[post_z.argmax()] if post_z.size else 39
            peak_fraction = float(peak_positions) / 39.0
            weights = np.maximum(post_z, 0.0)
            centroid = float(np.average(post_indices, weights=weights)) / 39.0 if np.sum(weights) > 0 else 0.0
            x = post_indices.astype(float) / 39.0
            slope = float(np.polyfit(x, post_z, 1)[0]) if post_z.size >= 2 and np.ptp(x) > 0 else 0.0
            adjacent = np.abs(np.diff(post_z))[np.diff(post_indices) == 1]
            mean_adjacent = float(np.mean(adjacent)) if adjacent.size else 0.0
            fraction_high = float(np.mean(post_z >= 0.5)) if post_z.size else 0.0
            z2[service_index, channel_index] = (
                pre_z_mean, post_z_mean, post_z_mean - pre_z_mean,
                peak_fraction, centroid, slope, mean_adjacent, fraction_high, 1.0,
            )
    return base, z, masks, active, z2


def extract_case_features(
    case_id: str,
    candidates: Sequence[str],
    anchor_time: float,
    source: CaseSource,
) -> CaseFeatureSet:
    root = Path(source.source_root) if hasattr(source, "source_root") else None
    if root is None:
        root = Path(source.metrics_path).parent
    paths = {
        "metric": (Path(source.simple_metrics_path), "time"),
        "log": (Path(source.logts_path), "time"),
        "trace-error": (Path(source.trace_error_path), "time"),
        "trace-latency": (Path(source.trace_latency_path), "time"),
    }
    q_channels = []
    mask_channels = []
    for channel in CHANNELS:
        path, timestamp_column = paths[channel]
        indicators = _binned_indicators(path, timestamp_column, candidates, channel, anchor_time)
        q, mask = _q_by_service(indicators, candidates)
        q_channels.append(q)
        mask_channels.append(mask)
    q = np.stack(q_channels, axis=1)
    q_mask = np.stack(mask_channels, axis=1)
    base, z, masks, active, z2 = _base_and_morphology(q, q_mask)
    available = base[:, :, 7] > 0
    clipped = np.minimum(base[:, :, 0], 20.0)
    a = np.divide(clipped.sum(axis=1), available.sum(axis=1), out=np.zeros(len(candidates), dtype=float), where=available.sum(axis=1) > 0)
    z3 = np.concatenate((base, z, masks, active[:, :, None]), axis=2)
    return CaseFeatureSet(
        case_id=case_id,
        candidates=tuple(candidates),
        a=a,
        base=base,
        z=z,
        q_mask=masks,
        morphology_active=active,
        z2=z2,
        z3=z3,
    )


def flatten_features(features: CaseFeatureSet, variant: str) -> np.ndarray:
    if variant == "z0":
        return features.a[:, None]
    if variant == "z1":
        return features.base.reshape(len(features.candidates), -1)
    if variant == "z2":
        return np.concatenate((features.base, features.z2), axis=2).reshape(len(features.candidates), -1)
    if variant == "z3":
        return features.z3.reshape(len(features.candidates), -1)
    raise ValueError("unknown feature variant {!r}".format(variant))


def deterministic_shuffle(features: CaseFeatureSet) -> CaseFeatureSet:
    seed_material = "Ada-RCA|P3-G1|20260826|{}".format(features.case_id).encode("utf-8")
    seed = int.from_bytes(__import__("hashlib").sha256(seed_material).digest()[:8], "big")
    rng = np.random.RandomState(seed % (2 ** 32 - 1))
    permutation = rng.permutation(N_BINS)
    z = features.z[:, :, permutation]
    masks = features.q_mask[:, :, permutation]
    z3 = np.concatenate((features.base, z, masks, features.morphology_active[:, :, None]), axis=2)
    return CaseFeatureSet(features.case_id, features.candidates, features.a, features.base, z, masks, features.morphology_active, features.z2, z3)
