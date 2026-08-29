"""Canonical semantic interpretation for frozen RCA evidence levels.

This module does not rewrite Gate 0 or Gate 1.  It classifies the evidence that
those historical artifacts recorded using the explicit PASS / FAIL /
NOT_AUDITABLE meanings required by Gate 5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .evidence_closure import DATASETS, sha256_file


PASS = "PASS"
FAIL = "FAIL"
NOT_AUDITABLE = "NOT_AUDITABLE"

STATUS_DEFINITIONS = {
    PASS: "The claim was directly verified from available immutable evidence.",
    FAIL: "Available evidence directly contradicts the required condition.",
    NOT_AUDITABLE: "The required object was not frozen, so the condition cannot be evaluated.",
}


def semantic_status(*, evidence_exists: bool, condition_verified: Optional[bool]) -> str:
    """Return the evidence-level status without treating absence as failure."""

    if not evidence_exists:
        return NOT_AUDITABLE
    if condition_verified is None:
        raise ValueError("condition_verified is required when evidence exists")
    return PASS if condition_verified else FAIL


def _load(root: Path, relative_path: str) -> Dict[str, Any]:
    return json.loads((root / relative_path).read_text(encoding="utf-8"))


def _direct_root_rank_checks(
    root: Path,
    rank_level: Mapping[str, Any],
) -> Dict[str, Dict[str, str]]:
    checks = rank_level["checks"]
    source_path = root / str(rank_level["source_file"])
    source_hash_matches = sha256_file(source_path) == str(rank_level["source_sha256"])

    grouped = {
        "case_coverage": (
            checks["exact_expected_90_cases"] == PASS
            and checks["unique_case_ids"] == PASS
        ),
        "fold_provenance": (
            checks["valid_folds"] == PASS
            and checks["fold_assignment_consistency"] == PASS
        ),
        "root_mapping": checks["root_mapping_consistency"] == PASS,
        "root_belongs_to_registry": (
            checks["root_belongs_to_legal_candidate_registry"] == PASS
        ),
        "root_rank_integer": checks["root_rank_integer"] == PASS,
        "root_rank_range": checks["root_rank_range"] == PASS,
        "root_rank_artifact_immutability": (
            checks["committed_immutable_root_rank_source"] == PASS
            and checks["no_post_audit_root_rank_modification"] == PASS
        ),
        "sha_and_commit_provenance": (
            checks["sha256_recorded"] == PASS
            and checks["traceable_to_frozen_optimization_commit"] == PASS
            and source_hash_matches
        ),
        "no_model_refit_required": checks["no_model_refit_required"] == PASS,
    }
    return {
        name: {
            "status": semantic_status(
                evidence_exists=True,
                condition_verified=verified,
            ),
            "evidence": str(rank_level["source_file"]),
        }
        for name, verified in grouped.items()
    }


def _per_dataset_ranking_object_checks() -> Dict[str, Dict[str, str]]:
    reason = "The complete candidate score/ranking object was not frozen."
    return {
        name: {
            "status": semantic_status(
                evidence_exists=False,
                condition_verified=None,
            ),
            "reason": reason,
        }
        for name in (
            "complete_candidate_ranking_exists",
            "complete_candidate_scores_exist",
            "every_legal_candidate_represented_once",
            "no_duplicate_candidate_in_ranking",
            "root_present_in_complete_candidate_ranking",
            "score_to_ranking_consistency",
            "deterministic_candidate_ordering",
            "score_calibration",
            "complete_candidate_level_reproducibility",
        )
    }


def _per_dataset_corrections(
    historical_full_checks: Mapping[str, str],
) -> list[Dict[str, str]]:
    mappings = (
        (
            "immutable_complete_candidate_ranking",
            "complete_candidate_ranking_exists",
            NOT_AUDITABLE,
            "No complete candidate ranking was frozen; absence cannot contradict properties of that missing object.",
        ),
        (
            "complete_candidate_scores_where_expected",
            "complete_candidate_scores_exist",
            NOT_AUDITABLE,
            "No complete candidate score object was frozen.",
        ),
        (
            "every_legal_candidate_exactly_once",
            "every_legal_candidate_represented_once",
            NOT_AUDITABLE,
            "Candidate membership cannot be evaluated without the complete ranking.",
        ),
        (
            "no_duplicate_candidate",
            "no_duplicate_candidate_in_ranking",
            NOT_AUDITABLE,
            "Duplicate absence cannot be evaluated without the complete ranking.",
        ),
        (
            "root_present",
            "root_present_in_complete_candidate_ranking",
            NOT_AUDITABLE,
            "The root mapping and legal-registry membership pass separately, but root presence in the missing full ranking is not auditable.",
        ),
        (
            "score_to_ranking_consistency",
            "score_to_ranking_consistency",
            NOT_AUDITABLE,
            "Neither complete scores nor the complete ranking were frozen.",
        ),
        (
            "deterministic_tie_and_order_consistency",
            "deterministic_candidate_ordering",
            NOT_AUDITABLE,
            "Ordering determinism cannot be evaluated without the complete ranking and scores.",
        ),
        (
            "valid_fold_and_case_provenance",
            "case_and_fold_provenance_from_root_rank_artifact",
            PASS,
            "The immutable root-rank artifact directly verifies exact case coverage, unique case IDs, valid folds, and canonical fold assignments.",
        ),
    )
    return [
        {
            "historical_check": old_name,
            "historical_status": str(historical_full_checks[old_name]),
            "canonical_check": new_name,
            "canonical_status": new_status,
            "rationale": rationale,
        }
        for old_name, new_name, new_status, rationale in mappings
    ]


def build_evidence_semantic_correction(root: Path) -> Dict[str, Any]:
    """Build the canonical semantic layer without modifying prior artifacts."""

    root = root.resolve()
    metric_path = "artifacts/evidence_closure/metric_reconstruction_v1_1.json"
    inventory_path = "artifacts/evidence_closure/input_manifest.json"
    metric = _load(root, metric_path)
    inventory = _load(root, inventory_path)

    tracks: Dict[str, Any] = {}
    correction_rows = []
    for track in ("V1-SCIENTIFIC", "GLOBAL-OPT", "PER-DATASET-OPT"):
        datasets: Dict[str, Any] = {}
        for dataset in DATASETS:
            historical = metric["evidence_levels"][track]["datasets"][dataset]
            rank_level = historical["RANK_METRIC_SUFFICIENT"]
            direct_checks = _direct_root_rank_checks(root, rank_level)
            if track == "PER-DATASET-OPT":
                ranking_checks = _per_dataset_ranking_object_checks()
                corrections = _per_dataset_corrections(
                    historical["FULL_RANKING_INTEGRITY"]["checks"]
                )
                correction_rows.extend(
                    {"track": track, "dataset": dataset, **row}
                    for row in corrections
                )
                full_status = "FULL_RANKING_INTEGRITY_NOT_AUDITABLE"
            else:
                ranking_checks = {
                    name: {
                        "status": str(status),
                        "evidence": str(rank_level["source_file"]),
                    }
                    for name, status in historical["FULL_RANKING_INTEGRITY"][
                        "checks"
                    ].items()
                }
                corrections = []
                full_status = str(historical["FULL_RANKING_INTEGRITY"]["status"])

            datasets[dataset] = {
                "FULL_RANKING_INTEGRITY": full_status,
                "RANK_METRIC_SUFFICIENT": str(rank_level["status"]),
                "ranking_object_checks": ranking_checks,
                "direct_root_rank_checks": direct_checks,
                "historical_status_corrections": corrections,
            }
        tracks[track] = {"datasets": datasets}

    status_counts = {PASS: 0, FAIL: 0, NOT_AUDITABLE: 0}
    for track in tracks.values():
        for dataset in track["datasets"].values():
            for category in ("ranking_object_checks", "direct_root_rank_checks"):
                for check in dataset[category].values():
                    status_counts[check["status"]] += 1

    return {
        "schema_version": "ada_rca_evidence_semantic_correction_v1_1",
        "audit_type": "EVIDENCE_LEVEL_SEMANTIC_CORRECTION",
        "status_definitions": STATUS_DEFINITIONS,
        "historical_artifacts": {
            metric_path: {
                "sha256": sha256_file(root / metric_path),
                "preservation": "UNCHANGED_HISTORICAL_EVIDENCE",
            },
            inventory_path: {
                "sha256": sha256_file(root / inventory_path),
                "preservation": "UNCHANGED_HISTORICAL_EVIDENCE",
            },
        },
        "tracks": tracks,
        "corrections": correction_rows,
        "summary": {
            "canonical_status_counts": status_counts,
            "genuine_fail_count": status_counts[FAIL],
            "per_dataset_full_ranking_limitation": "PERMANENT",
            "per_dataset_full_ranking_status": "FULL_RANKING_INTEGRITY_NOT_AUDITABLE",
            "per_dataset_rank_metric_status": "RANK_METRIC_SUFFICIENT_PASS",
            "canonical_interpretation_layer": True,
        },
    }
