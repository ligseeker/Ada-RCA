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
DATASETS = ("re2ob", "re2tt")
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


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

