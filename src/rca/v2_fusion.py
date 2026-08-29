"""Preregistered low-capacity cross-modal features for Ada-RCA V2."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping, Sequence, Tuple

import numpy as np

from .final_method import FINAL_Z2_DIMENSION, FINAL_Z2_FEATURE_NAMES
from .p4 import CandidateEvent


MODALITY_ORDER = ("M", "L", "TE", "TL")
PAIR_ORDER = (
    ("M", "L"),
    ("M", "TE"),
    ("M", "TL"),
    ("L", "TE"),
    ("L", "TL"),
    ("TE", "TL"),
)
XC_FIELDS = (
    "onset_gap",
    "peak_gap",
    "centroid_gap",
    "post_activity_overlap",
    "pair_valid",
)
XC_FEATURE_NAMES = tuple(
    "{}-{}.{}".format(left, right, field)
    for left, right in PAIR_ORDER
    for field in XC_FIELDS
)
XC_DIMENSION = 30
F1_FEATURE_NAMES = FINAL_Z2_FEATURE_NAMES + XC_FEATURE_NAMES
F1_DIMENSION = 98
POST_START = 40
ACTIVE_THRESHOLD = 0.5


@dataclass(frozen=True)
class FusionCaseFeatures:
    case_id: str
    candidates: Tuple[str, ...]
    base: np.ndarray
    morphology: np.ndarray
    trajectories: np.ndarray
    observation_masks: np.ndarray
    morphology_active: np.ndarray

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id:
            raise ValueError("case_id must be a non-empty opaque string")
        candidates = tuple(str(value) for value in self.candidates)
        if len(candidates) < 4 or len(set(candidates)) != len(candidates):
            raise ValueError("V2 requires at least four unique candidates")
        n = len(candidates)
        base = np.asarray(self.base, dtype=np.float64)
        morphology = np.asarray(self.morphology, dtype=np.float64)
        trajectories = np.asarray(self.trajectories, dtype=np.float64)
        masks = np.asarray(self.observation_masks, dtype=bool)
        active = np.asarray(self.morphology_active, dtype=np.float64)
        expected = {
            "base": ((n, 4, 8), base),
            "morphology": ((n, 4, 9), morphology),
            "trajectories": ((n, 4, 80), trajectories),
            "observation_masks": ((n, 4, 80), masks),
            "morphology_active": ((n, 4), active),
        }
        for name, (shape, values) in expected.items():
            if values.shape != shape:
                raise ValueError("{} must have shape {}".format(name, shape))
        if not all(np.all(np.isfinite(values)) for values in (base, morphology, trajectories, active)):
            raise ValueError("frozen V2 inputs must be finite")
        if not np.array_equal(morphology[:, :, 8], active):
            raise ValueError("morphology active arrays disagree")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "morphology", morphology)
        object.__setattr__(self, "trajectories", trajectories)
        object.__setattr__(self, "observation_masks", masks)
        object.__setattr__(self, "morphology_active", active)

    def z2_values(self) -> np.ndarray:
        values = np.concatenate((self.base, self.morphology), axis=2).reshape(len(self.candidates), -1)
        if values.shape != (len(self.candidates), FINAL_Z2_DIMENSION):
            raise ValueError("frozen Z2 must remain exactly 68D")
        return values


@dataclass(frozen=True)
class F1Representation:
    event: CandidateEvent
    z2: np.ndarray
    xc30: np.ndarray
    shifts: Mapping[str, int]


def load_fusion_case(path: Path) -> FusionCaseFeatures:
    with np.load(path) as data:
        return FusionCaseFeatures(
            case_id=path.stem,
            candidates=tuple(str(value) for value in data["candidates"]),
            base=np.asarray(data["base"], dtype=np.float64),
            morphology=np.asarray(data["z2"], dtype=np.float64),
            trajectories=np.asarray(data["z"], dtype=np.float64),
            observation_masks=np.asarray(data["q_mask"], dtype=bool),
            morphology_active=np.asarray(data["morphology_active"], dtype=np.float64),
        )


def reorder_fusion_case(case: FusionCaseFeatures, candidate_order: Sequence[str]) -> FusionCaseFeatures:
    candidate_order = tuple(str(value) for value in candidate_order)
    if len(candidate_order) != len(case.candidates) or set(candidate_order) != set(case.candidates):
        raise ValueError("candidate order must contain the exact candidate set")
    indices = np.asarray([case.candidates.index(candidate) for candidate in candidate_order], dtype=np.int64)
    return FusionCaseFeatures(
        case.case_id,
        candidate_order,
        case.base[indices],
        case.morphology[indices],
        case.trajectories[indices],
        case.observation_masks[indices],
        case.morphology_active[indices],
    )


def deterministic_misalignment_shifts(case_id: str, candidate_count: int) -> Mapping[str, int]:
    if candidate_count < 4:
        raise ValueError("nonzero distinct shifts require at least four candidates")
    shifts = {"M": 0}
    used = {0}
    for modality in MODALITY_ORDER[1:]:
        material = "Ada-RCA|V2-F1|20260829|{}|{}".format(case_id, modality).encode("utf-8")
        shift = int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % candidate_count
        while shift in used:
            shift = (shift + 1) % candidate_count
        shifts[modality] = int(shift)
        used.add(int(shift))
    return shifts


def shifted_source_indices(candidate_count: int, shifts: Mapping[str, int]) -> Mapping[str, np.ndarray]:
    if set(shifts) != set(MODALITY_ORDER) or int(shifts["M"]) != 0:
        raise ValueError("shifts must contain the frozen modalities with metric shift zero")
    values = tuple(int(shifts[modality]) for modality in MODALITY_ORDER[1:])
    if any(value <= 0 or value >= candidate_count for value in values) or len(set(values)) != 3:
        raise ValueError("non-metric shifts must be nonzero, in range, and distinct")
    target = np.arange(candidate_count, dtype=np.int64)
    return {
        modality: (target + int(shifts[modality])) % candidate_count
        for modality in MODALITY_ORDER
    }


def build_xc30(case: FusionCaseFeatures, shifts: Mapping[str, int] = None) -> np.ndarray:
    n = len(case.candidates)
    if shifts is None:
        shifts = {modality: 0 for modality in MODALITY_ORDER}
        sources = {modality: np.arange(n, dtype=np.int64) for modality in MODALITY_ORDER}
    else:
        sources = shifted_source_indices(n, shifts)
    columns = []
    for left, right in PAIR_ORDER:
        left_channel = MODALITY_ORDER.index(left)
        right_channel = MODALITY_ORDER.index(right)
        left_rows = sources[left]
        right_rows = sources[right]

        left_onset_missing = case.base[left_rows, left_channel, 4]
        right_onset_missing = case.base[right_rows, right_channel, 4]
        onset_gap = np.ones(n, dtype=np.float64)
        onset_valid = (left_onset_missing == 0.0) & (right_onset_missing == 0.0)
        onset_gap[onset_valid] = np.abs(
            case.base[left_rows[onset_valid], left_channel, 3]
            - case.base[right_rows[onset_valid], right_channel, 3]
        ) / 600.0

        left_active = case.morphology_active[left_rows, left_channel] == 1.0
        right_active = case.morphology_active[right_rows, right_channel] == 1.0
        both_active = left_active & right_active
        peak_gap = np.ones(n, dtype=np.float64)
        centroid_gap = np.ones(n, dtype=np.float64)
        peak_gap[both_active] = np.abs(
            case.morphology[left_rows[both_active], left_channel, 3]
            - case.morphology[right_rows[both_active], right_channel, 3]
        )
        centroid_gap[both_active] = np.abs(
            case.morphology[left_rows[both_active], left_channel, 4]
            - case.morphology[right_rows[both_active], right_channel, 4]
        )

        left_mask = case.observation_masks[left_rows, left_channel, POST_START:]
        right_mask = case.observation_masks[right_rows, right_channel, POST_START:]
        joint = left_mask & right_mask
        left_post_active = (case.trajectories[left_rows, left_channel, POST_START:] >= ACTIVE_THRESHOLD) & joint
        right_post_active = (case.trajectories[right_rows, right_channel, POST_START:] >= ACTIVE_THRESHOLD) & joint
        intersection = np.count_nonzero(left_post_active & right_post_active, axis=1)
        union = np.count_nonzero(left_post_active | right_post_active, axis=1)
        overlap = np.divide(
            intersection,
            union,
            out=np.zeros(n, dtype=np.float64),
            where=union > 0,
        )
        jointly_observed = np.any(joint, axis=1)
        left_available = case.base[left_rows, left_channel, 7] == 1.0
        right_available = case.base[right_rows, right_channel, 7] == 1.0
        pair_valid = (
            left_available & right_available & left_active & right_active & jointly_observed
        ).astype(np.float64)
        columns.extend((onset_gap, peak_gap, centroid_gap, overlap, pair_valid))
    xc30 = np.column_stack(columns).astype(np.float64)
    if xc30.shape != (n, XC_DIMENSION) or not np.all(np.isfinite(xc30)):
        raise ValueError("XC30 must be a finite 30D representation")
    return xc30


def build_f1_representation(case: FusionCaseFeatures, misaligned: bool = False) -> F1Representation:
    z2 = case.z2_values()
    shifts = (
        deterministic_misalignment_shifts(case.case_id, len(case.candidates))
        if misaligned
        else {modality: 0 for modality in MODALITY_ORDER}
    )
    xc30 = build_xc30(case, shifts if misaligned else None)
    values = np.concatenate((z2, xc30), axis=1)
    if values.shape != (len(case.candidates), F1_DIMENSION):
        raise ValueError("F1 must be exactly 98D")
    if not np.array_equal(values[:, :FINAL_Z2_DIMENSION], z2):
        raise ValueError("F1 construction changed frozen Z2")
    return F1Representation(
        event=CandidateEvent(case.case_id, case.candidates, values),
        z2=z2,
        xc30=xc30,
        shifts=shifts,
    )
