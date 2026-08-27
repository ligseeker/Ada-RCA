"""Frozen final Ada-RCA Z2 execution and persisted-state replay helpers."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple

import numpy as np

from .features import CHANNELS
from .p4 import CandidateEvent, ConditionalLogitFit, fit_predict_oof, rank_candidates


BASE_FIELDS = (
    "magnitude",
    "mean_impact",
    "pre_post_shift",
    "onset_seconds",
    "onset_missing",
    "persistence",
    "coverage",
    "channel_available",
)
MORPHOLOGY_FIELDS = (
    "normalized_pre_mean",
    "normalized_post_mean",
    "normalized_post_minus_pre_mean",
    "post_peak_time_fraction",
    "post_amplitude_weighted_centroid_fraction",
    "post_ols_slope",
    "post_mean_absolute_adjacent_difference",
    "post_fraction_z_ge_0_5",
    "morphology_active",
)
FINAL_Z2_FEATURE_NAMES = tuple(
    "{}.{}".format(channel, field)
    for channel in CHANNELS
    for field in BASE_FIELDS + MORPHOLOGY_FIELDS
)
FINAL_Z2_DIMENSION = 68
FINAL_Z2_FEATURE_ORDER_SHA256 = hashlib.sha256(
    "\n".join(FINAL_Z2_FEATURE_NAMES).encode("utf-8")
).hexdigest()


@dataclass(frozen=True)
class PersistedFoldState:
    fold: int
    fit: ConditionalLogitFit
    feature_names: Tuple[str, ...]
    l2_lambda: float
    gradient_tolerance: float
    source_commit: str
    representation_provenance: str
    split_provenance: str
    dataset_tree_sha256: str


def read_jsonl(path: Path) -> Tuple[Mapping[str, object], ...]:
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_z2_event(path: Path) -> CandidateEvent:
    with np.load(path) as data:
        candidates = tuple(str(value) for value in data["candidates"])
        base = np.asarray(data["base"], dtype=np.float64)
        morphology = np.asarray(data["z2"], dtype=np.float64)
    values = np.concatenate((base, morphology), axis=2).reshape(len(candidates), -1)
    if values.shape[1] != FINAL_Z2_DIMENSION:
        raise ValueError("frozen Z2 must contain exactly 68 features")
    return CandidateEvent(path.stem, candidates, values)


def load_dataset(project_root: Path, dataset: str):
    if dataset not in ("re2ob", "re2tt"):
        raise ValueError("dataset must be re2ob or re2tt")
    source = project_root / "artifacts" / "source" / dataset
    labels = {str(row["case_id"]): row for row in read_jsonl(source / "labels.jsonl")}
    assignments = {
        str(row["case_id"]): int(row["fold"])
        for row in json.loads(
            (project_root / "artifacts" / "splits" / dataset / "assignments.json").read_text(encoding="utf-8")
        )
    }
    events = {
        case_id: load_z2_event(project_root / "artifacts" / "features" / dataset / (case_id + ".npz"))
        for case_id in sorted(labels)
    }
    if any(event.case_id != case_id for case_id, event in events.items()):
        raise ValueError("feature filename and case ID mismatch")
    if set(events) != set(labels) or set(events) != set(assignments):
        raise ValueError("features, labels, and split assignments must align")
    roots = {case_id: str(row["root_service"]) for case_id, row in labels.items()}
    return events, labels, roots, assignments


def fit_final_oof(events, roots, assignments):
    return fit_predict_oof(
        events,
        roots,
        assignments,
        relative=False,
        l2_lambda=1.0,
        max_iter=1000,
        gradient_tolerance=1e-8,
    )


def save_fold_state(path: Path, state: PersistedFoldState) -> Mapping[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        weights=np.asarray(state.fit.weights, dtype=np.float64),
        scaler_mean=np.asarray(state.fit.scaler_mean, dtype=np.float64),
        scaler_scale=np.asarray(state.fit.scaler_scale, dtype=np.float64),
    )
    metadata = {
        "schema_version": "ada_rca_final_fold_state_v1",
        "fold": int(state.fold),
        "feature_dimension": len(state.feature_names),
        "feature_names": list(state.feature_names),
        "feature_order_sha256": FINAL_Z2_FEATURE_ORDER_SHA256,
        "lambda": float(state.l2_lambda),
        "optimizer": "scipy.optimize.minimize:L-BFGS-B with deterministic Newton polish",
        "zero_initialization": True,
        "float_dtype": "float64",
        "gradient_tolerance": float(state.gradient_tolerance),
        "initial_loss": float(state.fit.initial_loss),
        "final_loss": float(state.fit.final_loss),
        "gradient_norm": float(state.fit.gradient_norm),
        "iterations": int(state.fit.iterations),
        "converged": bool(state.fit.converged),
        "message": str(state.fit.message),
        "source_commit": state.source_commit,
        "representation_provenance": state.representation_provenance,
        "split_provenance": state.split_provenance,
        "dataset_tree_sha256": state.dataset_tree_sha256,
        "array_file": path.name,
        "array_sha256": sha256_file(path),
    }
    metadata_path = path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def load_fold_state(path: Path) -> PersistedFoldState:
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if metadata["array_sha256"] != sha256_file(path):
        raise ValueError("persisted model-state checksum mismatch")
    feature_names = tuple(str(value) for value in metadata["feature_names"])
    if feature_names != FINAL_Z2_FEATURE_NAMES:
        raise ValueError("persisted feature order differs from frozen Z2")
    if metadata["feature_order_sha256"] != FINAL_Z2_FEATURE_ORDER_SHA256:
        raise ValueError("persisted feature-order digest mismatch")
    with np.load(path) as data:
        fit = ConditionalLogitFit(
            weights=np.asarray(data["weights"], dtype=np.float64),
            scaler_mean=np.asarray(data["scaler_mean"], dtype=np.float64),
            scaler_scale=np.asarray(data["scaler_scale"], dtype=np.float64),
            initial_loss=float(metadata["initial_loss"]),
            final_loss=float(metadata["final_loss"]),
            gradient_norm=float(metadata["gradient_norm"]),
            iterations=int(metadata["iterations"]),
            converged=bool(metadata["converged"]),
            message=str(metadata["message"]),
        )
    if fit.weights.shape != (FINAL_Z2_DIMENSION,):
        raise ValueError("persisted weight dimension differs from frozen Z2")
    if fit.scaler_mean.shape != fit.weights.shape or fit.scaler_scale.shape != fit.weights.shape:
        raise ValueError("persisted scaler dimension differs from weights")
    return PersistedFoldState(
        fold=int(metadata["fold"]),
        fit=fit,
        feature_names=feature_names,
        l2_lambda=float(metadata["lambda"]),
        gradient_tolerance=float(metadata["gradient_tolerance"]),
        source_commit=str(metadata["source_commit"]),
        representation_provenance=str(metadata["representation_provenance"]),
        split_provenance=str(metadata["split_provenance"]),
        dataset_tree_sha256=str(metadata["dataset_tree_sha256"]),
    )


def predict_with_persisted_states(
    events: Mapping[str, CandidateEvent],
    assignments: Mapping[str, int],
    states: Mapping[int, PersistedFoldState],
) -> Tuple[Mapping[str, object], ...]:
    predictions = []
    for case_id in sorted(events):
        event = events[case_id]
        fold = int(assignments[case_id])
        if fold not in states or states[fold].fold != fold:
            raise ValueError("missing persisted state for fold {}".format(fold))
        if event.features.shape[1] != len(states[fold].feature_names):
            raise ValueError("event feature dimension differs from persisted state")
        scores = states[fold].fit.scores(event.features)
        predictions.append({
            "case_id": case_id,
            "fold": fold,
            "candidate_scores": {
                candidate: float(scores[index])
                for index, candidate in enumerate(event.candidates)
            },
            "ranking": list(rank_candidates(event.candidates, scores)),
        })
    return tuple(predictions)


def compare_predictions(
    left: Sequence[Mapping[str, object]],
    right: Sequence[Mapping[str, object]],
) -> Mapping[str, object]:
    left_by_id = {str(row["case_id"]): row for row in left}
    right_by_id = {str(row["case_id"]): row for row in right}
    if set(left_by_id) != set(right_by_id):
        raise ValueError("prediction case IDs differ")
    max_error = 0.0
    ranking_equal = True
    for case_id in sorted(left_by_id):
        left_row, right_row = left_by_id[case_id], right_by_id[case_id]
        if tuple(left_row["ranking"]) != tuple(right_row["ranking"]):
            ranking_equal = False
        left_scores = left_row["candidate_scores"]
        right_scores = right_row["candidate_scores"]
        if set(left_scores) != set(right_scores):
            raise ValueError("candidate score keys differ for {}".format(case_id))
        for candidate in left_scores:
            max_error = max(max_error, abs(float(left_scores[candidate]) - float(right_scores[candidate])))
    return {
        "case_count": len(left_by_id),
        "ranking_identical": ranking_equal,
        "max_abs_score_difference": float(max_error),
    }

