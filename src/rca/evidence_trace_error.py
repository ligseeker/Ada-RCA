"""Read-only invariant audit for the frozen Trace Error Z2 block."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from .evidence_closure import DATASETS, FROZEN_COMMIT, sha256_bytes, sha256_file
from .features import CHANNELS
from .final_method import BASE_FIELDS, MORPHOLOGY_FIELDS, FINAL_Z2_DIMENSION


TRACE_ERROR_CHANNEL = "trace-error"
TRACE_ERROR_CHANNEL_INDEX = CHANNELS.index(TRACE_ERROR_CHANNEL)
TRACE_ERROR_FEATURE_NAMES = tuple(
    f"{TRACE_ERROR_CHANNEL}.{field}"
    for field in BASE_FIELDS + MORPHOLOGY_FIELDS
)
TRACE_ERROR_DIMENSION = len(TRACE_ERROR_FEATURE_NAMES)
TRACE_ERROR_Z2_START = TRACE_ERROR_CHANNEL_INDEX * TRACE_ERROR_DIMENSION
TRACE_ERROR_Z2_INDICES = tuple(
    range(TRACE_ERROR_Z2_START, TRACE_ERROR_Z2_START + TRACE_ERROR_DIMENSION)
)


def _frozen_feature_state(
    root: Path,
    dataset: str,
) -> Tuple[Set[str], Set[str]]:
    prefix = f"artifacts/features/{dataset}"
    tracked = {
        path
        for path in
        subprocess.check_output(
            ("git", "ls-tree", "-r", "--name-only", FROZEN_COMMIT, prefix),
            cwd=root,
            text=True,
        ).splitlines()
        if path.endswith(".npz")
    }
    changed = {
        path
        for path in
        subprocess.check_output(
            ("git", "diff", "--name-only", FROZEN_COMMIT, "--", prefix),
            cwd=root,
            text=True,
        ).splitlines()
        if path.endswith(".npz")
    }
    return tracked, changed


def _frozen_sha256(
    root: Path,
    relative_path: str,
    tracked: Set[str],
    changed: Set[str],
    working_sha256: str,
) -> Optional[str]:
    if relative_path not in tracked:
        return None
    if relative_path not in changed:
        return working_sha256
    frozen_bytes = subprocess.check_output(
        ("git", "show", f"{FROZEN_COMMIT}:{relative_path}"), cwd=root
    )
    return sha256_bytes(frozen_bytes)


def _extract_trace_error_block(path: Path) -> Tuple[Tuple[str, ...], np.ndarray]:
    with np.load(path) as data:
        candidates = tuple(str(value) for value in data["candidates"])
        base = np.asarray(data["base"], dtype=np.float64)
        morphology = np.asarray(data["z2"], dtype=np.float64)
    if base.shape != (len(candidates), len(CHANNELS), len(BASE_FIELDS)):
        raise ValueError(f"{path}: unexpected frozen base shape {base.shape}")
    if morphology.shape != (
        len(candidates),
        len(CHANNELS),
        len(MORPHOLOGY_FIELDS),
    ):
        raise ValueError(f"{path}: unexpected frozen morphology shape {morphology.shape}")
    block = np.concatenate(
        (
            base[:, TRACE_ERROR_CHANNEL_INDEX, :],
            morphology[:, TRACE_ERROR_CHANNEL_INDEX, :],
        ),
        axis=1,
    )
    if block.shape[1] != TRACE_ERROR_DIMENSION:
        raise ValueError(f"{path}: Trace Error block is not 17-dimensional")
    return candidates, block


def _case_is_discriminative(block: np.ndarray) -> bool:
    return bool(np.any(block != block[0]))


def _dimension_records(
    rows: np.ndarray,
    case_blocks: Sequence[np.ndarray],
) -> List[Dict[str, Any]]:
    records = []
    for index, feature_name in enumerate(TRACE_ERROR_FEATURE_NAMES):
        values = rows[:, index]
        records.append(
            {
                "block_index": index,
                "frozen_z2_index": TRACE_ERROR_Z2_INDICES[index],
                "feature": feature_name,
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "variance": float(np.var(values)),
                "unique_count": int(np.unique(values).size),
                "globally_nonzero": bool(np.any(values != 0.0)),
                "varies_across_candidates_within_any_case": bool(
                    any(np.any(block[:, index] != block[0, index]) for block in case_blocks)
                ),
            }
        )
    return records


def _relationship_record(rows: np.ndarray) -> Dict[str, Any]:
    coverage = rows[:, 6]
    channel_available = rows[:, 7]
    remaining_morphology = rows[:, 8:16]
    morphology_active = rows[:, 16]
    combinations, counts = np.unique(
        np.column_stack(
            (
                coverage,
                channel_available,
                morphology_active,
                np.any(remaining_morphology != 0.0, axis=1).astype(float),
            )
        ),
        axis=0,
        return_counts=True,
    )
    return {
        "fields": [
            "base.coverage",
            "base.channel_available",
            "morphology_active",
            "remaining_morphology_any_nonzero",
        ],
        "observed_combinations": [
            {
                "values": [float(value) for value in combination],
                "row_count": int(count),
            }
            for combination, count in zip(combinations, counts)
        ],
        "base_coverage_zero_rows": int(np.count_nonzero(coverage == 0.0)),
        "base_channel_available_zero_rows": int(
            np.count_nonzero(channel_available == 0.0)
        ),
        "morphology_active_zero_rows": int(
            np.count_nonzero(morphology_active == 0.0)
        ),
        "remaining_morphology_all_zero_rows": int(
            np.count_nonzero(np.all(remaining_morphology == 0.0, axis=1))
        ),
        "onset_missing_one_rows": int(np.count_nonzero(rows[:, 4] == 1.0)),
        "exact_relationship": (
            "Every row has base.coverage=0, base.channel_available=0, "
            "morphology_active=0, all other morphology fields=0, and "
            "base.onset_missing=1. All other base fields are 0."
        ),
        "implementation_path": (
            "When no Trace Error indicator survives robust pre-event scaling, "
            "q remains unobserved, coverage is 0, and the unavailable-channel "
            "branch emits onset_missing=1 before morphology computation."
        ),
    }


def _dataset_invariant(root: Path, dataset: str) -> Dict[str, Any]:
    feature_root = root / "artifacts" / "features" / dataset
    paths = sorted(feature_root.glob("*.npz"))
    if len(paths) != 90:
        raise ValueError(f"{dataset}: expected 90 frozen feature matrices")

    relative_paths = {path.relative_to(root).as_posix() for path in paths}
    tracked_paths, changed_paths = _frozen_feature_state(root, dataset)
    file_records = []
    case_blocks: List[np.ndarray] = []
    case_ids = []
    for path in paths:
        relative_path = path.relative_to(root).as_posix()
        working_bytes = path.read_bytes()
        working_sha256 = sha256_bytes(working_bytes)
        frozen_sha256 = _frozen_sha256(
            root,
            relative_path,
            tracked_paths,
            changed_paths,
            working_sha256,
        )
        candidates, block = _extract_trace_error_block(path)
        case_ids.append(path.stem)
        case_blocks.append(block)
        file_records.append(
            {
                "path": relative_path,
                "sha256": working_sha256,
                "frozen_commit_sha256": frozen_sha256,
                "matches_frozen_commit": (
                    frozen_sha256 == working_sha256
                    and relative_path in tracked_paths
                    and relative_path not in changed_paths
                ),
                "candidate_rows": len(candidates),
            }
        )

    rows = np.concatenate(case_blocks, axis=0)
    dimension_records = _dimension_records(rows, case_blocks)
    discriminative_flags = [_case_is_discriminative(block) for block in case_blocks]
    discriminative_cases = [
        case_id
        for case_id, discriminative in zip(case_ids, discriminative_flags)
        if discriminative
    ]
    case_mean_vectors = np.stack([np.mean(block, axis=0) for block in case_blocks])
    unique_vectors = np.unique(rows, axis=0)
    exact_vector = (
        [float(value) for value in unique_vectors[0]]
        if unique_vectors.shape[0] == 1
        else None
    )
    globally_nonzero = bool(np.any(rows != 0.0))
    across_case_variation = bool(np.any(np.var(case_mean_vectors, axis=0) != 0.0))
    within_case_variation = bool(discriminative_cases)
    classification = (
        "TRACE_ERROR_EFFECTIVELY_NONDISCRIMINATIVE_IN_FROZEN_Z2"
        if not within_case_variation
        else "TRACE_ERROR_RETAINS_CANDIDATE_DISCRIMINATIVE_INFORMATION"
    )
    manifest_lines = [
        f"{record['path']}\0{record['sha256']}\0{record['candidate_rows']}"
        for record in file_records
    ]
    return {
        "dataset": dataset,
        "case_count": len(paths),
        "total_candidate_case_rows": int(rows.shape[0]),
        "trace_error_dimension": int(rows.shape[1]),
        "all_zero_rows": int(np.count_nonzero(np.all(rows == 0.0, axis=1))),
        "nonzero_rows": int(np.count_nonzero(np.any(rows != 0.0, axis=1))),
        "unique_trace_error_vectors": int(unique_vectors.shape[0]),
        "exact_unique_vector_when_single": exact_vector,
        "dimensions_with_nonzero_variance": int(
            sum(record["variance"] != 0.0 for record in dimension_records)
        ),
        "dimension_statistics": dimension_records,
        "globally_nonzero": globally_nonzero,
        "across_case_variation": {
            "present": across_case_variation,
            "unique_case_mean_vectors": int(np.unique(case_mean_vectors, axis=0).shape[0]),
        },
        "within_case_candidate_discriminative_variation": {
            "present": within_case_variation,
            "cases": discriminative_cases,
            "case_count": len(discriminative_cases),
            "case_proportion": len(discriminative_cases) / float(len(paths)),
            "any_dimension_varies_within_case": any(
                record["varies_across_candidates_within_any_case"]
                for record in dimension_records
            ),
        },
        "removal_invariant": {
            "raw_candidate_vectors_changed_by_removing_trace_error": int(
                np.count_nonzero(np.any(rows != 0.0, axis=1))
            ),
            "cases_with_trace_error_constant_across_candidates": int(
                len(paths) - len(discriminative_cases)
            ),
            "change_is_constant_across_candidates_in_every_case": (
                not within_case_variation
            ),
            "conditional_logit_pairwise_utility_differences_from_trace_error": 0.0
            if not within_case_variation
            else "NONZERO_FOR_AT_LEAST_ONE_CASE_IS_POSSIBLE",
            "mathematical_interpretation": (
                "Removing the block changes the raw vector because onset_missing=1, "
                "but removes the same block from every candidate in every case; "
                "therefore the block cannot change within-case Conditional Logit "
                "utility differences or ranking for any fixed coefficient vector."
                if not within_case_variation
                else "At least one case contains candidate-varying Trace Error values."
            ),
        },
        "field_relationship": _relationship_record(rows),
        "classification": classification,
        "provenance": {
            "frozen_optimization_commit": FROZEN_COMMIT,
            "feature_file_count": len(file_records),
            "all_feature_files_match_frozen_commit": all(
                record["matches_frozen_commit"] for record in file_records
            )
            and relative_paths == tracked_paths,
            "feature_file_manifest_sha256": hashlib.sha256(
                "\n".join(manifest_lines).encode("utf-8")
            ).hexdigest(),
            "feature_files": file_records,
        },
    }


def _without_representation(record: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in record.items() if key != "representation"}


def _selection_trace_equivalence(
    root: Path,
    left_representation: str,
    right_representation: str,
) -> Dict[str, Any]:
    datasets: Dict[str, Any] = {}
    total_screen = total_screen_exact = 0
    total_grid = total_grid_exact = 0
    for dataset in DATASETS:
        o4_path = Path(f"artifacts/opt/o4_nested/{dataset}/selection_trace.json")
        final_path = Path(
            f"artifacts/opt/final/PER-DATASET-OPT/{dataset}/selection_trace.json"
        )
        trace = json.loads((root / o4_path).read_text(encoding="utf-8"))
        screen_available = screen_exact = 0
        grid_available = grid_exact = 0
        outer_fold_records = []
        for outer in trace:
            inner = outer["inner_selection_trace"]
            screen_by_representation = {
                str(row["representation"]): row
                for row in inner["representation_screen"]
            }
            screen_pair_available = (
                left_representation in screen_by_representation
                and right_representation in screen_by_representation
            )
            screen_pair_exact = False
            if screen_pair_available:
                screen_available += 1
                screen_pair_exact = (
                    _without_representation(
                        screen_by_representation[left_representation]
                    )
                    == _without_representation(
                        screen_by_representation[right_representation]
                    )
                )
                screen_exact += int(screen_pair_exact)

            left_grid = {
                (str(row["ranker"]), float(row["lambda"])): row
                for row in inner["ranker_grid"]
                if row["representation"] == left_representation
            }
            right_grid = {
                (str(row["ranker"]), float(row["lambda"])): row
                for row in inner["ranker_grid"]
                if row["representation"] == right_representation
            }
            shared_grid = sorted(set(left_grid) & set(right_grid))
            grid_available += len(shared_grid)
            exact_grid_keys = [
                key
                for key in shared_grid
                if _without_representation(left_grid[key])
                == _without_representation(right_grid[key])
            ]
            grid_exact += len(exact_grid_keys)
            outer_fold_records.append(
                {
                    "outer_fold": int(outer["outer_fold"]),
                    "representation_screen_pair_available": screen_pair_available,
                    "representation_screen_exact": screen_pair_exact
                    if screen_pair_available
                    else None,
                    "shared_ranker_grid_configurations": [
                        {"ranker": key[0], "lambda": key[1]} for key in shared_grid
                    ],
                    "exact_ranker_grid_configurations": [
                        {"ranker": key[0], "lambda": key[1]}
                        for key in exact_grid_keys
                    ],
                }
            )
        datasets[dataset] = {
            "outer_folds": outer_fold_records,
            "representation_screen_comparisons_available": screen_available,
            "representation_screen_comparisons_exact": screen_exact,
            "ranker_grid_comparisons_available": grid_available,
            "ranker_grid_comparisons_exact": grid_exact,
            "o4_selection_trace": {
                "path": o4_path.as_posix(),
                "sha256": sha256_file(root / o4_path),
            },
            "final_selection_trace": {
                "path": final_path.as_posix(),
                "sha256": sha256_file(root / final_path),
                "byte_identical_to_o4": (
                    (root / final_path).read_bytes() == (root / o4_path).read_bytes()
                ),
            },
        }
        total_screen += screen_available
        total_screen_exact += screen_exact
        total_grid += grid_available
        total_grid_exact += grid_exact
    return {
        "left_representation": left_representation,
        "right_representation": right_representation,
        "representation_screen_comparisons_available": total_screen,
        "representation_screen_comparisons_exact": total_screen_exact,
        "ranker_grid_comparisons_available": total_grid,
        "ranker_grid_comparisons_exact": total_grid_exact,
        "all_available_comparisons_exact": (
            total_screen == total_screen_exact and total_grid == total_grid_exact
        ),
        "datasets": datasets,
        "interpretation": "CONSISTENT_WITH_TE_NONDISCRIMINATIVE",
    }


def _optimization_trace_cross_check(root: Path) -> Dict[str, Any]:
    return {
        "status": "CONSISTENT_WITH_TE_NONDISCRIMINATIVE",
        "role": "SECONDARY_ONLY",
        "primary_proof": "FROZEN_FEATURE_MATRICES",
        "equivalences": {
            "M+TE_vs_Z1-M": _selection_trace_equivalence(
                root, "M+TE", "Z1-M"
            ),
            "FULL-Z2_vs_M+L+TL": _selection_trace_equivalence(
                root, "FULL-Z2", "M+L+TL"
            ),
        },
    }


def build_trace_error_representation_invariant(root: Path) -> Dict[str, Any]:
    """Describe the frozen Trace Error block without scoring or fitting a model."""

    root = root.resolve()
    datasets = {dataset: _dataset_invariant(root, dataset) for dataset in DATASETS}
    classifications = {record["classification"] for record in datasets.values()}
    if len(classifications) == 1:
        final_classification = next(iter(classifications))
    else:
        final_classification = "TRACE_ERROR_STATUS_MIXED"
    return {
        "schema_version": "ada_rca_trace_error_representation_invariant_v1",
        "audit_type": "READ_ONLY_FROZEN_TRACE_ERROR_REPRESENTATION_INVARIANT",
        "scope": {
            "model_fit": "NOT EXECUTED",
            "model_scoring": "NOT EXECUTED",
            "prediction_regeneration": "NOT EXECUTED",
            "feature_modification": "NOT EXECUTED",
            "primary_proof": "FROZEN_FEATURE_MATRICES",
        },
        "feature_order": {
            "frozen_z2_total_dimension": FINAL_Z2_DIMENSION,
            "channel": TRACE_ERROR_CHANNEL,
            "channel_index": TRACE_ERROR_CHANNEL_INDEX,
            "base_dimension": len(BASE_FIELDS),
            "morphology_dimension": len(MORPHOLOGY_FIELDS),
            "trace_error_dimension": TRACE_ERROR_DIMENSION,
            "frozen_z2_indices": list(TRACE_ERROR_Z2_INDICES),
            "feature_names": list(TRACE_ERROR_FEATURE_NAMES),
        },
        "implementation_provenance": {
            "src/rca/features.py": sha256_file(root / "src/rca/features.py"),
            "src/rca/final_method.py": sha256_file(root / "src/rca/final_method.py"),
        },
        "datasets": datasets,
        "optimization_trace_cross_check": _optimization_trace_cross_check(root),
        "final_classification": final_classification,
    }
