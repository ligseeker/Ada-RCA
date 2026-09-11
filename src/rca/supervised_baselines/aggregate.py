"""Strict fold aggregation, paired bootstrap, and the preregistered DejaVu gate."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple

from ..p4_stats import evaluate_predictions, paired_fault_stratified_bootstrap
from .common import (
    EXPECTED_CANDIDATES,
    EXPECTED_CASES,
    FOLDS,
    FROZEN_SHA256,
    load_prediction_events,
    read_json,
    sha256_file,
    write_json,
    write_jsonl,
)


METHODS = ("logistic", "xgb_ranker", "tcn")
FINAL_METRICS_SHA256 = {
    "re2ob": "080a4035753de2d9c8eeb15e9f4d18d43be34116ee9a3b7e0954ed797f5a43d1",
    "re2tt": "7dfcafc271420df860877e11c87778fba32a75793a3006a5ab48d3fad4f5ef5c",
}


def _read_jsonl(path: Path):
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _verify_checksums(run_dir: Path) -> None:
    checksums = read_json(run_dir / "checksums.json")
    if not checksums:
        raise ValueError("empty fold checksum manifest")
    for relative, expected in checksums.items():
        if sha256_file(run_dir / relative) != expected:
            raise ValueError("fold artifact checksum mismatch: {}".format(run_dir / relative))


def _load_fold_rows(
    artifact_root: Path, method: str, dataset: str, fold: int
) -> Tuple[Mapping[str, object], ...]:
    run_dir = artifact_root / method / dataset / "fold_{}".format(fold)
    if read_json(run_dir / "status.json")["status"] != "COMPLETE":
        raise ValueError("fold is not complete: {}".format(run_dir))
    _verify_checksums(run_dir)
    integrity = read_json(run_dir / "integrity.json")
    firewall = read_json(run_dir / "label_firewall.json")
    if integrity["status"] != "PASS" or firewall["status"] != "PASS":
        raise ValueError("fold integrity or firewall did not pass")
    rows = _read_jsonl(run_dir / "predictions.jsonl")
    expected = 30 * EXPECTED_CANDIDATES[dataset]
    if len(rows) != expected or {int(row["fold"]) for row in rows} != {fold}:
        raise ValueError("fold candidate-row coverage mismatch")
    return rows


def aggregate_method_dataset(
    project_root: Path, artifact_root: Path, method: str, dataset: str
) -> Mapping[str, object]:
    if method not in METHODS:
        raise ValueError("unsupported supervised comparator")
    events = load_prediction_events(project_root, dataset)
    all_rows = tuple(
        row for fold in FOLDS for row in _load_fold_rows(artifact_root, method, dataset, fold)
    )
    by_case: Dict[str, list] = {}
    for row in all_rows:
        by_case.setdefault(str(row["case_id"]), []).append(row)
    if set(by_case) != set(events) or len(by_case) != EXPECTED_CASES:
        raise ValueError("aggregate case universe mismatch")

    prediction_rows = []
    candidates_by_case = {}
    roots = {}
    for case_id in sorted(by_case):
        rows = sorted(by_case[case_id], key=lambda row: int(row["rank"]))
        event = events[case_id]
        ranking = tuple(str(row["candidate"]) for row in rows)
        if len(rows) != len(event.candidates) or set(ranking) != set(event.candidates):
            raise ValueError("aggregate ranking is not a complete candidate permutation")
        if [int(row["rank"]) for row in rows] != list(range(1, len(rows) + 1)):
            raise ValueError("aggregate ranks are not contiguous")
        root_values = {str(row["root_service"]) for row in rows}
        root_rank_values = {int(row["root_rank"]) for row in rows}
        fault_values = {str(row["fault_type"]) for row in rows}
        if len(root_values) != 1 or len(root_rank_values) != 1 or len(fault_values) != 1:
            raise ValueError("post-evaluation labels are inconsistent within a case")
        root = next(iter(root_values))
        if ranking.index(root) + 1 != next(iter(root_rank_values)):
            raise ValueError("root rank does not match complete ranking")
        score_map = {str(row["candidate"]): float(row["score"]) for row in rows}
        prediction_rows.append({
            "case_id": case_id,
            "dataset": dataset,
            "fault_type": next(iter(fault_values)),
            "fold": event.fold,
            "root_service": root,
            "candidate_scores": score_map,
            "ranking": list(ranking),
        })
        candidates_by_case[case_id] = event.candidates
        roots[case_id] = root
    metrics = evaluate_predictions(prediction_rows, candidates_by_case, roots)

    final_metrics_path = project_root / "artifacts" / "final_method" / dataset / "metrics.json"
    if sha256_file(final_metrics_path) != FINAL_METRICS_SHA256[dataset]:
        raise ValueError("frozen Ada-RCA metric artifact digest mismatch")
    ada_metrics = read_json(final_metrics_path)
    baseline_cases = {row["case_id"]: row for row in metrics["case_metrics"]}
    ada_cases = {row["case_id"]: row for row in ada_metrics["case_metrics"]}
    bootstrap = paired_fault_stratified_bootstrap(
        baseline_cases, ada_cases, metric="Avg@5", resamples=10000, seed=20260826
    )
    bootstrap["direction"] = "supervised_baseline_minus_ada_rca_v1"

    aggregate_dir = artifact_root / method / dataset / "aggregate"
    if aggregate_dir.exists():
        raise FileExistsError("aggregate output already exists: {}".format(aggregate_dir))
    aggregate_dir.mkdir(parents=True)
    write_jsonl(aggregate_dir / "predictions.jsonl", all_rows)
    write_json(aggregate_dir / "metrics.json", metrics)
    write_json(aggregate_dir / "paired_bootstrap.json", bootstrap)
    write_json(aggregate_dir / "integrity.json", {
        "status": "PASS",
        "case_count": len(by_case),
        "candidate_row_count": len(all_rows),
        "expected_candidate_row_count": EXPECTED_CASES * EXPECTED_CANDIDATES[dataset],
        "folds": list(FOLDS),
        "complete_candidate_rankings": True,
    })
    write_json(aggregate_dir / "provenance.json", {
        "schema_version": "supervised_baseline_aggregate_v1",
        "method": method,
        "dataset": dataset,
        "fold_directories": ["fold_{}".format(fold) for fold in FOLDS],
        "frozen_input_sha256": FROZEN_SHA256[dataset],
        "ada_rca_metrics_sha256": FINAL_METRICS_SHA256[dataset],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    checksums = {
        path.name: sha256_file(path)
        for path in sorted(aggregate_dir.iterdir())
        if path.is_file() and path.name != "checksums.json"
    }
    write_json(aggregate_dir / "checksums.json", checksums)
    return {
        "method": method,
        "dataset": dataset,
        "metrics": metrics["overall_cases"],
        "bootstrap": bootstrap,
        "aggregate_dir": str(aggregate_dir),
    }


def evaluate_dejavu_gate(project_root: Path, artifact_root: Path) -> Mapping[str, object]:
    missing = []
    comparator_metrics: Dict[str, Dict[str, Mapping[str, float]]] = {}
    for method in METHODS:
        comparator_metrics[method] = {}
        for dataset in ("re2ob", "re2tt"):
            path = artifact_root / method / dataset / "aggregate" / "metrics.json"
            if not path.is_file():
                missing.append("{}/{}".format(method, dataset))
                continue
            comparator_metrics[method][dataset] = read_json(path)["overall_cases"]
    ada = {}
    for dataset in ("re2ob", "re2tt"):
        path = project_root / "artifacts" / "final_method" / dataset / "metrics.json"
        if sha256_file(path) != FINAL_METRICS_SHA256[dataset]:
            raise ValueError("frozen Ada-RCA metric artifact digest mismatch")
        ada[dataset] = read_json(path)["overall_cases"]
    if missing:
        return {
            "decision": "PENDING",
            "reason": "generic supervised comparator aggregates are incomplete",
            "missing": missing,
            "primary_metric": "Avg@5",
            "ada_rca_v1": ada,
        }
    dominance = {}
    for method in METHODS:
        dominance[method] = {
            dataset: float(comparator_metrics[method][dataset]["Avg@5"])
            > float(ada[dataset]["Avg@5"])
            for dataset in ("re2ob", "re2tt")
        }
        dominance[method]["both_datasets"] = all(dominance[method].values())
    failed = any(row["both_datasets"] for row in dominance.values())
    return {
        "decision": "FAIL" if failed else "PASS",
        "definition": "FAIL iff one generic comparator strictly exceeds Ada-RCA V1 Avg@5 on both datasets",
        "primary_metric": "Avg@5",
        "ada_rca_v1": ada,
        "comparators": comparator_metrics,
        "strict_dominance_checks": dominance,
        "statistical_significance_gate": False,
    }


def persist_dejavu_gate(
    artifact_root: Path, gate: Mapping[str, object], filename: str = "dejavu_gate.json"
) -> Path:
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise ValueError("gate filename must be a simple JSON filename")
    path = artifact_root / filename
    if path.exists():
        raise FileExistsError("DejaVu gate artifact already exists")
    write_json(path, gate)
    return path
