#!/usr/bin/env python3
"""Fail-closed validation for the frozen Ada-RCA V1 thesis asset package.

The validator checks source identity, package completeness, manifest hashes,
independent case-rank reconstruction, numerical/replay integrity, evidence
class boundaries, and exclusion of superseded or baseline material.  It is
read-only and never imports a model runner or computes a new model fit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from export_thesis_assets import (  # noqa: E402
    DATASETS,
    DOCUMENT_CLASSES,
    EXPECTED_CANDIDATES,
    EXPECTED_CASES,
    EXPECTED_FINAL,
    FAULT_ORDER,
    PACKAGE_REL,
    SOURCE_COMMIT,
    TOLERANCE,
    aggregate,
    exact_float_equal,
    feature_schema,
    git_blob,
    json_load,
    jsonl_load,
    load_final_case_rows,
    run_git,
    sha256_bytes,
    sha256_file,
)


class ValidationState:
    def __init__(self) -> None:
        self.failures: List[str] = []
        self.checks: List[str] = []

    def check(self, condition: bool, name: str, detail: str = "") -> None:
        if condition:
            self.checks.append(name)
        else:
            self.failures.append(f"{name}: {detail}" if detail else name)


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_float(value: Any) -> float:
    return float(str(value))


def source_bytes(repo: Path, commit: str, relative: str) -> bytes:
    return run_git(repo, "show", f"{commit}:{relative}", text=False)


def manifest_source_check(repo: Path, row: Mapping[str, str], state: ValidationState) -> None:
    source_paths = [item for item in row.get("source_path", "").split(";") if item]
    blob_values = [item for item in row.get("source_blob_sha", "").split(";") if item]
    file_values = [item for item in row.get("source_file_sha256", "").split(";") if item]
    state.check(bool(source_paths), f"manifest source paths: {row.get('asset_path', '')}")
    state.check(len(source_paths) == len(blob_values), f"manifest source blob cardinality: {row.get('asset_path', '')}")
    state.check(len(source_paths) == len(file_values), f"manifest source file cardinality: {row.get('asset_path', '')}")
    if len(source_paths) != len(blob_values) or len(source_paths) != len(file_values):
        return
    source_commit = row.get("source_commit", "")
    for relative, expected_blob, expected_file in zip(source_paths, blob_values, file_values):
        state.check("baseline_eval" not in relative, f"manifest baseline exclusion: {row.get('asset_path', '')}", relative)
        try:
            actual_blob = git_blob(repo, source_commit, relative)
            data = source_bytes(repo, source_commit, relative)
        except Exception as exc:  # pragma: no cover - reported as a validation failure
            state.failures.append(f"manifest source exists: {relative}: {exc}")
            continue
        state.check(actual_blob == expected_blob, f"manifest source Git blob: {relative}")
        state.check(sha256_bytes(data) == expected_file, f"manifest source file hash: {relative}")


def validate_manifest(repo: Path, package: Path, state: ValidationState) -> List[Dict[str, str]]:
    manifest_path = package / "MANIFEST.csv"
    state.check(manifest_path.is_file(), "MANIFEST.csv exists")
    if not manifest_path.is_file():
        return []
    fields, rows = read_csv(manifest_path)
    required = {"asset_path", "source_path", "source_commit", "source_blob_sha", "source_file_sha256", "asset_sha256", "evidence_class", "derived_or_copied"}
    state.check(required.issubset(fields), "MANIFEST.csv schema", f"missing={sorted(required - set(fields))}")
    assets = [row.get("asset_path", "") for row in rows]
    state.check(len(assets) == len(set(assets)), "manifest asset paths unique")
    package_files = sorted(
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file() and path.relative_to(package).as_posix() != "MANIFEST.csv"
    )
    state.check(sorted(assets) == package_files, "manifest covers every package file", f"missing={sorted(set(package_files)-set(assets))[:5]} unexpected={sorted(set(assets)-set(package_files))[:5]}")
    for row in rows:
        asset_rel = row.get("asset_path", "")
        asset_path = package / asset_rel
        state.check(asset_path.is_file(), f"manifest asset exists: {asset_rel}")
        if asset_path.is_file():
            state.check(sha256_file(asset_path) == row.get("asset_sha256", ""), f"manifest asset hash: {asset_rel}")
        manifest_source_check(repo, row, state)
        source_commit = row.get("source_commit", "")
        try:
            run_git(repo, "cat-file", "-e", f"{source_commit}^{{commit}}")
            commit_exists = True
        except Exception:
            commit_exists = False
        state.check(commit_exists, f"manifest source commit: {asset_rel}")
        state.check(row.get("evidence_class") in {"CANONICAL", "SUPPORTING", "DEVELOPMENT", "DIAGNOSTIC", "HISTORICAL_SUPERSEDED", "OUT_OF_SCOPE", "DESCRIPTIVE"}, f"manifest evidence class: {asset_rel}")
    return rows


def validate_source_identity(repo: Path, package: Path, state: ValidationState) -> None:
    state.check(run_git(repo, "branch", "--show-current") == "thesis/ada-rca-assets", "export branch identity")
    state.check(run_git(repo, "rev-parse", SOURCE_COMMIT) == SOURCE_COMMIT, "frozen source commit exists")
    state.check(not any((repo / path).exists() for path in ("artifacts/baseline_eval", "docs/baseline_eval", "src/baseline_eval")), "baseline paths absent from Ada worktree")
    state.check(not any("baseline_eval" in path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file()), "baseline paths absent from package")
    provenance_path = package / "PROVENANCE.json"
    state.check(provenance_path.is_file(), "PROVENANCE.json exists")
    if provenance_path.is_file():
        provenance = json_load(provenance_path)
        state.check(provenance.get("source_ref") == "research/evidence-closure", "provenance source ref")
        state.check(provenance.get("source_commit") == SOURCE_COMMIT, "provenance source commit")
        state.check(provenance.get("scientific_decision") == "RCA_FREEZE_READY_WITH_LIMITATION", "provenance scientific decision")
        isolation = provenance.get("baseline_isolation", {})
        state.check(isolation.get("baseline_predictions_not_included") is True and isolation.get("baseline_metrics_not_computed") is True, "provenance baseline isolation")


def reconstruct_package_case_rows(package: Path) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}
    for dataset in DATASETS:
        prefix = package / "raw/source" / dataset
        inputs = {str(row["case_id"]): row for row in jsonl_load(prefix / "inputs.jsonl")}
        labels = {str(row["case_id"]): row for row in jsonl_load(prefix / "labels.jsonl")}
        assignments = {str(row["case_id"]): int(row["fold"]) for row in json_load(package / "raw/splits" / dataset / "assignments.json")}
        registry = list(json_load(prefix / "service_registry.json")["services"])
        predictions = jsonl_load(package / "raw/final_method" / dataset / "predictions.jsonl")
        if len(inputs) != EXPECTED_CASES[dataset] or len(labels) != EXPECTED_CASES[dataset] or len(predictions) != EXPECTED_CASES[dataset]:
            raise ValueError(f"{dataset}: package case count mismatch")
        if len(registry) != EXPECTED_CANDIDATES[dataset]:
            raise ValueError(f"{dataset}: package candidate count mismatch")
        if set(inputs) != set(labels) or set(inputs) != set(assignments):
            raise ValueError(f"{dataset}: package source/split IDs do not align")
        if any(list(row["candidates"]) != registry for row in inputs.values()):
            raise ValueError(f"{dataset}: package candidate registry is not fixed")
        if {str(row["case_id"]) for row in predictions} != set(inputs):
            raise ValueError(f"{dataset}: package prediction coverage mismatch")
        rows: List[Dict[str, Any]] = []
        for prediction in sorted(predictions, key=lambda row: str(row["case_id"])):
            case_id = str(prediction["case_id"])
            ranking = list(prediction["ranking"])
            candidates = list(inputs[case_id]["candidates"])
            if len(ranking) != len(candidates) or len(set(ranking)) != len(ranking) or set(ranking) != set(candidates):
                raise ValueError(f"{dataset}/{case_id}: package ranking is incomplete")
            label = labels[case_id]
            root = str(label["root_service"])
            if root not in ranking or int(prediction["fold"]) != assignments[case_id]:
                raise ValueError(f"{dataset}/{case_id}: package root/fold mismatch")
            rank = ranking.index(root) + 1
            rows.append({
                "dataset": dataset,
                "case_id": case_id,
                "fold": assignments[case_id],
                "fault_type": str(label["fault_type"]),
                "root_service": root,
                "candidate_count": len(candidates),
                "root_rank": rank,
                "AC@1": float(rank <= 1),
                "AC@2": float(rank <= 2),
                "AC@3": float(rank <= 3),
                "AC@4": float(rank <= 4),
                "AC@5": float(rank <= 5),
                "Avg@5": sum(float(rank <= k) for k in range(1, 6)) / 5.0,
                "MRR": 1.0 / float(rank),
            })
        result[dataset] = rows
    return result


def compare_case_rows(expected: Mapping[str, Sequence[Mapping[str, Any]]], actual_rows: Sequence[Mapping[str, str]], state: ValidationState) -> None:
    expected_map = {(row["dataset"], str(row["case_id"])): row for row in expected.values() for row in row}
    actual_map = {(row.get("dataset", ""), str(row.get("case_id", ""))): row for row in actual_rows}
    state.check(set(expected_map) == set(actual_map), "case-rank coverage", f"missing={sorted(set(expected_map)-set(actual_map))[:3]} unexpected={sorted(set(actual_map)-set(expected_map))[:3]}")
    for key, expected_row in expected_map.items():
        actual = actual_map.get(key)
        if actual is None:
            continue
        for field in ("fold", "fault_type", "root_service", "candidate_count", "root_rank"):
            state.check(str(actual.get(field)) == str(expected_row[field]), f"case rank field {key}/{field}")
        for metric in ("AC@1", "AC@2", "AC@3", "AC@4", "AC@5", "Avg@5", "MRR"):
            try:
                equal = exact_float_equal(parse_float(actual[metric]), float(expected_row[metric]))
            except (KeyError, ValueError):
                equal = False
            state.check(equal, f"case rank metric {key}/{metric}")


def validate_final_statistics(repo: Path, package: Path, state: ValidationState) -> Dict[str, List[Dict[str, Any]]]:
    try:
        source_rows = load_final_case_rows(repo)
        package_rows = reconstruct_package_case_rows(package)
    except Exception as exc:
        state.failures.append(f"independent case reconstruction: {exc}")
        return {}
    for dataset in DATASETS:
        state.check(len(source_rows[dataset]) == EXPECTED_CASES[dataset], f"source final case count {dataset}")
        state.check(len(package_rows[dataset]) == EXPECTED_CASES[dataset], f"package final case count {dataset}")
        state.check(source_rows[dataset] == package_rows[dataset], f"source/package reconstructed rows identical {dataset}")
    fields, rows = read_csv(package / "data/final/case_root_ranks.csv")
    state.check("root_rank" in fields and set(DATASETS).issubset({row.get("dataset") for row in rows}), "case_root_ranks schema and datasets")
    compare_case_rows(source_rows, rows, state)
    _, case_metric_rows = read_csv(package / "data/final/case_level_metrics.csv")
    state.check((package / "data/final/case_level_metrics.csv").read_bytes() == (package / "data/final/case_root_ranks.csv").read_bytes(), "case-level and case-root-rank views identical")
    state.check(len(case_metric_rows) == 180, "case-level metric row count")
    _, overall_rows = read_csv(package / "data/final/overall_metrics.csv")
    state.check(len(overall_rows) == 2, "overall metric row count")
    for row in overall_rows:
        dataset = row.get("dataset", "")
        if dataset not in DATASETS:
            state.failures.append(f"overall metric unknown dataset: {dataset}")
            continue
        reconstructed = aggregate(source_rows[dataset])
        for metric in ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR"):
            try:
                value = parse_float(row[metric])
                state.check(exact_float_equal(value, reconstructed[metric]), f"overall reconstruction {dataset}/{metric}")
                state.check(exact_float_equal(value, EXPECTED_FINAL[dataset][metric]), f"overall frozen value {dataset}/{metric}")
            except (KeyError, ValueError):
                state.failures.append(f"overall metric missing or invalid: {dataset}/{metric}")
        state.check(row.get("reconstruction_status") == "MATCHES_FROZEN_CANONICAL_WITHIN_1E-12", f"overall reconstruction status {dataset}")
    _, fault_rows = read_csv(package / "data/final/fault_level_metrics.csv")
    state.check(len(fault_rows) == 12, "fault-level row count")
    for dataset in DATASETS:
        ds_rows = [row for row in fault_rows if row.get("dataset") == dataset]
        state.check(len(ds_rows) == 6, f"fault-level six fault types {dataset}")
        state.check(all(row.get("n_cases") == "15" for row in ds_rows), f"fault-level 15 cases per fault {dataset}")
        state.check({row.get("fault_type", "").lower() for row in ds_rows} == set(FAULT_ORDER), f"fault-level taxonomy {dataset}")
    _, root_rows = read_csv(package / "data/final/root_level_metrics.csv")
    _, fold_rows = read_csv(package / "data/final/fold_level_metrics.csv")
    state.check(sum(int(row["n_cases"]) for row in root_rows) == 180, "root-level case total")
    state.check(len(fold_rows) == 6 and all(row.get("n_cases") == "30" for row in fold_rows), "fold-level 30 cases per fold")
    _, distribution_rows = read_csv(package / "data/final/root_rank_distribution.csv")
    for dataset in DATASETS:
        state.check(sum(int(row["count"]) for row in distribution_rows if row.get("dataset") == dataset) == 90, f"rank distribution case total {dataset}")
    _, candidate_rows = read_csv(package / "data/final/candidate_universe_summary.csv")
    state.check({(row.get("dataset"), int(row.get("candidate_count", "-1"))) for row in candidate_rows} == {("re2ob", 11), ("re2tt", 68)}, "candidate universe summary")
    return source_rows


def validate_schema_and_fit(repo: Path, package: Path, state: ValidationState) -> None:
    try:
        schema_rows, digest, meta = feature_schema(repo)
        fields, package_schema = read_csv(package / "data/reproducibility/feature_schema_68d.csv")
        state.check(len(package_schema) == 68, "68D schema row count")
        state.check([(int(row["feature_index"]), row["channel"], row["family"], row["field"]) for row in package_schema] == [(int(row["feature_index"]), row["channel"], row["family"], row["field"]) for row in schema_rows], "code-derived feature schema")
        config = json_load(package / "data/reproducibility/frozen_configuration.json")
        state.check(config.get("feature_order_sha256") == digest and config.get("dimension") == 68, "frozen feature-order digest")
        state.check(config.get("channels") == meta["channels"] and config.get("ranker") == "event-level Conditional Logit", "frozen configuration semantics")
    except Exception as exc:
        state.failures.append(f"feature schema/configuration validation: {exc}")
    fit_rows = read_csv(package / "data/reproducibility/model_fit_diagnostics.csv")[1]
    state.check(len(fit_rows) == 6, "six persisted fit diagnostics")
    for row in fit_rows:
        state.check(parse_bool(row.get("converged")), f"fit converged {row.get('dataset')}/{row.get('fold')}")
        state.check(row.get("float_dtype") == "float64", f"fit dtype {row.get('dataset')}/{row.get('fold')}")
        state.check(int(row.get("feature_dimension", "-1")) == 68, f"fit dimension {row.get('dataset')}/{row.get('fold')}")
        state.check(parse_float(row.get("gradient_norm", "nan")) <= parse_float(row.get("gradient_tolerance", "1e-8")) if row.get("gradient_tolerance") else parse_float(row.get("gradient_norm", "nan")) <= 1e-8, f"fit gradient tolerance {row.get('dataset')}/{row.get('fold')}")
    replay_rows = read_csv(package / "data/reproducibility/replay_integrity.csv")[1]
    state.check(len(replay_rows) == 2, "two replay integrity rows")
    for row in replay_rows:
        state.check(parse_bool(row.get("ranking_identical")), f"replay rankings identical {row.get('dataset')}")
        state.check(parse_float(row.get("max_abs_score_difference", "nan")) <= TOLERANCE, f"replay score difference {row.get('dataset')}")
        state.check(row.get("checksum_status") == "PASS" and row.get("integrity_status") == "INTEGRITY_VALID", f"replay checksum/integrity {row.get('dataset')}")
        state.check(parse_bool(row.get("all_folds_converged")) and parse_bool(row.get("metrics_exact")), f"replay fold/metric status {row.get('dataset')}")


def validate_evidence_boundaries(repo: Path, package: Path, rows: Sequence[Mapping[str, str]], state: ValidationState) -> None:
    _, documents = read_csv(package / "refs/document_index.csv")
    source_docs = {path.name for path in (repo / "docs").glob("*.md")}
    state.check({row.get("path", "").split("/", 1)[-1] for row in documents} == source_docs, "complete document index")
    state.check({row.get("path", "").split("/", 1)[-1]: row.get("evidence_class") for row in documents} == DOCUMENT_CLASSES, "document classifications complete")
    state.check(all(row.get("copied") == "false" for row in documents if row.get("evidence_class") == "OUT_OF_SCOPE"), "out-of-scope documents not copied")
    state.check(not any(row.get("evidence_class") == "HISTORICAL_SUPERSEDED" and row.get("asset_path", "") for row in documents), "historical documents are routed outside active docs")
    _, superseded = read_csv(package / "refs/superseded_artifacts.csv")
    state.check(any(row.get("path") == "artifacts/opt/final/bootstrap.json" for row in superseded), "legacy bootstrap explicitly superseded")
    state.check(all(row.get("evidence_class") == "HISTORICAL_SUPERSEDED" for row in superseded), "superseded artifact class")
    forbidden_text = []
    for root_name in ("data", "tables", "refs"):
        for path in (package / root_name).rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                lowered = text.lower()
                if "artifacts/opt/final/bootstrap.json" in lowered or "legacy bootstrap.json" in lowered:
                    forbidden_text.append(path.as_posix())
                if "not_auditable" in lowered and ("pass" in lowered or "fail" in lowered):
                    # The package must not collapse NOT_AUDITABLE into a binary
                    # pass/fail result in the same exported table view.
                    forbidden_text.append(f"binary audit collapse: {path.as_posix()}")
    state.check(not forbidden_text, "superseded/binary-audit exclusion", "; ".join(forbidden_text[:5]))
    state.check(not (package / "data/final/discrepancy_report.json").exists(), "no discrepancy report in valid package")
    anchor_fields, anchor_rows = read_csv(package / "data/diagnostics/anchor_feasibility_summary.csv")
    status_rows = {(row.get("scope"), row.get("statistic")): row.get("value") for row in anchor_rows}
    state.check(status_rows.get(("overall", "status")) == "ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE", "anchor limitation status")
    state.check(status_rows.get(("overall", "performance_computed")) in {"false", "False"}, "anchor performance not computed")
    source_artifact_fields, source_artifacts = read_csv(package / "refs/source_artifact_index.csv")
    expected_source_artifacts = {path.relative_to(repo).as_posix() for path in (repo / "artifacts").rglob("*") if path.is_file()}
    state.check({row.get("path") for row in source_artifacts} == expected_source_artifacts, "complete source artifact index")
    state.check(all("baseline_eval" not in row.get("path", "") for row in source_artifacts), "source artifact index baseline exclusion")
    code_fields, code_rows = read_csv(package / "refs/source_code_index.csv")
    expected_code = {path.relative_to(repo).as_posix() for root in (repo / "src/rca", repo / "scripts") for path in root.glob("*.py")}
    state.check({row.get("path") for row in code_rows} == expected_code, "complete source code index")
    for row in code_rows:
        relative = row.get("path", "")
        try:
            state.check(row.get("git_blob_sha") == git_blob(repo, SOURCE_COMMIT, relative), f"source code Git blob {relative}")
            state.check(row.get("sha256") == sha256_file(repo / relative), f"source code file hash {relative}")
        except Exception as exc:
            state.failures.append(f"source code provenance {relative}: {exc}")
    state.check(not any("artifacts/baseline_eval" in str(row) or "docs/baseline_eval" in str(row) or "src/baseline_eval" in str(row) for row in rows), "manifest baseline source exclusion")


def validate_raw_copy(repo: Path, package: Path, state: ValidationState) -> None:
    # Every copied source artifact listed by the exporter must remain
    # byte-identical to the frozen source commit.  This catches accidental
    # edits to labels, predictions, folds, or canonical machine-readable JSON.
    _, source_artifacts = read_csv(package / "refs/source_artifact_index.csv")
    for row in source_artifacts:
        if row.get("copied") != "true":
            continue
        relative = row["path"]
        candidates = [manifest for manifest in read_csv(package / "MANIFEST.csv")[1] if manifest.get("source_path") == relative]
        state.check(bool(candidates), f"copied source has manifest row {relative}")
        if not candidates:
            continue
        try:
            state.check(row.get("git_blob_sha") == git_blob(repo, SOURCE_COMMIT, relative), f"copied source frozen blob {relative}")
        except Exception as exc:
            state.failures.append(f"copied source blob {relative}: {exc}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=SCRIPT_DIR.parents[3])
    parser.add_argument("--json", action="store_true", help="emit machine-readable validation output")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    package = repo / PACKAGE_REL
    state = ValidationState()
    try:
        validate_source_identity(repo, package, state)
        manifest_rows = validate_manifest(repo, package, state)
        validate_final_statistics(repo, package, state)
        validate_schema_and_fit(repo, package, state)
        validate_evidence_boundaries(repo, package, manifest_rows, state)
        validate_raw_copy(repo, package, state)
    except Exception as exc:  # fail closed while preserving a useful report
        state.failures.append(f"validator exception: {type(exc).__name__}: {exc}")
    status = "THESIS_ASSET_PACKAGE_READY_WITH_LIMITATION" if not state.failures else "THESIS_ASSET_PACKAGE_INVALID"
    report = {"status": status, "package": str(package), "source_commit": SOURCE_COMMIT, "checks_passed": len(state.checks), "failure_count": len(state.failures), "failures": state.failures}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if not state.failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
