"""Read-only evidence inventory for the Ada-RCA scientific closure audit.

This module deliberately does not import the evaluator, model, feature, or
bootstrap implementation.  Its only inputs are committed frozen artifacts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


FROZEN_COMMIT = "53c9face2c96761c9114edb558eb6d8666a38dc6"
V1_REFERENCE_COMMIT = "bed295326e567395e725caa82840a534dcc0b1de"
AMENDMENT_COMMIT = "775ec8034cad35a53c4bbe38a1093243b3050a15"
DATASETS = ("re2ob", "re2tt")
RANK_METRICS = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")
METRIC_TOLERANCE = 1e-12
TRACKS = {
    "V1-SCIENTIFIC": {
        "kind": "full",
        "path": "artifacts/final_method/{dataset}/predictions.jsonl",
        "metric_path": "artifacts/final_method/{dataset}/metrics.json",
    },
    "GLOBAL-OPT": {
        "kind": "full",
        "path": "artifacts/opt/final/GLOBAL-OPT/{dataset}/predictions.jsonl",
        "metric_path": "artifacts/opt/final/GLOBAL-OPT/{dataset}/metrics.json",
    },
    "PER-DATASET-OPT": {
        "kind": "root_rank",
        "path": "artifacts/opt/final/PER-DATASET-OPT/{dataset}/case_ranks.csv",
        "metric_path": "artifacts/opt/final/PER-DATASET-OPT/{dataset}/metrics.json",
        "replica_path": "artifacts/opt/final/PER-DATASET-OPT/{dataset}/outer_predictions.csv",
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _git(root: Path, *args: str, text: bool = True) -> Any:
    return subprocess.check_output(("git", *args), cwd=root, text=text)


def _git_blob(root: Path, commit: str, relative_path: str) -> bytes:
    return _git(root, "show", f"{commit}:{relative_path}", text=False)


def _last_modifying_commit(root: Path, relative_path: str) -> str:
    return _git(root, "log", "-1", "--format=%H", "--", relative_path).strip()


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ("git", "merge-base", "--is-ancestor", ancestor, descendant),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _path_exists_in_commit(root: Path, commit: str, relative_path: str) -> bool:
    result = subprocess.run(
        ("git", "cat-file", "-e", f"{commit}:{relative_path}"),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(value)
    return rows


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _file_record(root: Path, relative_path: str, role: str) -> Dict[str, Any]:
    path = root / relative_path
    data = path.read_bytes()
    frozen_blob = _git_blob(root, FROZEN_COMMIT, relative_path)
    if path.suffix == ".jsonl":
        row_count = len(load_jsonl(path))
    elif path.suffix == ".csv":
        row_count = len(load_csv(path))
    else:
        row_count = None
    return {
        "role": role,
        "source_file": relative_path,
        "repository_commit": FROZEN_COMMIT,
        "last_modifying_commit": _last_modifying_commit(root, relative_path),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "row_count": row_count,
        "git_blob_sha256_at_frozen_commit": sha256_bytes(frozen_blob),
        "working_copy_matches_frozen_commit": data == frozen_blob,
    }


def _source_bundle(root: Path, dataset: str) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    inputs = load_jsonl(root / f"artifacts/source/{dataset}/inputs.jsonl")
    labels = load_jsonl(root / f"artifacts/source/{dataset}/labels.jsonl")
    registry = json.loads((root / f"artifacts/source/{dataset}/service_registry.json").read_text(encoding="utf-8"))
    input_by_id = {str(row["case_id"]): row for row in inputs}
    label_by_id = {str(row["case_id"]): row for row in labels}
    if len(input_by_id) != len(inputs):
        raise ValueError(f"{dataset}: duplicate source input case IDs")
    if len(label_by_id) != len(labels):
        raise ValueError(f"{dataset}: duplicate source label case IDs")
    if set(input_by_id) != set(label_by_id):
        raise ValueError(f"{dataset}: source input/label case mismatch")
    return input_by_id, label_by_id, list(registry["services"])


def _full_prediction_audit(
    rows: Sequence[Mapping[str, Any]],
    inputs: Mapping[str, Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, Any]],
    registry: Sequence[str],
    canonical_folds: Mapping[str, int] | None,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    ids = [str(row.get("case_id")) for row in rows]
    counts = Counter(ids)
    duplicate_ids = sorted(case_id for case_id, count in counts.items() if count != 1)
    expected_ids = set(inputs)
    observed_ids = set(ids)
    fold_counts: Counter[int] = Counter()
    fold_mismatches: List[str] = []
    candidate_mismatches: List[str] = []
    root_mismatches: List[str] = []
    duplicate_ranking_entries: List[str] = []
    nondeterministic_rankings: List[str] = []
    root_absent: List[str] = []
    ranking_entries = 0

    for row in rows:
        case_id = str(row.get("case_id"))
        if case_id not in inputs or case_id not in labels:
            continue
        fold = int(row["fold"])
        fold_counts[fold] += 1
        if canonical_folds is not None and canonical_folds.get(case_id) != fold:
            fold_mismatches.append(case_id)
        expected_candidates = list(inputs[case_id]["candidates"])
        ranking = list(row.get("ranking", []))
        scores = dict(row.get("candidate_scores", {}))
        ranking_entries += len(ranking)
        if len(ranking) != len(set(ranking)):
            duplicate_ranking_entries.append(case_id)
        if set(ranking) != set(expected_candidates) or set(scores) != set(expected_candidates):
            candidate_mismatches.append(case_id)
        expected_root = str(labels[case_id]["root_service"])
        if row.get("root_service") != expected_root or row.get("fault_type") != labels[case_id]["fault_type"]:
            root_mismatches.append(case_id)
        if expected_root not in expected_candidates or expected_root not in ranking:
            root_absent.append(case_id)
        if set(scores) == set(expected_candidates):
            deterministic = sorted(expected_candidates, key=lambda candidate: (-float(scores[candidate]), candidate))
            if ranking != deterministic:
                nondeterministic_rankings.append(case_id)

    registry_consistent = all(list(row["candidates"]) == list(registry) for row in inputs.values())
    complete = (
        not duplicate_ids
        and observed_ids == expected_ids
        and not candidate_mismatches
        and not duplicate_ranking_entries
        and not root_absent
    )
    integrity = {
        "event_id_uniqueness": "PASS" if not duplicate_ids else "FAIL",
        "duplicate_event_ids": duplicate_ids,
        "expected_case_coverage": "PASS" if observed_ids == expected_ids else "FAIL",
        "missing_case_ids": sorted(expected_ids - observed_ids),
        "unexpected_case_ids": sorted(observed_ids - expected_ids),
        "event_count": len(rows),
        "expected_event_count": len(inputs),
        "fold_coverage": {str(fold): fold_counts[fold] for fold in sorted(fold_counts)},
        "fold_assignments_valid": "PASS" if set(fold_counts) == {0, 1, 2} and not fold_mismatches else "FAIL",
        "fold_assignment_mismatches": sorted(fold_mismatches),
        "candidate_registry_count": len(registry),
        "candidate_registry_consistency": "PASS" if registry_consistent else "FAIL",
        "candidate_coverage": {
            "expected_candidate_case_pairs": sum(len(row["candidates"]) for row in inputs.values()),
            "observed_ranking_entries": ranking_entries,
            "status": "PASS" if not candidate_mismatches else "FAIL",
            "mismatched_case_ids": sorted(candidate_mismatches),
        },
        "duplicate_ranking_entries": "PASS" if not duplicate_ranking_entries else "FAIL",
        "duplicate_ranking_case_ids": sorted(duplicate_ranking_entries),
        "root_mapping_consistency": "PASS" if not root_mismatches else "FAIL",
        "root_mapping_mismatches": sorted(root_mismatches),
        "root_presence": "PASS" if not root_absent else "FAIL",
        "root_absent_case_ids": sorted(root_absent),
        "ranking_completeness": "PASS" if complete else "FAIL",
        "ranking_deterministic": "PASS" if not nondeterministic_rankings else "FAIL",
        "nondeterministic_case_ids": sorted(nondeterministic_rankings),
        "full_prediction_ranking_evidence_exists": True,
        "frozen_prediction_status": "AVAILABLE",
    }
    return integrity, {case_id: int(row["fold"]) for case_id, row in ((str(r["case_id"]), r) for r in rows)}


def _root_rank_audit(
    rows: Sequence[Mapping[str, str]],
    inputs: Mapping[str, Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, Any]],
    registry: Sequence[str],
    canonical_folds: Mapping[str, int],
) -> Dict[str, Any]:
    ids = [str(row.get("case_id")) for row in rows]
    counts = Counter(ids)
    duplicate_ids = sorted(case_id for case_id, count in counts.items() if count != 1)
    expected_ids = set(inputs)
    observed_ids = set(ids)
    fold_counts: Counter[int] = Counter()
    fold_mismatches: List[str] = []
    root_mismatches: List[str] = []
    invalid_root_ranks: List[str] = []
    root_absent: List[str] = []
    for row in rows:
        case_id = str(row.get("case_id"))
        if case_id not in inputs or case_id not in labels:
            continue
        fold = int(row["fold"])
        fold_counts[fold] += 1
        if canonical_folds.get(case_id) != fold:
            fold_mismatches.append(case_id)
        expected_root = str(labels[case_id]["root_service"])
        if row.get("root_service") != expected_root or row.get("fault_type") != labels[case_id]["fault_type"]:
            root_mismatches.append(case_id)
        candidates = list(inputs[case_id]["candidates"])
        if expected_root not in candidates:
            root_absent.append(case_id)
        try:
            root_rank = int(row["root_rank"])
        except (KeyError, TypeError, ValueError):
            invalid_root_ranks.append(case_id)
        else:
            if not 1 <= root_rank <= len(candidates):
                invalid_root_ranks.append(case_id)
    registry_consistent = all(list(row["candidates"]) == list(registry) for row in inputs.values())
    return {
        "event_id_uniqueness": "PASS" if not duplicate_ids else "FAIL",
        "duplicate_event_ids": duplicate_ids,
        "expected_case_coverage": "PASS" if observed_ids == expected_ids else "FAIL",
        "missing_case_ids": sorted(expected_ids - observed_ids),
        "unexpected_case_ids": sorted(observed_ids - expected_ids),
        "event_count": len(rows),
        "expected_event_count": len(inputs),
        "fold_coverage": {str(fold): fold_counts[fold] for fold in sorted(fold_counts)},
        "fold_assignments_valid": "PASS" if set(fold_counts) == {0, 1, 2} and not fold_mismatches else "FAIL",
        "fold_assignment_mismatches": sorted(fold_mismatches),
        "candidate_registry_count": len(registry),
        "candidate_registry_consistency": "PASS" if registry_consistent else "FAIL",
        "candidate_coverage": {
            "expected_candidate_case_pairs": sum(len(row["candidates"]) for row in inputs.values()),
            "observed_ranking_entries": 0,
            "status": "NOT_AUDITABLE_FROM_ROOT_RANK_ONLY",
            "mismatched_case_ids": [],
        },
        "duplicate_ranking_entries": "NOT_AUDITABLE_FROM_ROOT_RANK_ONLY",
        "duplicate_ranking_case_ids": [],
        "root_mapping_consistency": "PASS" if not root_mismatches else "FAIL",
        "root_mapping_mismatches": sorted(root_mismatches),
        "root_presence": "PASS" if not root_absent else "FAIL",
        "root_absent_case_ids": sorted(root_absent),
        "root_rank_range": "PASS" if not invalid_root_ranks else "FAIL",
        "invalid_root_rank_case_ids": sorted(invalid_root_ranks),
        "ranking_completeness": "FAIL",
        "ranking_deterministic": "NOT_AUDITABLE_FROM_ROOT_RANK_ONLY",
        "full_prediction_ranking_evidence_exists": False,
        "frozen_prediction_status": "FROZEN_PREDICTION_EVIDENCE_UNAVAILABLE",
    }


def build_input_manifest(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    frozen_head = _git(root, "rev-parse", FROZEN_COMMIT).strip()
    v1_head = _git(root, "rev-parse", V1_REFERENCE_COMMIT).strip()
    evidence: Dict[str, Any] = {}
    canonical_folds: Dict[str, Dict[str, int]] = {}
    fatal_defects: List[Dict[str, str]] = []

    for track, spec in TRACKS.items():
        track_record: Dict[str, Any] = {"datasets": {}}
        for dataset in DATASETS:
            inputs, labels, registry = _source_bundle(root, dataset)
            relative_path = str(spec["path"]).format(dataset=dataset)
            files = [
                _file_record(root, relative_path, "frozen_prediction_or_rank"),
                _file_record(root, str(spec["metric_path"]).format(dataset=dataset), "legacy_final_metrics"),
                _file_record(root, f"artifacts/source/{dataset}/inputs.jsonl", "case_and_candidate_registry"),
                _file_record(root, f"artifacts/source/{dataset}/labels.jsonl", "root_and_fault_sidecar"),
                _file_record(root, f"artifacts/source/{dataset}/service_registry.json", "candidate_registry"),
            ]
            if spec["kind"] == "full":
                rows = load_jsonl(root / relative_path)
                audit, folds = _full_prediction_audit(
                    rows,
                    inputs,
                    labels,
                    registry,
                    canonical_folds.get(dataset),
                )
                if track == "V1-SCIENTIFIC":
                    canonical_folds[dataset] = folds
            else:
                replica_path = str(spec["replica_path"]).format(dataset=dataset)
                files.append(_file_record(root, replica_path, "root_rank_replica"))
                rows = load_csv(root / relative_path)
                audit = _root_rank_audit(rows, inputs, labels, registry, canonical_folds[dataset])
                audit["root_rank_replica_byte_identical"] = (root / relative_path).read_bytes() == (root / replica_path).read_bytes()
            dataset_fatals: List[str] = []
            if audit["frozen_prediction_status"] != "AVAILABLE":
                dataset_fatals.append("FROZEN_PREDICTION_EVIDENCE_UNAVAILABLE")
            for field in (
                "event_id_uniqueness",
                "expected_case_coverage",
                "fold_assignments_valid",
                "candidate_registry_consistency",
                "root_mapping_consistency",
                "root_presence",
                "ranking_completeness",
            ):
                if audit[field] == "FAIL":
                    dataset_fatals.append(f"{field.upper()}_FAILURE")
            dataset_fatals = sorted(set(dataset_fatals))
            for defect in dataset_fatals:
                fatal_defects.append({"track": track, "dataset": dataset, "defect": defect})
            track_record["datasets"][dataset] = {
                "source_files": files,
                "integrity": audit,
                "fatal_defects": dataset_fatals,
            }
        evidence[track] = track_record

    v1_sha: Dict[str, Any] = {}
    for dataset in DATASETS:
        current = root / f"artifacts/final_method/{dataset}/predictions.jsonl"
        at_v1 = _git_blob(root, V1_REFERENCE_COMMIT, f"artifacts/final_method/{dataset}/predictions.jsonl")
        v1_sha[dataset] = {
            "current_sha256": sha256_file(current),
            "v1_reference_commit_sha256": sha256_bytes(at_v1),
            "byte_identical": current.read_bytes() == at_v1,
        }

    status = "PASS" if not fatal_defects else "FAIL"
    return {
        "schema_version": "ada_rca_evidence_closure_input_manifest_v1",
        "audit_type": "READ_ONLY_FROZEN_EVIDENCE_INVENTORY",
        "frozen_repository_commit": frozen_head,
        "v1_scientific_reference_commit": v1_head,
        "v1_reference_traceability": {
            "reference_is_ancestor_of_frozen_commit": _is_ancestor(root, V1_REFERENCE_COMMIT, FROZEN_COMMIT),
            "prediction_artifact_identity": v1_sha,
        },
        "evidence": evidence,
        "gate_0": {
            "status": status,
            "fatal_defects": fatal_defects,
            "terminal_state_if_unresolved": "RCA_EVIDENCE_NOT_CLOSED" if fatal_defects else None,
            "downstream_gate_authorization": "STOP" if fatal_defects else "GATE_1_AUTHORIZED",
        },
    }


def load_frozen_rank_cases(root: Path, track: str, dataset: str) -> List[Dict[str, Any]]:
    """Load only the immutable case quantities needed by rank-derived metrics.

    Complete-ranking tracks derive the root rank from the frozen ranking.  The
    PER-DATASET track reads the committed root-rank CSV directly.  This path
    performs no model, feature, score, or evaluator call.
    """

    root = root.resolve()
    if track not in TRACKS:
        raise ValueError(f"unknown track: {track}")
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset: {dataset}")
    inputs, labels, _ = _source_bundle(root, dataset)
    spec = TRACKS[track]
    relative_path = str(spec["path"]).format(dataset=dataset)
    cases: List[Dict[str, Any]] = []
    if spec["kind"] == "full":
        rows: Sequence[Mapping[str, Any]] = load_jsonl(root / relative_path)
        for row in rows:
            case_id = str(row["case_id"])
            canonical_root = str(labels[case_id]["root_service"])
            ranking = [str(candidate) for candidate in row["ranking"]]
            if canonical_root not in ranking:
                raise ValueError(f"{track}/{dataset}/{case_id}: root absent from ranking")
            cases.append(
                {
                    "case_id": case_id,
                    "fold": int(row["fold"]),
                    "root_service": canonical_root,
                    "fault_type": str(labels[case_id]["fault_type"]),
                    "root_rank": ranking.index(canonical_root) + 1,
                    "candidate_count": len(inputs[case_id]["candidates"]),
                }
            )
    else:
        rows = load_csv(root / relative_path)
        for row in rows:
            case_id = str(row["case_id"])
            raw_rank = str(row["root_rank"])
            if not raw_rank.isdigit():
                raise ValueError(f"{track}/{dataset}/{case_id}: root rank is not an integer")
            cases.append(
                {
                    "case_id": case_id,
                    "fold": int(row["fold"]),
                    "root_service": str(row["root_service"]),
                    "fault_type": str(row["fault_type"]),
                    "root_rank": int(raw_rank),
                    "candidate_count": len(inputs[case_id]["candidates"]),
                }
            )
    return sorted(cases, key=lambda row: row["case_id"])


def _status_checks(checks: Mapping[str, bool]) -> Dict[str, str]:
    return {name: "PASS" if value else "FAIL" for name, value in checks.items()}


def classify_evidence_levels(root: Path) -> Dict[str, Any]:
    """Classify claim-specific frozen evidence under Amendment V1.1."""

    root = root.resolve()
    inventory = build_input_manifest(root)
    v1_cases = {
        dataset: load_frozen_rank_cases(root, "V1-SCIENTIFIC", dataset)
        for dataset in DATASETS
    }
    canonical_folds = {
        dataset: {str(row["case_id"]): int(row["fold"]) for row in cases}
        for dataset, cases in v1_cases.items()
    }
    levels: Dict[str, Any] = {}
    for track, spec in TRACKS.items():
        by_dataset: Dict[str, Any] = {}
        for dataset in DATASETS:
            record = inventory["evidence"][track]["datasets"][dataset]
            integrity = record["integrity"]
            source = record["source_files"][0]
            cases = load_frozen_rank_cases(root, track, dataset)
            case_ids = [str(row["case_id"]) for row in cases]
            folds = Counter(int(row["fold"]) for row in cases)
            inputs, labels, registry = _source_bundle(root, dataset)
            mappings_valid = all(
                row["root_service"] == str(labels[row["case_id"]]["root_service"])
                and row["fault_type"] == str(labels[row["case_id"]]["fault_type"])
                for row in cases
            )
            roots_legal = all(
                row["root_service"] in inputs[row["case_id"]]["candidates"]
                and row["root_service"] in registry
                for row in cases
            )
            ranks_integer = all(
                isinstance(row["root_rank"], int) and not isinstance(row["root_rank"], bool)
                for row in cases
            )
            ranks_in_range = all(
                1 <= int(row["root_rank"]) <= int(row["candidate_count"])
                for row in cases
            )
            relative_path = str(spec["path"]).format(dataset=dataset)
            last_commit = str(source["last_modifying_commit"])
            rank_checks = {
                "committed_immutable_root_rank_source": bool(
                    source["working_copy_matches_frozen_commit"]
                    and source["sha256"] == source["git_blob_sha256_at_frozen_commit"]
                ),
                "sha256_recorded": len(str(source["sha256"])) == 64,
                "exact_expected_90_cases": len(cases) == 90 and set(case_ids) == set(inputs),
                "unique_case_ids": len(case_ids) == len(set(case_ids)),
                "valid_folds": folds == Counter({0: 30, 1: 30, 2: 30}),
                "fold_assignment_consistency": all(
                    canonical_folds[dataset].get(row["case_id"]) == row["fold"] for row in cases
                ),
                "root_mapping_consistency": mappings_valid,
                "root_belongs_to_legal_candidate_registry": roots_legal,
                "root_rank_integer": ranks_integer,
                "root_rank_range": ranks_in_range,
                "no_model_refit_required": spec["kind"] in {"full", "root_rank"},
                "traceable_to_frozen_optimization_commit": bool(
                    _path_exists_in_commit(root, FROZEN_COMMIT, relative_path)
                    and _is_ancestor(root, last_commit, FROZEN_COMMIT)
                ),
                "no_post_audit_root_rank_modification": bool(
                    source["working_copy_matches_frozen_commit"]
                ),
            }
            full_checks = {
                "immutable_complete_candidate_ranking": bool(
                    spec["kind"] == "full"
                    and source["working_copy_matches_frozen_commit"]
                    and integrity["ranking_completeness"] == "PASS"
                ),
                "complete_candidate_scores_where_expected": bool(
                    spec["kind"] == "full"
                    and integrity["candidate_coverage"]["status"] == "PASS"
                ),
                "every_legal_candidate_exactly_once": bool(
                    spec["kind"] == "full"
                    and integrity["candidate_coverage"]["status"] == "PASS"
                    and integrity["duplicate_ranking_entries"] == "PASS"
                ),
                "no_duplicate_candidate": bool(
                    spec["kind"] == "full"
                    and integrity["duplicate_ranking_entries"] == "PASS"
                ),
                "root_present": bool(spec["kind"] == "full" and integrity["root_presence"] == "PASS"),
                "score_to_ranking_consistency": bool(
                    spec["kind"] == "full" and integrity["ranking_deterministic"] == "PASS"
                ),
                "deterministic_tie_and_order_consistency": bool(
                    spec["kind"] == "full" and integrity["ranking_deterministic"] == "PASS"
                ),
                "valid_fold_and_case_provenance": bool(
                    spec["kind"] == "full"
                    and integrity["event_id_uniqueness"] == "PASS"
                    and integrity["expected_case_coverage"] == "PASS"
                    and integrity["fold_assignments_valid"] == "PASS"
                    and integrity["root_mapping_consistency"] == "PASS"
                ),
            }
            if spec["kind"] != "full":
                full_status = "FULL_RANKING_INTEGRITY_NOT_AUDITABLE"
            elif all(full_checks.values()):
                full_status = "FULL_RANKING_INTEGRITY_PASS"
            else:
                full_status = "FULL_RANKING_INTEGRITY_FAIL"
            rank_status = (
                "RANK_METRIC_SUFFICIENT_PASS"
                if all(rank_checks.values())
                else "RANK_METRIC_SUFFICIENT_FAIL"
            )
            normalized_cases = json.dumps(cases, sort_keys=True, separators=(",", ":")).encode("utf-8")
            by_dataset[dataset] = {
                "FULL_RANKING_INTEGRITY": {
                    "status": full_status,
                    "checks": _status_checks(full_checks),
                    "limitation": (
                        "None"
                        if full_status == "FULL_RANKING_INTEGRITY_PASS"
                        else "Complete candidate scores/rankings are absent; candidate-level integrity is not auditable."
                    ),
                },
                "RANK_METRIC_SUFFICIENT": {
                    "status": rank_status,
                    "checks": _status_checks(rank_checks),
                    "source_file": relative_path,
                    "source_kind": (
                        "complete_frozen_ranking_root_rank_derived"
                        if spec["kind"] == "full"
                        else "immutable_root_rank_artifact"
                    ),
                    "source_sha256": source["sha256"],
                    "frozen_commit": FROZEN_COMMIT,
                    "last_modifying_commit": last_commit,
                    "case_quantity_sha256": sha256_bytes(normalized_cases),
                },
            }
        levels[track] = {"datasets": by_dataset}
    return levels


def independent_case_metrics(root_rank: int) -> Dict[str, float]:
    """Compute a case's five metrics using only its one-indexed root rank."""

    if isinstance(root_rank, bool) or not isinstance(root_rank, int) or root_rank < 1:
        raise ValueError("root_rank must be a positive integer")
    return {
        "AC@1": float(root_rank <= 1),
        "AC@3": float(root_rank <= 3),
        "AC@5": float(root_rank <= 5),
        "Avg@5": sum(float(root_rank <= k) for k in range(1, 6)) / 5.0,
        "MRR": 1.0 / float(root_rank),
    }


def aggregate_independent_rank_metrics(cases: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    """Aggregate case metrics without importing or calling the legacy evaluator."""

    if not cases:
        raise ValueError("cannot aggregate zero cases")
    per_case = [independent_case_metrics(int(row["root_rank"])) for row in cases]
    return {
        metric: sum(row[metric] for row in per_case) / float(len(per_case))
        for metric in RANK_METRICS
    }


def build_metric_reconstruction(root: Path) -> Dict[str, Any]:
    """Build Gate 1 from immutable rank quantities and legacy summaries."""

    root = root.resolve()
    evidence_levels = classify_evidence_levels(root)
    comparisons: Dict[str, Any] = {}
    all_rank_evidence_pass = True
    all_legacy_metrics_match = True
    for track, spec in TRACKS.items():
        datasets: Dict[str, Any] = {}
        for dataset in DATASETS:
            level = evidence_levels[track]["datasets"][dataset]
            rank_pass = level["RANK_METRIC_SUFFICIENT"]["status"] == "RANK_METRIC_SUFFICIENT_PASS"
            all_rank_evidence_pass = all_rank_evidence_pass and rank_pass
            if not rank_pass:
                datasets[dataset] = {
                    "status": "NOT_COMPUTED_RANK_EVIDENCE_FAILURE",
                    "evidence_levels": level,
                }
                continue
            cases = load_frozen_rank_cases(root, track, dataset)
            independent = aggregate_independent_rank_metrics(cases)
            legacy_path = str(spec["metric_path"]).format(dataset=dataset)
            legacy_document = json.loads((root / legacy_path).read_text(encoding="utf-8"))
            legacy = {metric: float(legacy_document["overall_cases"][metric]) for metric in RANK_METRICS}
            metric_comparison: Dict[str, Any] = {}
            for metric in RANK_METRICS:
                difference = abs(independent[metric] - legacy[metric])
                status = "PASS" if difference <= METRIC_TOLERANCE else "FAIL"
                all_legacy_metrics_match = all_legacy_metrics_match and status == "PASS"
                metric_comparison[metric] = {
                    "independent_metric": independent[metric],
                    "legacy_metric": legacy[metric],
                    "absolute_difference": difference,
                    "tolerance": METRIC_TOLERANCE,
                    "status": status,
                }
            datasets[dataset] = {
                "status": (
                    "PASS"
                    if all(item["status"] == "PASS" for item in metric_comparison.values())
                    else "FAIL"
                ),
                "evidence_levels": level,
                "case_count": len(cases),
                "metric_comparison": metric_comparison,
                "legacy_metric_source": {
                    "path": legacy_path,
                    "sha256": sha256_file(root / legacy_path),
                },
            }
        comparisons[track] = {"datasets": datasets}
    gate_pass = all_rank_evidence_pass and all_legacy_metrics_match
    input_manifest_path = root / "artifacts/evidence_closure/input_manifest.json"
    evaluator_path = root / "src/rca/evaluator.py"
    corrected_paths = (
        "artifacts/evidence_closure/metric_reconstruction_v1_1.json",
        "artifacts/evidence_closure/bootstrap_corrected_v1_1.json",
    )
    return {
        "schema_version": "ada_rca_metric_reconstruction_v1_1",
        "audit_type": "INDEPENDENT_FROZEN_RANK_METRIC_RECONSTRUCTION",
        "protocol_amendment": {
            "status": "POST-AUDIT PROTOCOL CLARIFICATION",
            "path": "docs/RCA_EVIDENCE_CLOSURE_PROTOCOL_AMENDMENT_V1_1.md",
            "commit": AMENDMENT_COMMIT,
            "commit_is_ancestor_of_execution_head": _is_ancestor(
                root, AMENDMENT_COMMIT, _git(root, "rev-parse", "HEAD").strip()
            ),
            "corrected_outputs_absent_at_amendment_commit": {
                path: not _path_exists_in_commit(root, AMENDMENT_COMMIT, path)
                for path in corrected_paths
            },
        },
        "frozen_input_manifest": {
            "path": "artifacts/evidence_closure/input_manifest.json",
            "sha256": sha256_file(input_manifest_path),
        },
        "metric_definition_verification": {
            "scientific_protocol": "docs/RCA_FINAL_EVALUATION_PROTOCOL_V1.0.md section 3",
            "legacy_definition_source": "src/rca/evaluator.py",
            "legacy_definition_source_sha256": sha256_file(evaluator_path),
            "formulas": {
                "AC@k": "AC@k = (1/N) * sum_i 1[root_rank_i <= k], for k in {1,3,5}",
                "Avg@5": "Avg@5 = (1/N) * sum_i ((1/5) * sum_{k=1}^5 1[root_rank_i <= k])",
                "MRR": "MRR = (1/N) * sum_i (1/root_rank_i)",
            },
            "implementation": "Independent root-rank implementation; no import or call to src.rca.evaluator",
        },
        "evidence_levels": evidence_levels,
        "tracks": comparisons,
        "gate_1": {
            "status": "PASS" if gate_pass else "FAIL",
            "rank_evidence_status": "PASS" if all_rank_evidence_pass else "FAIL",
            "legacy_metric_consistency": "PASS" if all_legacy_metrics_match else "FAIL",
            "bootstrap_authorization": "GATE_2_AUTHORIZED" if gate_pass else "STOP",
            "terminal_state_if_failed": "RCA_EVIDENCE_NOT_CLOSED" if not gate_pass else None,
        },
    }


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
