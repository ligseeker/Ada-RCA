#!/usr/bin/env python3
"""Export the frozen Ada-RCA V1 evidence into a thesis-facing asset package.

The exporter is deliberately read-only with respect to the frozen repository
evidence.  It copies selected small artifacts byte-for-byte and derives only
statistics, indexes, and tables from committed evidence.  It never imports a
model runner, fits a model, accesses the network, or executes an optimization.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


SOURCE_COMMIT = "9342e06db91945be2e44703437229ba45b18bda8"
SOURCE_REF = "research/evidence-closure"
V1_REFERENCE_COMMIT = "bed295326e567395e725caa82840a534dcc0b1de"
OPTIMIZATION_COMMIT = "53c9face2c96761c9114edb558eb6d8666a38dc6"
EVIDENCE_DECISION_COMMIT = "5957b465fac7351a6c55ab799a058ef66a60f9bc"
PACKAGE_REL = Path("thesis_assets/ada_rca_v1")
METRICS = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")
CASE_METRICS = ("AC@1", "AC@2", "AC@3", "AC@4", "AC@5", "Avg@5", "MRR")
FAULT_ORDER = ("cpu", "mem", "disk", "socket", "delay", "loss")
FAULT_DISPLAY = {fault: fault.upper() for fault in FAULT_ORDER}
DATASETS = ("re2ob", "re2tt")
EXPECTED_CASES = {"re2ob": 90, "re2tt": 90}
EXPECTED_CANDIDATES = {"re2ob": 11, "re2tt": 68}
EXPECTED_FINAL = {
    "re2ob": {
        "AC@1": 0.8777777777777778,
        "AC@3": 0.9888888888888889,
        "AC@5": 0.9888888888888889,
        "Avg@5": 0.9622222222222222,
        "MRR": 0.9314814814814816,
    },
    "re2tt": {
        "AC@1": 0.7111111111111111,
        "AC@3": 0.8666666666666667,
        "AC@5": 0.9333333333333333,
        "Avg@5": 0.851111111111111,
        "MRR": 0.8034718881941106,
    },
}
TOLERANCE = 1e-12


# Classification is explicit and reviewable.  The active evidence index and
# semantic correction, rather than a filename heuristic, determine the class.
DOCUMENT_CLASSES: Dict[str, str] = {}
for _name in (
    "RCA_EVIDENCE_INDEX.md",
    "RCA_FINAL_SCIENTIFIC_FREEZE_V1.md",
    "RCA_THESIS_RESULTS_PACKAGE.md",
    "RCA_THESIS_CLAIM_MATRIX.md",
    "BOOTSTRAP_FORENSIC_AUDIT.md",
    "TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md",
    "TRACE_ERROR_REPRESENTATION_INVARIANT.md",
    "EVIDENCE_ERRATA.md",
    "EVIDENCE_LEVEL_SEMANTIC_CORRECTION.md",
    "RCA_EVIDENCE_CLOSURE_PROTOCOL.md",
    "RCA_EVIDENCE_CLOSURE_PROTOCOL_AMENDMENT_V1_1.md",
    "INDEPENDENT_METRIC_RECONSTRUCTION_V1_1.md",
    "FINAL_METHOD_REPLAY_AUDIT.md",
):
    DOCUMENT_CLASSES[_name] = "CANONICAL"
for _name in (
    "DATASET_AUDIT_RE2.md",
    "EVALUATION_PROTOCOL.md",
    "FINAL_AUDIT_PROTOCOL_DEVIATIONS.md",
    "FINAL_EVIDENCE_SUMMARY.md",
    "FINAL_METHOD_DECISION.md",
    "FINAL_RCA_CONTROL_AUDIT.md",
    "LEAKAGE_AUDIT.md",
    "OPT_O0_BASELINE_INTEGRITY.md",
    "OPT_RESEARCH_PROTOCOL_V2.md",
    "OPT_SEARCH_SPACE_FREEZE_V1.md",
    "RCA_FINAL_METHOD_FREEZE_V1.0.md",
    "README.md",
    "REPRESENTATION_FREEZE.md",
    "RESEARCH_STATUS.md",
    "SPLIT_PROTOCOL.md",
):
    DOCUMENT_CLASSES[_name] = "SUPPORTING"
for _name in (
    "P3_G1_DECISION.md",
    "RCA_P3_Research_Execution_Protocol_V0.6_min.md",
    "P4_G0_DECISION.md",
    "P4_G0_FAILURE_ANALYSIS.md",
    "P4_G0_IMPLEMENTATION_AUDIT.md",
    "P4_G0_RESULTS.md",
    "P4_PROTOCOL_DEVIATIONS.md",
    "RCA_P4_G0_MINIMAL_COMPARATIVE_PROTOCOL_V0.7.md",
    "OPT_DATASET_SPECIFIC_RESULTS.md",
    "OPT_FINAL_DECISION.md",
    "OPT_GLOBAL_CONFIGURATION_RESULTS.md",
    "OPT_NESTED_SELECTION_RESULTS.md",
    "OPT_RESEARCH_PROTOCOL_V2.md",
    "OPT_SEARCH_SPACE_FREEZE_V1.md",
    "ZERO_MODEL_AUDIT.md",
):
    # Frozen search/protocol documents above remain supporting when they are
    # already assigned; the results themselves are development evidence.
    if _name not in DOCUMENT_CLASSES:
        DOCUMENT_CLASSES[_name] = "DEVELOPMENT"
for _name in (
    "ANCHOR_FEASIBILITY_AUDIT.md",
    "MAGNITUDE_INVERSION_AUDIT.md",
    "P3_POSTMORTEM.md",
    "P4_CONTEXT_DIAGNOSTIC_LIMITATION.md",
    "S3_SERVICE_IDENTITY_PROBE.md",
):
    DOCUMENT_CLASSES[_name] = "DIAGNOSTIC"
for _name in (
    "LEGACY_ASSET_MAP.md",
    "OPT_FINAL_EVIDENCE_SUMMARY.md",
    "OPT_HISTORICAL_COMPATIBILITY_AUDIT.md",
    "OPT_HISTORICAL_MODEL_INVENTORY.md",
    "OPT_HISTORICAL_REPLAY_RESULTS.md",
    "OPT_TELEMETRY_INFORMATION_LOSS_AUDIT.md",
    "RCA_EVIDENCE_CLOSURE_FAILURE.md",
):
    DOCUMENT_CLASSES[_name] = "HISTORICAL_SUPERSEDED"
for _name in (
    "BASELINE_COMPATIBILITY_MATRIX.md",
    "BENCHMARK_COMPATIBILITY.md",
    "P6_G0_BASELINE_MATRIX_DECISION.md",
    "RCAEVAL_RE2_TT_PUBLISHED_CONTEXT_AUDIT.md",
    "RCAEVAL_RE2_TT_TABLE6_PUBLISHED_REFERENCE.md",
    "RCA_FINAL_EVALUATION_PROTOCOL_V1.0.md",
):
    DOCUMENT_CLASSES[_name] = "OUT_OF_SCOPE"

DOCUMENT_USES = {
    "CANONICAL": "direct thesis evidence or authoritative interpretation",
    "SUPPORTING": "method, protocol, audit, or provenance context",
    "DEVELOPMENT": "internal P3/P4/optimization evidence; bounded use only",
    "DIAGNOSTIC": "limitation or post-hoc diagnostic; not confirmatory",
    "HISTORICAL_SUPERSEDED": "historical context only; not canonical metrics",
    "OUT_OF_SCOPE": "excluded from this Ada-RCA-only asset package",
}
DOCUMENT_SUPERSEDERS = {
    "OPT_FINAL_EVIDENCE_SUMMARY.md": "BOOTSTRAP_FORENSIC_AUDIT.md; artifacts/evidence_closure/bootstrap_corrected_v1_1.json",
    "OPT_TELEMETRY_INFORMATION_LOSS_AUDIT.md": "TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md; artifacts/evidence_closure/telemetry_information_loss_v1_1.json",
    "RCA_EVIDENCE_CLOSURE_FAILURE.md": "EVIDENCE_LEVEL_SEMANTIC_CORRECTION.md; final_decision_v1_1.json",
    "OPT_HISTORICAL_COMPATIBILITY_AUDIT.md": "RCA_FINAL_SCIENTIFIC_FREEZE_V1.md; RCA_THESIS_CLAIM_MATRIX.md",
    "OPT_HISTORICAL_MODEL_INVENTORY.md": "RCA_FINAL_SCIENTIFIC_FREEZE_V1.md; RCA_THESIS_CLAIM_MATRIX.md",
    "OPT_HISTORICAL_REPLAY_RESULTS.md": "RCA_FINAL_SCIENTIFIC_FREEZE_V1.md; RCA_THESIS_CLAIM_MATRIX.md",
    "LEGACY_ASSET_MAP.md": "RCA_EVIDENCE_INDEX.md; RCA_THESIS_CLAIM_MATRIX.md",
}


class ExportError(RuntimeError):
    """A fail-closed export error with machine-readable details."""

    def __init__(self, message: str, report: Optional[Mapping[str, Any]] = None):
        super().__init__(message)
        self.report = dict(report or {"error": message})


def repo_from_script() -> Path:
    # repo/thesis_assets/ada_rca_v1/scripts/export_thesis_assets.py
    return Path(__file__).resolve().parents[3]


def run_git(repo: Path, *args: str, check: bool = True, text: bool = True) -> str:
    result = subprocess.run(
        ("git", *args),
        cwd=str(repo),
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    if text:
        return result.stdout.strip()
    return result.stdout


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl_load(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ExportError(f"{path}:{line_number}: JSONL row is not an object")
            rows.append(value)
    return rows


def json_inline(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json_inline(value)
    return value


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def git_blob(repo: Path, commit: str, relative_path: str) -> str:
    try:
        return run_git(repo, "rev-parse", f"{commit}:{relative_path}")
    except subprocess.CalledProcessError as exc:
        raise ExportError(
            f"source path is not present at {commit}: {relative_path}",
            {"source_path": relative_path, "source_commit": commit},
        ) from exc


def source_sha_values(repo: Path, commit: str, source_paths: Sequence[str]) -> Tuple[str, str]:
    blobs: List[str] = []
    files: List[str] = []
    for relative in sorted(dict.fromkeys(source_paths)):
        path = repo / relative
        if not path.is_file():
            raise ExportError(f"source file is missing: {relative}", {"source_path": relative})
        blobs.append(git_blob(repo, commit, relative))
        files.append(sha256_file(path))
    return ";".join(blobs), ";".join(files)


def require_source_boundary(repo: Path) -> str:
    actual = run_git(repo, "rev-parse", SOURCE_REF)
    if actual != SOURCE_COMMIT:
        raise ExportError(
            f"{SOURCE_REF} changed: expected {SOURCE_COMMIT}, found {actual}",
            {"expected": SOURCE_COMMIT, "actual": actual, "source_ref": SOURCE_REF},
        )
    branch = run_git(repo, "branch", "--show-current")
    if branch != "thesis/ada-rca-assets":
        raise ExportError(
            f"wrong export branch: expected thesis/ada-rca-assets, found {branch!r}",
            {"expected_branch": "thesis/ada-rca-assets", "actual_branch": branch},
        )
    for forbidden in ("artifacts/baseline_eval", "docs/baseline_eval", "src/baseline_eval"):
        # Metadata-only existence checks protect the isolated Ada worktree;
        # no contents of these paths are read.
        if (repo / forbidden).exists():
            raise ExportError(
                f"forbidden baseline path exists in Ada-RCA worktree: {forbidden}",
                {"forbidden_path": forbidden},
            )
    exporter = repo / PACKAGE_REL / "scripts" / "export_thesis_assets.py"
    if exporter.is_file():
        exporter_rel = str(exporter.relative_to(repo))
        # `git diff --quiet` communicates dirtiness through its return code,
        # not stdout.  Keep this check explicit so a source edit cannot be
        # silently incorporated into a provenance record.
        result_dirty = subprocess.run(("git", "diff", "--quiet", "--", exporter_rel), cwd=repo)
        result_staged = subprocess.run(("git", "diff", "--cached", "--quiet", "--", exporter_rel), cwd=repo)
        if result_dirty.returncode != 0 or result_staged.returncode != 0:
            raise ExportError("exporter source is modified; commit it before exporting", {"path": str(exporter)})
    return branch


def exporter_commit(repo: Path) -> str:
    relative = str((PACKAGE_REL / "scripts" / "export_thesis_assets.py").as_posix())
    try:
        return run_git(repo, "log", "-1", "--format=%H", "--", relative)
    except subprocess.CalledProcessError:
        return run_git(repo, "rev-parse", "HEAD")


def ensure_output_dirs(package: Path) -> None:
    # These are generated package subtrees.  The exporter script and tests live
    # under scripts/tests and are deliberately preserved.
    for name in ("docs", "raw", "data", "tables", "refs"):
        path = package / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def parse_json_constant(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except ValueError as exc:
                        raise ExportError(f"constant {name} is not literal in {path}") from exc
    raise ExportError(f"constant {name} not found in {path}")


def feature_schema(repo: Path) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    features_path = repo / "src/rca/features.py"
    final_path = repo / "src/rca/final_method.py"
    channels = tuple(parse_json_constant(features_path, "CHANNELS"))
    base_fields = tuple(parse_json_constant(final_path, "BASE_FIELDS"))
    morphology_fields = tuple(parse_json_constant(final_path, "MORPHOLOGY_FIELDS"))
    dimension = int(parse_json_constant(final_path, "FINAL_Z2_DIMENSION"))
    names = tuple(f"{channel}.{field}" for channel in channels for field in base_fields + morphology_fields)
    digest = sha256_bytes("\n".join(names).encode("utf-8"))
    if len(names) != dimension or dimension != 68 or len(channels) != 4 or len(base_fields) != 8 or len(morphology_fields) != 9:
        raise ExportError(
            "frozen feature schema is not 4 x 17 x 68",
            {"dimension": len(names), "channels": len(channels), "base": len(base_fields), "morphology": len(morphology_fields)},
        )
    rows: List[Dict[str, Any]] = []
    index = 0
    for channel in channels:
        for field in base_fields:
            rows.append({"feature_index": index, "channel": channel, "family": "BASE", "field": field})
            index += 1
        for field in morphology_fields:
            rows.append({"feature_index": index, "channel": channel, "family": "MORPHOLOGY", "field": field})
            index += 1
    return rows, digest, {
        "channels": list(channels),
        "base_fields": list(base_fields),
        "morphology_fields": list(morphology_fields),
        "names": list(names),
        "dimension": dimension,
    }


def load_final_case_rows(repo: Path) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}
    for dataset in DATASETS:
        source_prefix = repo / "artifacts/source" / dataset
        input_rows = jsonl_load(source_prefix / "inputs.jsonl")
        label_rows = jsonl_load(source_prefix / "labels.jsonl")
        inputs = {str(row["case_id"]): row for row in input_rows}
        labels = {str(row["case_id"]): row for row in label_rows}
        assignment_rows = json_load(repo / "artifacts/splits" / dataset / "assignments.json")
        assignments = {str(row["case_id"]): int(row["fold"]) for row in assignment_rows}
        registry = list(json_load(source_prefix / "service_registry.json")["services"])
        prediction_rows = jsonl_load(repo / "artifacts/final_method" / dataset / "predictions.jsonl")
        if len(input_rows) != EXPECTED_CASES[dataset] or len(label_rows) != EXPECTED_CASES[dataset] or len(prediction_rows) != EXPECTED_CASES[dataset]:
            raise ExportError(
                f"{dataset}: final case count mismatch",
                {"dataset": dataset, "inputs": len(input_rows), "labels": len(label_rows), "predictions": len(prediction_rows)},
            )
        if len(inputs) != len(input_rows) or len(labels) != len(label_rows) or len(assignments) != len(assignment_rows):
            raise ExportError(f"{dataset}: duplicate case IDs in source or split evidence")
        if set(inputs) != set(labels) or set(inputs) != set(assignments):
            raise ExportError(f"{dataset}: labels, inputs, and split assignments do not align")
        if any(list(row["candidates"]) != registry for row in input_rows):
            raise ExportError(f"{dataset}: candidate registry is not fixed across cases")
        if len(registry) != EXPECTED_CANDIDATES[dataset]:
            raise ExportError(f"{dataset}: candidate count differs from frozen expectation", {"actual": len(registry), "expected": EXPECTED_CANDIDATES[dataset]})
        observed_ids = [str(row.get("case_id")) for row in prediction_rows]
        if len(set(observed_ids)) != len(observed_ids) or set(observed_ids) != set(inputs):
            raise ExportError(f"{dataset}: final prediction coverage is incomplete or duplicated", {"missing": sorted(set(inputs) - set(observed_ids)), "unexpected": sorted(set(observed_ids) - set(inputs))})
        rows: List[Dict[str, Any]] = []
        for prediction in sorted(prediction_rows, key=lambda row: str(row["case_id"])):
            case_id = str(prediction["case_id"])
            expected_candidates = list(inputs[case_id]["candidates"])
            ranking = list(prediction.get("ranking", []))
            scores = dict(prediction.get("candidate_scores", {}))
            if len(ranking) != len(expected_candidates) or len(set(ranking)) != len(ranking) or set(ranking) != set(expected_candidates) or set(scores) != set(expected_candidates):
                raise ExportError(f"{dataset}/{case_id}: final ranking is not complete and legal")
            label = labels[case_id]
            root = str(label["root_service"])
            if root not in expected_candidates or root not in ranking:
                raise ExportError(f"{dataset}/{case_id}: labelled root is not in candidate ranking")
            fold = assignments[case_id]
            if int(prediction.get("fold")) != fold:
                raise ExportError(f"{dataset}/{case_id}: prediction fold disagrees with frozen split")
            if prediction.get("root_service") not in (None, root) or prediction.get("fault_type") not in (None, label["fault_type"]):
                raise ExportError(f"{dataset}/{case_id}: prediction label fields disagree with label sidecar")
            root_rank = ranking.index(root) + 1
            case = {
                "dataset": dataset,
                "case_id": case_id,
                "fold": fold,
                "fault_type": str(label["fault_type"]),
                "root_service": root,
                "candidate_count": len(expected_candidates),
                "root_rank": root_rank,
                "AC@1": float(root_rank <= 1),
                "AC@2": float(root_rank <= 2),
                "AC@3": float(root_rank <= 3),
                "AC@4": float(root_rank <= 4),
                "AC@5": float(root_rank <= 5),
                "Avg@5": sum(float(root_rank <= k) for k in range(1, 6)) / 5.0,
                "MRR": 1.0 / float(root_rank),
            }
            rows.append(case)
        result[dataset] = rows
    return result


def aggregate(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    if not rows:
        raise ExportError("cannot aggregate an empty subgroup")
    return {metric: float(mean(float(row[metric]) for row in rows)) for metric in METRICS}


def grouped_metric_rows(case_rows: Mapping[str, Sequence[Mapping[str, Any]]], dimension: str) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for dataset in DATASETS:
        rows = list(case_rows[dataset])
        if dimension == "overall":
            groups = [("overall", rows)]
        elif dimension == "fault_type":
            groups = [(fault, [row for row in rows if row["fault_type"] == fault]) for fault in FAULT_ORDER]
        elif dimension == "root_service":
            groups = [(root, [row for row in rows if row["root_service"] == root]) for root in sorted({str(row["root_service"]) for row in rows})]
        elif dimension == "fold":
            groups = [(fold, [row for row in rows if int(row["fold"]) == fold]) for fold in (0, 1, 2)]
        else:
            raise ExportError(f"unknown grouping dimension: {dimension}")
        for group, subset in groups:
            metrics = aggregate(subset)
            row: Dict[str, Any] = {"dataset": dataset, dimension: group, "n_cases": len(subset), **metrics}
            output.append(row)
    return output


def exact_float_equal(left: float, right: float) -> bool:
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= TOLERANCE


def verify_reconstruction(repo: Path, case_rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    closure = json_load(repo / "artifacts/evidence_closure/metric_reconstruction_v1_1.json")
    for dataset in DATASETS:
        reconstructed = aggregate(case_rows[dataset])
        final_metrics = json_load(repo / "artifacts/final_method" / dataset / "metrics.json")["overall_cases"]
        canonical = closure["tracks"]["V1-SCIENTIFIC"]["datasets"][dataset]["metric_comparison"]
        discrepancies = {}
        for metric in METRICS:
            values = {
                "reconstructed": reconstructed[metric],
                "expected": EXPECTED_FINAL[dataset][metric],
                "final_method": float(final_metrics[metric]),
                "evidence_closure": float(canonical[metric]["independent_metric"]),
            }
            if not all(exact_float_equal(values["reconstructed"], values[key]) for key in ("expected", "final_method", "evidence_closure")):
                discrepancies[metric] = values
        if discrepancies:
            raise ExportError(
                f"{dataset}: independent metric reconstruction mismatch; table generation stopped",
                {"dataset": dataset, "tolerance": TOLERANCE, "metrics": discrepancies},
            )


def make_manifest_record(
    repo: Path,
    package: Path,
    assets: MutableMapping[str, Dict[str, Any]],
    asset_rel: str,
    source_paths: Sequence[str],
    source_commit: str,
    evidence_class: str,
    thesis_use: str,
    citation_allowed: bool,
    derived_or_copied: str,
    derivation: str,
    caveat: str,
) -> None:
    asset_path = package / asset_rel
    if not asset_path.is_file():
        raise ExportError(f"cannot register missing asset: {asset_rel}")
    if asset_rel in assets:
        raise ExportError(f"duplicate asset registration: {asset_rel}")
    source_paths = sorted(dict.fromkeys(str(path) for path in source_paths))
    blob_sha, source_file_sha = source_sha_values(repo, source_commit, source_paths)
    assets[asset_rel] = {
        "asset_path": asset_rel,
        "source_path": ";".join(source_paths),
        "source_commit": source_commit,
        "source_blob_sha": blob_sha,
        "source_file_sha256": source_file_sha,
        "asset_sha256": sha256_file(asset_path),
        "evidence_class": evidence_class,
        "thesis_use": thesis_use,
        "citation_allowed": citation_allowed,
        "derived_or_copied": derived_or_copied,
        "derivation": derivation,
        "caveat": caveat,
    }


def copy_registered(
    repo: Path,
    package: Path,
    assets: MutableMapping[str, Dict[str, Any]],
    copied_sources: MutableMapping[str, bool],
    source_rel: str,
    asset_rel: str,
    evidence_class: str,
    thesis_use: str,
    citation_allowed: bool = True,
    caveat: str = "",
) -> None:
    source = repo / source_rel
    if not source.is_file():
        raise ExportError(f"required source artifact is missing: {source_rel}")
    destination = package / asset_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if destination.read_bytes() != source.read_bytes():
        raise ExportError(f"byte-copy failed: {source_rel}")
    make_manifest_record(
        repo,
        package,
        assets,
        asset_rel,
        [source_rel],
        SOURCE_COMMIT,
        evidence_class,
        thesis_use,
        citation_allowed,
        "COPIED",
        "byte-identical copy of committed frozen evidence",
        caveat,
    )
    copied_sources[source_rel] = True


def generated_text(
    repo: Path,
    package: Path,
    assets: MutableMapping[str, Dict[str, Any]],
    asset_rel: str,
    text: str,
    source_paths: Sequence[str],
    evidence_class: str,
    thesis_use: str,
    citation_allowed: bool,
    derivation: str,
    caveat: str = "",
) -> None:
    write_text(package / asset_rel, text)
    make_manifest_record(
        repo,
        package,
        assets,
        asset_rel,
        source_paths,
        SOURCE_COMMIT,
        evidence_class,
        thesis_use,
        citation_allowed,
        "DERIVED",
        derivation,
        caveat,
    )


def generated_json(
    repo: Path,
    package: Path,
    assets: MutableMapping[str, Dict[str, Any]],
    asset_rel: str,
    value: Any,
    source_paths: Sequence[str],
    evidence_class: str,
    thesis_use: str,
    citation_allowed: bool,
    derivation: str,
    caveat: str = "",
) -> None:
    write_json(package / asset_rel, value)
    make_manifest_record(repo, package, assets, asset_rel, source_paths, SOURCE_COMMIT, evidence_class, thesis_use, citation_allowed, "DERIVED", derivation, caveat)


def generated_csv(
    repo: Path,
    package: Path,
    assets: MutableMapping[str, Dict[str, Any]],
    asset_rel: str,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    source_paths: Sequence[str],
    evidence_class: str,
    thesis_use: str,
    citation_allowed: bool,
    derivation: str,
    caveat: str = "",
) -> None:
    write_csv(package / asset_rel, fieldnames, rows)
    make_manifest_record(repo, package, assets, asset_rel, source_paths, SOURCE_COMMIT, evidence_class, thesis_use, citation_allowed, "DERIVED", derivation, caveat)


def copy_document_set(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], copied_sources: MutableMapping[str, bool]) -> List[Dict[str, Any]]:
    document_paths = sorted(path.relative_to(repo / "docs").as_posix() for path in (repo / "docs").glob("*.md"))
    if set(document_paths) != set(DOCUMENT_CLASSES):
        missing = sorted(set(document_paths) - set(DOCUMENT_CLASSES))
        extra = sorted(set(DOCUMENT_CLASSES) - set(document_paths))
        raise ExportError("document classification is incomplete", {"missing_classification": missing, "unknown_classification": extra})
    index_rows: List[Dict[str, Any]] = []
    for name in document_paths:
        evidence_class = DOCUMENT_CLASSES[name]
        if evidence_class == "OUT_OF_SCOPE":
            copied = False
            asset_path = ""
        else:
            bucket = "canonical" if evidence_class == "CANONICAL" else "historical_superseded" if evidence_class == "HISTORICAL_SUPERSEDED" else "supporting"
            asset_path = f"docs/{bucket}/{name}"
            copy_registered(repo, package, assets, copied_sources, f"docs/{name}", asset_path, evidence_class, DOCUMENT_USES[evidence_class], evidence_class != "OUT_OF_SCOPE", "Historical or development documents are retained with their class and use boundary." if evidence_class in ("HISTORICAL_SUPERSEDED", "DEVELOPMENT", "DIAGNOSTIC") else "")
            copied = True
        title = ""
        for line in (repo / "docs" / name).read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        if not title:
            title = name
        index_rows.append({
            "path": f"docs/{name}",
            "source_commit": SOURCE_COMMIT,
            "git_blob_sha": git_blob(repo, SOURCE_COMMIT, f"docs/{name}"),
            "title": title,
            "evidence_class": evidence_class,
            "thesis_use": DOCUMENT_USES[evidence_class],
            "citation_allowed": evidence_class != "OUT_OF_SCOPE",
            "superseded_by": DOCUMENT_SUPERSEDERS.get(name, ""),
            "copied": copied,
            "asset_path": asset_path,
            "notes": "Baseline/external-comparison context is deliberately outside this Ada-RCA-only package." if evidence_class == "OUT_OF_SCOPE" else "",
        })
    return index_rows


def copy_required_raw(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], copied_sources: MutableMapping[str, bool]) -> None:
    final_files = ("metrics.json", "predictions.jsonl", "config.json", "environment.json", "provenance.json", "checksums.json", "replay_audit.json", "runtime.json", "model_state_manifest.json")
    for dataset in DATASETS:
        for filename in final_files:
            copy_registered(repo, package, assets, copied_sources, f"artifacts/final_method/{dataset}/{filename}", f"raw/final_method/{dataset}/{filename}", "CANONICAL", "frozen final-method raw evidence", True, "Final persisted state manifests are copied; large model arrays are indexed only.")
        for filename in ("inputs.jsonl", "labels.jsonl", "service_registry.json", "manifest.json"):
            copy_registered(repo, package, assets, copied_sources, f"artifacts/source/{dataset}/{filename}", f"raw/source/{dataset}/{filename}", "CANONICAL", "self-contained case, label, and candidate semantics", True, "sources.jsonl and raw telemetry are indexed, not copied.")
        for filename in ("assignments.json", "folds.json", "split_manifest.json"):
            copy_registered(repo, package, assets, copied_sources, f"artifacts/splits/{dataset}/{filename}", f"raw/splits/{dataset}/{filename}", "CANONICAL", "frozen fold reconstruction evidence")
    copy_registered(repo, package, assets, copied_sources, "artifacts/splits/split_summary.json", "raw/splits/split_summary.json", "CANONICAL", "frozen fold reconstruction evidence")
    for dataset in DATASETS:
        copy_registered(repo, package, assets, copied_sources, f"artifacts/splits/{dataset}_3fold.json", f"raw/splits/{dataset}_3fold.json", "CANONICAL", "frozen fold reconstruction evidence")
    for filename in (
        "evidence_semantic_correction_v1_1.json",
        "final_decision_v1_1.json",
        "metric_reconstruction_v1_1.json",
        "bootstrap_corrected_v1_1.json",
        "telemetry_information_loss_v1_1.json",
        "trace_error_representation_invariant.json",
        "provenance_normalization_v1_1.json",
        "input_manifest.json",
    ):
        copy_registered(repo, package, assets, copied_sources, f"artifacts/evidence_closure/{filename}", f"raw/evidence_closure/{filename}", "CANONICAL", "canonical Evidence Closure machine-readable evidence", True, "This is the canonical machine-readable layer; legacy summaries remain historical.")


def copy_tree_files(
    repo: Path,
    package: Path,
    assets: MutableMapping[str, Dict[str, Any]],
    copied_sources: MutableMapping[str, bool],
    source_root: str,
    asset_root: str,
    evidence_class: str,
    thesis_use: str,
    exclude: Optional[Sequence[str]] = None,
    skip_npz: bool = True,
) -> None:
    excluded = set(exclude or ())
    root = repo / source_root
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(repo).as_posix()
        if relative in excluded or (skip_npz and path.suffix == ".npz"):
            continue
        suffix = path.relative_to(root).as_posix()
        copy_registered(repo, package, assets, copied_sources, relative, f"{asset_root}/{suffix}", evidence_class, thesis_use, True, "Large .npz state/feature arrays are indexed only." if path.suffix == ".npz" else "")


def copy_development_raw(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], copied_sources: MutableMapping[str, bool]) -> None:
    for variant in ("z0", "z1", "z2", "z3", "z3_shuffle"):
        for dataset in DATASETS:
            copy_tree_files(repo, package, assets, copied_sources, f"artifacts/runs/{variant}/{dataset}", f"raw/p3/{variant}/{dataset}", "DEVELOPMENT", "P3 internal OOF evidence")
    for filename in ("p3_a2_summary.json",):
        copy_registered(repo, package, assets, copied_sources, f"artifacts/runs/{filename}", f"raw/p3/{filename}", "DEVELOPMENT", "P3 internal OOF evidence")
    copy_registered(repo, package, assets, copied_sources, "artifacts/bootstrap/p3_g1_bootstrap.json", "raw/p3/p3_g1_bootstrap.json", "DEVELOPMENT", "P3 paired bootstrap and NO-GO decision evidence", True, "P3 is development/internal evidence and P3-G1 is NO-GO/CLOSED.")
    copy_tree_files(repo, package, assets, copied_sources, "artifacts/p4_g0", "raw/p4", "DEVELOPMENT", "P4 matched ablation and diagnostics", skip_npz=True)
    copy_tree_files(repo, package, assets, copied_sources, "artifacts/final_audit", "raw/controls", "SUPPORTING", "final falsification controls and audit evidence", exclude=("artifacts/final_audit/anchor_feasibility.json",), skip_npz=True)
    for path in sorted((repo / "artifacts/opt/o3_search_space").rglob("*")):
        if path.is_file():
            relative = path.relative_to(repo).as_posix()
            copy_registered(repo, package, assets, copied_sources, relative, f"raw/optimization/{path.relative_to(repo / 'artifacts/opt').as_posix()}", "DEVELOPMENT", "configuration robustness and frozen optimization post-study")
    for root_name in ("o4_nested", "final/GLOBAL-OPT", "final/PER-DATASET-OPT"):
        copy_tree_files(repo, package, assets, copied_sources, f"artifacts/opt/{root_name}", f"raw/optimization/{root_name}", "DEVELOPMENT", "configuration robustness and frozen optimization post-study", skip_npz=True)
    for relative in ("artifacts/opt/diagnostics/shortcut_audit.json",):
        copy_registered(repo, package, assets, copied_sources, relative, f"raw/optimization/{relative.split('artifacts/opt/', 1)[1]}", "SUPPORTING", "bounded label-firewall and shortcut audit")
    copy_registered(repo, package, assets, copied_sources, "artifacts/postmortem/case_rank_transitions.csv", "raw/controls/postmortem/case_rank_transitions.csv", "DIAGNOSTIC", "post-hoc diagnostic evidence")
    for filename in ("coverage_analysis.json", "fault_root_fold_analysis.json", "mi_subset_analysis.json", "z2_vs_z1_bootstrap.json"):
        copy_registered(repo, package, assets, copied_sources, f"artifacts/postmortem/{filename}", f"raw/controls/postmortem/{filename}", "DIAGNOSTIC", "post-hoc diagnostic evidence")
    copy_registered(repo, package, assets, copied_sources, "artifacts/audits/magnitude_inversion.json", "raw/controls/postmortem/magnitude_inversion.json", "DIAGNOSTIC", "post-hoc magnitude inversion diagnostic")


def source_artifact_index(repo: Path, assets: MutableMapping[str, Dict[str, Any]], copied_sources: Mapping[str, bool]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    roots = repo / "artifacts"
    for path in sorted(p for p in roots.rglob("*") if p.is_file()):
        relative = path.relative_to(repo).as_posix()
        if "baseline_eval" in relative:
            raise ExportError(f"baseline artifact encountered during Ada scan: {relative}")
        blob = git_blob(repo, SOURCE_COMMIT, relative)
        actual_sha = sha256_file(path)
        source_blob_bytes = run_git(repo, "show", f"{SOURCE_COMMIT}:{relative}", text=False)
        if sha256_bytes(source_blob_bytes) != actual_sha:
            raise ExportError("frozen source artifact has changed in working tree", {"path": relative, "expected_blob_sha256": sha256_bytes(source_blob_bytes), "actual_sha256": actual_sha})
        if relative in copied_sources:
            role = "copied compact evidence"
            needed = True
            reason = ""
        elif relative == "artifacts/opt/final/bootstrap.json":
            role = "legacy optimization bootstrap"
            needed = False
            reason = "HISTORICAL_SUPERSEDED; use raw/evidence_closure/bootstrap_corrected_v1_1.json and BOOTSTRAP_FORENSIC_AUDIT.md"
        elif relative.startswith("artifacts/opt/o1_historical/") or relative == "artifacts/opt/o2_telemetry/event_feature_audit.json":
            role = "historical optimization or telemetry audit"
            needed = False
            reason = "Historical/legacy artifact retained in the source index; canonical Evidence Closure correction is used."
        elif path.suffix == ".npz":
            role = "large frozen feature or model-state array"
            needed = False
            reason = "Large array is not duplicated; its path, size, Git blob, and SHA-256 are indexed."
        elif relative.endswith("/sources.jsonl"):
            role = "path-heavy source mapping"
            needed = False
            reason = "Path-heavy source mapping is indexed only; compact inputs/labels/registry are retained."
        elif relative == "artifacts/final_audit/anchor_feasibility.json":
            role = "complete anchor feasibility audit"
            needed = True
            reason = "Full report is indexed; a compact, status-only thesis diagnostic is exported."
        else:
            role = "supporting source artifact"
            needed = True
            reason = "Not copied because the thesis package keeps only compact evidence needed for its tables."
        rows.append({
            "path": relative,
            "type": path.suffix.lstrip(".") or "file",
            "size": path.stat().st_size,
            "git_blob_sha": blob,
            "sha256_if_available": actual_sha,
            "scientific_role": role,
            "needed_for_thesis": needed,
            "copied": relative in copied_sources,
            "reason_not_copied": reason,
        })
    return rows


def source_code_index(repo: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    frozen_method = {"src/rca/features.py", "src/rca/final_method.py", "src/rca/p4.py", "src/rca/evaluator.py"}
    closure = {"src/rca/evidence_bootstrap.py", "src/rca/evidence_closure.py", "src/rca/evidence_final.py", "src/rca/evidence_telemetry.py", "src/rca/evidence_trace_error.py", "src/rca/final_audit.py"}
    for path in sorted(list((repo / "src/rca").glob("*.py")) + list((repo / "scripts").glob("*.py"))):
        relative = path.relative_to(repo).as_posix()
        if relative in frozen_method:
            role, canonicality, used_for = "frozen V1 method implementation", "FROZEN_METHOD", "feature schema, final method, and scorer semantics"
        elif relative in closure:
            role, canonicality, used_for = "evidence producer or final audit implementation", "EVIDENCE_PRODUCER", "Evidence Closure, controls, telemetry, replay, or diagnostic evidence"
        elif relative.startswith("scripts/"):
            role, canonicality, used_for = "experiment/audit producer script", "EVIDENCE_PRODUCER", "P3/P4/optimization/final audit provenance"
        else:
            role, canonicality, used_for = "supporting RCA implementation", "SUPPORTING", "frozen repository reproducibility context"
        rows.append({
            "path": relative,
            "source_commit": SOURCE_COMMIT,
            "git_blob_sha": git_blob(repo, SOURCE_COMMIT, relative),
            "sha256": sha256_file(path),
            "role": role,
            "canonicality": canonicality,
            "used_for": used_for,
        })
    return rows


def superseded_artifact_rows(repo: Path) -> List[Dict[str, Any]]:
    patterns = ["artifacts/opt/final/bootstrap.json", "artifacts/opt/o1_historical/*", "artifacts/opt/o2_telemetry/event_feature_audit.json"]
    paths: List[str] = []
    for pattern in patterns:
        if pattern.endswith("/*"):
            paths.extend(p.relative_to(repo).as_posix() for p in sorted((repo / pattern[:-2]).glob("*")) if p.is_file())
        elif (repo / pattern).is_file():
            paths.append(pattern)
    rows = []
    for relative in sorted(paths):
        rows.append({
            "path": relative,
            "evidence_class": "HISTORICAL_SUPERSEDED",
            "citation_allowed": True,
            "use_boundary": "historical context only; never a canonical metric or paired interval",
            "canonical_replacement": "artifacts/evidence_closure/bootstrap_corrected_v1_1.json; docs/BOOTSTRAP_FORENSIC_AUDIT.md" if "bootstrap" in relative else "artifacts/evidence_closure/telemetry_information_loss_v1_1.json; docs/TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md" if "telemetry" in relative else "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md; docs/RCA_THESIS_CLAIM_MATRIX.md",
            "reason": "Retained immutable legacy evidence; later canonical interpretation supersedes its metric/terminology use.",
        })
    return rows


def excluded_scope_rows(repo: Path, document_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in document_rows:
        if row["evidence_class"] == "OUT_OF_SCOPE":
            path = str(row["path"])
            rows.append({"path": path, "scope": "external-baseline context", "exists_in_source": (repo / path).exists(), "status": "EXCLUDED_BY_SCOPE", "reason": "This package contains Ada-RCA frozen evidence only; no baseline result or comparison is exported."})
    for path, scope, reason in (
        ("artifacts/baseline_eval/", "external baseline artifacts", "Never inspected, copied, or included."),
        ("docs/baseline_eval/", "external baseline documents", "Never inspected, copied, or included."),
        ("src/baseline_eval/", "external baseline code", "Never inspected, copied, or included."),
    ):
        rows.append({"path": path, "scope": scope, "exists_in_source": (repo / path).exists(), "status": "EXCLUDED_BY_SCOPE", "reason": reason})
    return rows


def flatten_json_rows(value: Any, path: str = "") -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        rows: List[Dict[str, Any]] = []
        for key in sorted(value):
            child = f"{path}.{key}" if path else str(key)
            rows.extend(flatten_json_rows(value[key], child))
        return rows
    if isinstance(value, list):
        return [{"statistic": path, "value": json_inline(value)}]
    return [{"statistic": path, "value": value}]


def p3_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], case_rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    summary = json_load(repo / "artifacts/runs/p3_a2_summary.json")
    metric_rows = []
    for variant, label in (("z0", "Z0"), ("z1", "Z1"), ("z2", "Z2"), ("z3", "Z3"), ("z3_shuffle", "Z3-SHUFFLE")):
        for dataset in DATASETS:
            metrics = json_load(repo / "artifacts/runs" / variant / dataset / "metrics.json")["overall_cases"]
            metric_rows.append({"variant": label, "dataset": dataset, "n_cases": EXPECTED_CASES[dataset], **{metric: metrics[metric] for metric in METRICS}, "evidence_class": "DEVELOPMENT", "confirmatory": False, "gate_status": "P3-G1 NO-GO / CLOSED" if label in ("Z3", "Z3-SHUFFLE") else "DEVELOPMENT"})
    p3_sources = ["artifacts/runs/p3_a2_summary.json", "artifacts/bootstrap/p3_g1_bootstrap.json"]
    generated_csv(repo, package, assets, "data/ablation/p3_representation_metrics.csv", ("variant", "dataset", "n_cases", *METRICS, "evidence_class", "confirmatory", "gate_status"), sorted(metric_rows, key=lambda row: ((DATASETS.index(row["dataset"])), ("Z0", "Z1", "Z2", "Z3", "Z3-SHUFFLE").index(row["variant"]))), p3_sources, "DEVELOPMENT", "P3 representation metrics; internal evidence only", True, "Read overall metrics from the five committed P3 variant runs.", "P3-G1 is NO-GO/CLOSED; this is not external confirmation.")
    bootstrap = json_load(repo / "artifacts/bootstrap/p3_g1_bootstrap.json")
    comparison_rows = []
    temporal_rows = []
    names = {"z3_minus_z1": "Z3 - Z1", "z3_minus_z3_shuffle": "Z3 - Z3-SHUFFLE"}
    for comparison in ("z3_minus_z1", "z3_minus_z3_shuffle"):
        for unit in ("re2ob", "re2tt", "mean_ob_tt"):
            report = bootstrap["comparisons"][comparison][unit]
            row = {"comparison": names[comparison], "dataset": "equal_dataset_mean" if unit == "mean_ob_tt" else unit, "point_delta_avg5": report["point_delta_avg5"], "ci_lower": report["ci95"][0], "ci_upper": report["ci95"][1], "resamples": report["resamples"], "seed": report["seed"], "delta_by_fault": report.get("delta_by_fault", ""), "evidence_class": "DEVELOPMENT", "confirmatory": False, "decision": "P3-G1 NO-GO / CLOSED"}
            comparison_rows.append(row)
            if comparison == "z3_minus_z3_shuffle":
                temporal_rows.append(row)
    fields = ("comparison", "dataset", "point_delta_avg5", "ci_lower", "ci_upper", "resamples", "seed", "delta_by_fault", "evidence_class", "confirmatory", "decision")
    generated_csv(repo, package, assets, "data/ablation/p3_bootstrap.csv", fields, sorted(comparison_rows, key=lambda row: (row["comparison"], DATASETS.index(row["dataset"]) if row["dataset"] in DATASETS else 2)), ["artifacts/bootstrap/p3_g1_bootstrap.json"], "DEVELOPMENT", "P3 paired bootstrap evidence", True, "Flattened the committed fault-stratified paired bootstrap without changing its direction or estimator.", "The Z3-vs-Z1 gate remains NO-GO; Z3-vs-shuffle is a narrow temporal-order comparison.")
    generated_csv(repo, package, assets, "data/ablation/p3_temporal_comparisons.csv", fields, sorted(temporal_rows, key=lambda row: DATASETS.index(row["dataset"]) if row["dataset"] in DATASETS else 2), ["artifacts/bootstrap/p3_g1_bootstrap.json", "docs/P3_G1_DECISION.md"], "DEVELOPMENT", "narrow temporal-alignment evidence", True, "Selected only the predeclared Z3 versus deterministic Z3-SHUFFLE comparison.", "This does not support universal full-trajectory superiority.")


P4_DEFINITIONS = {
    "A0": ("Z1-ABS", 32, "absolute four-channel base plus frozen Z1 representation", "event-level Conditional Logit, lambda 1.0, train-fold-only StandardScaler"),
    "A1": ("Z1-REL", 64, "within-event feature-wise percentile transform of Z1-ABS", "event-level Conditional Logit, lambda 1.0, train-fold-only StandardScaler"),
    "A2": ("Z2-ABS", 68, "frozen final Ada-RCA V1 four-channel Z2 representation", "event-level Conditional Logit, lambda 1.0, train-fold-only StandardScaler"),
    "A3": ("Z2-REL", 136, "within-event feature-wise percentile transform of Z2-ABS", "event-level Conditional Logit, lambda 1.0, train-fold-only StandardScaler"),
}


def p4_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]]) -> None:
    summary = json_load(repo / "artifacts/p4_g0/metrics/summary.json")
    rows = []
    for dataset in DATASETS:
        for variant in ("A0", "A1", "A2", "A3"):
            display, dimension, definition, scorer = P4_DEFINITIONS[variant]
            rows.append({"dataset": dataset, "variant": variant, "representation": display, "dimension": dimension, "representation_definition": definition, "scorer_definition": scorer, "n_cases": EXPECTED_CASES[dataset], **summary[dataset][variant], "evidence_class": "DEVELOPMENT", "confirmatory": False, "gate_status": "P4-G0 NO-GO / CLOSED"})
    fields = ("dataset", "variant", "representation", "dimension", "representation_definition", "scorer_definition", "n_cases", *METRICS, "evidence_class", "confirmatory", "gate_status")
    generated_csv(repo, package, assets, "data/ablation/p4_a0_a1_a2_a3_metrics.csv", fields, rows, ["artifacts/p4_g0/metrics/summary.json", "docs/P4_G0_RESULTS.md"], "DEVELOPMENT", "P4 matched ablation metrics", True, "Flattened the four committed P4 variants and retained their exact definitions.", "P4-G0 candidate-relative consistency gate is NO-GO/CLOSED.")
    effects = []
    for dataset in DATASETS:
        for comparison in ("A1-A0", "A2-A0", "A3-A1", "A3-A2"):
            for metric, value in summary[dataset]["effects"][comparison].items():
                effects.append({"dataset": dataset, "comparison": comparison, "metric": metric, "point_delta": value, "evidence_class": "DEVELOPMENT", "confirmatory": False, "gate_status": "P4-G0 NO-GO / CLOSED"})
    generated_csv(repo, package, assets, "data/ablation/p4_main_effects.csv", ("dataset", "comparison", "metric", "point_delta", "evidence_class", "confirmatory", "gate_status"), effects, ["artifacts/p4_g0/metrics/summary.json", "docs/P4_G0_DECISION.md"], "DEVELOPMENT", "P4 matched main effects", True, "Read the committed A1-A0, A2-A0, A3-A1, and A3-A2 effects.")
    interactions = []
    for dataset in DATASETS:
        for metric, value in summary[dataset]["interaction"].items():
            interactions.append({"dataset": dataset, "metric": metric, "interaction": value, "formula": "(A3-A2) - (A1-A0)", "evidence_class": "DEVELOPMENT", "confirmatory": False, "gate_status": "P4-G0 NO-GO / CLOSED"})
    generated_csv(repo, package, assets, "data/ablation/p4_interaction.csv", ("dataset", "metric", "interaction", "formula", "evidence_class", "confirmatory", "gate_status"), interactions, ["artifacts/p4_g0/metrics/summary.json", "docs/P4_G0_RESULTS.md"], "DEVELOPMENT", "P4 factorial interaction", True, "Computed from the committed P4 effect definitions.")
    bootstrap = json_load(repo / "artifacts/p4_g0/bootstrap/p4_g0_bootstrap.json")
    boot_rows = []
    for comparison in ("A1-A0", "A2-A0", "A3-A1", "A3-A2"):
        for metric in ("AC@1", "Avg@5"):
            report_group = bootstrap["comparisons"][comparison][metric]
            for unit in ("re2ob", "re2tt", "mean_ob_tt"):
                report = report_group[unit]
                boot_rows.append({"comparison": comparison, "metric": metric, "dataset": "equal_dataset_mean" if unit == "mean_ob_tt" else unit, "point_delta": report["point_delta"], "ci_lower": report["ci95"][0], "ci_upper": report["ci95"][1], "resamples": bootstrap["resamples"], "seed": bootstrap["seed"], "sampling": bootstrap["sampling"], "evidence_class": "DEVELOPMENT", "confirmatory": False, "decision": "P4-G0 NO-GO / CLOSED"})
    generated_csv(repo, package, assets, "data/ablation/p4_bootstrap.csv", ("comparison", "metric", "dataset", "point_delta", "ci_lower", "ci_upper", "resamples", "seed", "sampling", "evidence_class", "confirmatory", "decision"), boot_rows, ["artifacts/p4_g0/bootstrap/p4_g0_bootstrap.json"], "DEVELOPMENT", "P4 paired bootstrap evidence", True, "Flattened the committed P4 bootstrap with its original metric direction and estimator.")
    source = repo / "artifacts/p4_g0/metrics/case_transitions.csv"
    destination = package / "data/ablation/p4_case_transitions.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    make_manifest_record(repo, package, assets, "data/ablation/p4_case_transitions.csv", ["artifacts/p4_g0/metrics/case_transitions.csv"], SOURCE_COMMIT, "DEVELOPMENT", "P4 case-level transitions", True, "COPIED", "byte-identical copy of committed P4 transition evidence", "P4 transitions are descriptive development evidence.")


def controls_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]]) -> None:
    summary = json_load(repo / "artifacts/final_audit/summary.json")
    controls = (("FINAL-Z2", "final"), ("S0-A", "s0_deterministic"), ("S0-B", "s0_tie_neutral"), ("S1", "s1"), ("S2", "s2"))
    rows = []
    for dataset in DATASETS:
        for control, key in controls:
            metrics = summary["datasets"][dataset][key]
            rows.append({"dataset": dataset, "control": control, "n_cases": EXPECTED_CASES[dataset], **{metric: metrics[metric] for metric in METRICS}, "evidence_class": "SUPPORTING", "confirmatory": False, "control_role": "frozen final method" if control == "FINAL-Z2" else "falsification/control"})
    fields = ("dataset", "control", "n_cases", *METRICS, "evidence_class", "confirmatory", "control_role")
    generated_csv(repo, package, assets, "data/controls/control_absolute_metrics.csv", fields, rows, ["artifacts/final_audit/summary.json", "docs/FINAL_RCA_CONTROL_AUDIT.md"], "SUPPORTING", "final method and falsification-control metrics", True, "Flattened absolute metrics from the committed final-audit summary; S3 is kept separate as a service-identity diagnostic.")
    final_by = {(row["dataset"]): row for row in rows if row["control"] == "FINAL-Z2"}
    delta_rows = []
    for row in rows:
        if row["control"] == "FINAL-Z2":
            continue
        final = final_by[row["dataset"]]
        for metric in METRICS:
            delta_rows.append({"dataset": row["dataset"], "control": row["control"], "metric": metric, "final_minus_control": float(final[metric]) - float(row[metric]), "evidence_class": "SUPPORTING", "confirmatory": False})
    generated_csv(repo, package, assets, "data/controls/final_minus_controls.csv", ("dataset", "control", "metric", "final_minus_control", "evidence_class", "confirmatory"), delta_rows, ["artifacts/final_audit/summary.json"], "SUPPORTING", "final-minus-control effect sizes", True, "Derived by subtracting each control's committed absolute metric from FINAL-Z2.")
    comparison = json_load(repo / "artifacts/final_audit/control_comparisons.json")
    boot_rows = []
    for control_key in ("s0_deterministic", "s0_tie_neutral", "s1", "s2"):
        for metric in ("AC@1", "Avg@5"):
            block = comparison[control_key][metric]
            for dataset in DATASETS:
                report = block["datasets"][dataset]
                boot_rows.append({"dataset": dataset, "control": {"s0_deterministic": "S0-A", "s0_tie_neutral": "S0-B", "s1": "S1", "s2": "S2"}[control_key], "metric": metric, "point_delta": report["point_delta"], "ci_lower": report["ci95"][0], "ci_upper": report["ci95"][1], "resamples": block["resamples"], "seed": block["seed"], "direction": "FINAL-Z2 - CONTROL", "state": block.get("state", ""), "evidence_class": "SUPPORTING", "confirmatory": False})
            mean_report = block["equal_dataset_mean"]
            boot_rows.append({"dataset": "equal_dataset_mean", "control": {"s0_deterministic": "S0-A", "s0_tie_neutral": "S0-B", "s1": "S1", "s2": "S2"}[control_key], "metric": metric, "point_delta": mean_report["point_delta"], "ci_lower": mean_report["ci95"][0], "ci_upper": mean_report["ci95"][1], "resamples": block["resamples"], "seed": block["seed"], "direction": "FINAL-Z2 - CONTROL", "state": block.get("state", ""), "evidence_class": "SUPPORTING", "confirmatory": False})
    generated_csv(repo, package, assets, "data/controls/control_bootstrap.csv", ("dataset", "control", "metric", "point_delta", "ci_lower", "ci_upper", "resamples", "seed", "direction", "state", "evidence_class", "confirmatory"), boot_rows, ["artifacts/final_audit/control_comparisons.json", "docs/FINAL_RCA_CONTROL_AUDIT.md"], "SUPPORTING", "final-versus-control paired bootstrap", True, "Flattened the committed 10,000-resample control comparisons.")
    s3 = json_load(repo / "artifacts/final_audit/s3_service_identity/summary.json")
    s3_rows = []
    for dataset in DATASETS:
        for row in flatten_json_rows(s3[dataset]):
            s3_rows.append({"dataset": dataset, "scope": row["statistic"].split(".", 1)[0], "statistic": row["statistic"], "value": row["value"], "evidence_class": "DIAGNOSTIC", "confirmatory": False, "interpretation": "SERVICE_IDENTITY_DIAGNOSTIC; not an RCA baseline"})
    generated_csv(repo, package, assets, "data/controls/service_identity_diagnostic.csv", ("dataset", "scope", "statistic", "value", "evidence_class", "confirmatory", "interpretation"), s3_rows, ["artifacts/final_audit/s3_service_identity/summary.json", "docs/S3_SERVICE_IDENTITY_PROBE.md"], "DIAGNOSTIC", "service identity and fingerprint diagnostic", True, "Flattened the committed S3 diagnostic summary without treating it as an RCA baseline.", "S3 is a diagnostic control, not an RCA baseline or causal result.")


def optimization_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]]) -> None:
    feature_names = json_load(repo / "artifacts/opt/o4_nested/re2ob/feature_names.json")["representations"]
    representations = ("Z1-M", "M+L", "M+TE", "M+TL", "M+L+TL", "FULL-Z2")
    search_rows = []
    for representation in representations:
        names = list(feature_names[representation])
        channels = []
        for name in names:
            channel = str(name).split(".", 1)[0]
            if channel not in channels:
                channels.append(channel)
        search_rows.append({"representation": representation, "channels": channels, "dimension": len(names), "status": "FROZEN_SEARCH_SPACE", "evidence_class": "SUPPORTING", "confirmatory": False})
    generated_csv(repo, package, assets, "data/optimization/representation_search_space.csv", ("representation", "channels", "dimension", "status", "evidence_class", "confirmatory"), search_rows, ["artifacts/opt/o3_search_space/README.md", "artifacts/opt/o4_nested/re2ob/feature_names.json", "docs/OPT_SEARCH_SPACE_FREEZE_V1.md"], "SUPPORTING", "configuration robustness search space", True, "Read the six representation keys and dimensions from the frozen O4 feature-name manifest.", "This is a frozen post-study search space, not a comprehensive sensitivity analysis.")
    config = json_load(repo / "artifacts/opt/o4_nested/re2ob/config.json")
    lambda_rows = []
    for ranker, spec in sorted(config["rankers"].items()):
        if spec.get("available"):
            for value in spec.get("lambda", []):
                lambda_rows.append({"ranker": ranker, "lambda": value, "status": "EXECUTED_GRID", "reason": "frozen Conditional-Logit lambda grid", "evidence_class": "SUPPORTING", "confirmatory": False})
        else:
            lambda_rows.append({"ranker": ranker, "lambda": "", "status": "NOT EXECUTED — DEPENDENCY UNAVAILABLE", "reason": spec.get("reason", "dependency unavailable"), "evidence_class": "SUPPORTING", "confirmatory": False})
    generated_csv(repo, package, assets, "data/optimization/lambda_grid.csv", ("ranker", "lambda", "status", "reason", "evidence_class", "confirmatory"), lambda_rows, ["artifacts/opt/o4_nested/re2ob/config.json", "docs/OPT_SEARCH_SPACE_FREEZE_V1.md"], "SUPPORTING", "frozen ranker and lambda grid", True, "Read the executed Conditional-Logit grid and preserve unavailable-ranker statuses.", "Unavailable XGBoost/LightGBM is not a negative performance result.")
    nested_rows = []
    for dataset in DATASETS:
        trace = json_load(repo / "artifacts/opt/o4_nested" / dataset / "selection_trace.json")
        for entry in trace:
            selected = entry["selected"]
            nested_rows.append({"row_type": "outer_fold_selection", "dataset": dataset, "outer_fold": entry["outer_fold"], "representation": selected["representation"], "ranker": selected["ranker"], "lambda": selected["lambda"], "inner_mean_Avg@5": selected["mean_Avg@5"], "inner_AC@1_mean": selected["AC@1_mean"], "outer_test_case_count": len(entry["outer_test_event_ids"]), "selection_status": "SELECTED", "evidence_class": "DEVELOPMENT", "confirmatory": False})
    for ranker in ("R1-XGBoost", "R2-LightGBM"):
        nested_rows.append({"row_type": "ranker_status", "dataset": "all", "outer_fold": "", "representation": "", "ranker": ranker, "lambda": "", "inner_mean_Avg@5": "", "inner_AC@1_mean": "", "outer_test_case_count": "", "selection_status": "NOT EXECUTED — DEPENDENCY UNAVAILABLE", "evidence_class": "DEVELOPMENT", "confirmatory": False})
    nested_fields = ("row_type", "dataset", "outer_fold", "representation", "ranker", "lambda", "inner_mean_Avg@5", "inner_AC@1_mean", "outer_test_case_count", "selection_status", "evidence_class", "confirmatory")
    generated_csv(repo, package, assets, "data/optimization/nested_selection_summary.csv", nested_fields, sorted(nested_rows, key=lambda row: (row["row_type"], row["dataset"], str(row["outer_fold"]), row["ranker"])), ["artifacts/opt/o4_nested/re2ob/selection_trace.json", "artifacts/opt/o4_nested/re2tt/selection_trace.json", "docs/OPT_NESTED_SELECTION_RESULTS.md"], "DEVELOPMENT", "nested selection and ranker availability", True, "Flattened the six frozen outer-fold selection records; unavailable rankers remain explicit.")
    closure = json_load(repo / "artifacts/evidence_closure/metric_reconstruction_v1_1.json")
    for track, output_name, class_name, integrity in (("GLOBAL-OPT", "global_opt_metrics.csv", "SUPPORTING", "FULL_RANKING_INTEGRITY_PASS"), ("PER-DATASET-OPT", "per_dataset_opt_metrics.csv", "DEVELOPMENT", "FULL_RANKING_INTEGRITY_NOT_AUDITABLE")):
        rows = []
        for dataset in DATASETS:
            metrics = json_load(repo / "artifacts/opt/final" / track / dataset / "metrics.json")["overall_cases"]
            evidence = closure["tracks"][track]["datasets"][dataset]["evidence_levels"]
            rows.append({"track": track, "dataset": dataset, "n_cases": EXPECTED_CASES[dataset], **{metric: metrics[metric] for metric in METRICS}, "full_ranking_integrity": evidence["FULL_RANKING_INTEGRITY"]["status"], "rank_metric_sufficient": evidence["RANK_METRIC_SUFFICIENT"]["status"], "identical_to_v1": track == "GLOBAL-OPT" and (repo / "artifacts/opt/final" / track / dataset / "predictions.jsonl").read_bytes() == (repo / "artifacts/final_method" / dataset / "predictions.jsonl").read_bytes(), "evidence_class": class_name, "confirmatory": False})
        generated_csv(repo, package, assets, f"data/optimization/{output_name}", ("track", "dataset", "n_cases", *METRICS, "full_ranking_integrity", "rank_metric_sufficient", "identical_to_v1", "evidence_class", "confirmatory"), rows, [f"artifacts/opt/final/{track}/re2ob/metrics.json", f"artifacts/opt/final/{track}/re2tt/metrics.json", "artifacts/evidence_closure/metric_reconstruction_v1_1.json"], class_name, "GLOBAL-OPT or PER-DATASET-OPT post-study metrics", True, "Read committed post-study metrics and canonical evidence-level semantics.", "PER-DATASET complete candidate rankings remain NOT_AUDITABLE.")
    corrected = json_load(repo / "artifacts/evidence_closure/bootstrap_corrected_v1_1.json")
    boot_rows = []
    for comparison, block in sorted(corrected["comparisons"].items()):
        for dataset, report in sorted(block["datasets"].items()):
            for metric, result in sorted(report["metrics"].items()):
                boot_rows.append({"comparison": comparison, "candidate": report["candidate"], "baseline": report["baseline"], "dataset": dataset, "metric": metric, "point_delta": result["point_delta"], "ci_lower": result["ci95"][0], "ci_upper": result["ci95"][1], "resamples": result["iterations"], "seed": result["seed"], "direction": result["direction"], "sampling_unit": result["sampling_unit"], "evidence_class": "CANONICAL", "confirmatory": False})
    generated_csv(repo, package, assets, "data/optimization/corrected_optimization_bootstrap.csv", ("comparison", "candidate", "baseline", "dataset", "metric", "point_delta", "ci_lower", "ci_upper", "resamples", "seed", "direction", "sampling_unit", "evidence_class", "confirmatory"), boot_rows, ["artifacts/evidence_closure/bootstrap_corrected_v1_1.json", "docs/BOOTSTRAP_FORENSIC_AUDIT.md"], "CANONICAL", "corrected optimization uncertainty evidence", True, "Flattened only the canonical Candidate-minus-V1 bootstrap artifact; legacy intervals are excluded.", "Intervals are conditional on fixed frozen root ranks and do not establish a consistent optimization gain.")


def telemetry_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]]) -> None:
    telemetry = json_load(repo / "artifacts/evidence_closure/telemetry_information_loss_v1_1.json")
    funnel_rows = []
    for dataset in DATASETS:
        for modality in ("Metric", "Log", "Trace Error", "Trace Latency"):
            report = telemetry["datasets"][dataset]["candidate_case_funnel"][modality]
            funnel_rows.append({"dataset": dataset, "modality": modality, "statistical_unit": report["statistical_unit"], **report["counts"], **{f"{key}_rate": value for key, value in report["rates_of_eligible"].items()}, "evidence_class": "CANONICAL", "confirmatory": False})
    funnel_fields = ("dataset", "modality", "statistical_unit", "eligible", "mapped", "window_observed", "pre_observed", "post_observed", "scale_valid", "feature_active", "eligible_rate", "mapped_rate", "window_observed_rate", "pre_observed_rate", "post_observed_rate", "scale_valid_rate", "feature_active_rate", "evidence_class", "confirmatory")
    generated_csv(repo, package, assets, "data/telemetry/modality_information_funnel.csv", funnel_fields, funnel_rows, ["artifacts/evidence_closure/telemetry_information_loss_v1_1.json", "docs/TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md"], "CANONICAL", "candidate-case modality information funnel", True, "Flattened candidate-case counts and eligible-denominator rates from canonical Gate 3 evidence.")
    te_rows = []
    for dataset in DATASETS:
        diagnostics = telemetry["datasets"][dataset]["trace_error_diagnostics"]
        for name in sorted(diagnostics["counts"]):
            te_rows.append({"dataset": dataset, "diagnostic": name, "count": diagnostics["counts"][name], "rate_of_eligible": diagnostics["rates_of_eligible"][name], "definition": diagnostics["definitions"].get(name, ""), "evidence_class": "CANONICAL", "confirmatory": False})
    generated_csv(repo, package, assets, "data/telemetry/trace_error_information_loss.csv", ("dataset", "diagnostic", "count", "rate_of_eligible", "definition", "evidence_class", "confirmatory"), te_rows, ["artifacts/evidence_closure/telemetry_information_loss_v1_1.json", "docs/TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md"], "CANONICAL", "Trace Error information-loss mechanism", True, "Flattened canonical Trace Error funnel diagnostics; no sparse replacement was run.", "This records robust-scale information loss, not a claim that raw Trace Error has no information.")
    invariant = json_load(repo / "artifacts/evidence_closure/trace_error_representation_invariant.json")
    invariant_rows = []
    for dataset in DATASETS:
        report = invariant["datasets"][dataset]
        for item in report["dimension_statistics"]:
            invariant_rows.append({"dataset": dataset, "frozen_z2_index": item["frozen_z2_index"], "feature": item["feature"], "min": item["min"], "max": item["max"], "variance": item["variance"], "unique_count": item["unique_count"], "varies_within_any_case": item["varies_across_candidates_within_any_case"], "globally_nonzero": item["globally_nonzero"], "nonzero_variance_dimensions": report["dimensions_with_nonzero_variance"], "classification": report["classification"], "evidence_class": "CANONICAL", "confirmatory": False})
    generated_csv(repo, package, assets, "data/telemetry/trace_error_representation_invariant.csv", ("dataset", "frozen_z2_index", "feature", "min", "max", "variance", "unique_count", "varies_within_any_case", "globally_nonzero", "nonzero_variance_dimensions", "classification", "evidence_class", "confirmatory"), invariant_rows, ["artifacts/evidence_closure/trace_error_representation_invariant.json", "docs/TRACE_ERROR_REPRESENTATION_INVARIANT.md"], "CANONICAL", "frozen 17D Trace Error representation invariant", True, "Read-only flattening of the canonical 17D invariant; no feature removal or model scoring was performed.", "The official frozen representation remains four-channel 68D Z2, not 51D.")


def diagnostics_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], case_rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    magnitude = json_load(repo / "artifacts/audits/magnitude_inversion.json")
    magnitude_rows = []
    for dataset in DATASETS:
        report = magnitude[dataset]
        for statistic in ("case_count", "mi_1_count", "mi_1_ratio", "mi_3_count", "mi_3_ratio"):
            magnitude_rows.append({"dataset": dataset, "scope": "overall", "statistic": statistic, "value": report.get(statistic), "evidence_class": "DIAGNOSTIC", "confirmatory": False})
        for fault in FAULT_ORDER:
            block = report.get("by_fault", {}).get(fault, {})
            for statistic in ("cases", "mi_1_count", "mi_1_ratio", "mi_3_count", "mi_3_ratio"):
                if statistic in block:
                    magnitude_rows.append({"dataset": dataset, "scope": FAULT_DISPLAY[fault], "statistic": statistic, "value": block[statistic], "evidence_class": "DIAGNOSTIC", "confirmatory": False})
    generated_csv(repo, package, assets, "data/diagnostics/magnitude_inversion_summary.csv", ("dataset", "scope", "statistic", "value", "evidence_class", "confirmatory"), magnitude_rows, ["artifacts/audits/magnitude_inversion.json", "docs/MAGNITUDE_INVERSION_AUDIT.md"], "DIAGNOSTIC", "magnitude inversion diagnostic", True, "Flattened the committed label-free magnitude inversion summary.")
    anchor = json_load(repo / "artifacts/final_audit/anchor_feasibility.json")
    anchor_rows = [{"scope": "overall", "statistic": key, "value": anchor[key], "evidence_class": "DIAGNOSTIC", "confirmatory": False} for key in ("status", "performance_computed", "unsupported_count", "all_180_cases_supported", "anchor_performance_authorized_by_feasibility", "window_width_seconds")]
    for dataset in DATASETS:
        unsupported = [
            row
            for row in anchor.get("unsupported", [])
            if str(row.get("dataset", "")).lower().replace("-", "").replace("_", "") == dataset
        ]
        anchor_rows.append({"scope": dataset, "statistic": "unsupported_combinations_in_dataset", "value": len(unsupported), "evidence_class": "DIAGNOSTIC", "confirmatory": False})
        anchor_rows.append({"scope": dataset, "statistic": "affected_cases_in_dataset", "value": len({row.get("case_id") for row in unsupported}), "evidence_class": "DIAGNOSTIC", "confirmatory": False})
    generated_csv(repo, package, assets, "data/diagnostics/anchor_feasibility_summary.csv", ("scope", "statistic", "value", "evidence_class", "confirmatory"), anchor_rows, ["artifacts/final_audit/anchor_feasibility.json", "docs/ANCHOR_FEASIBILITY_AUDIT.md"], "DIAGNOSTIC", "anchor feasibility limitation", True, "Exported only compact status/count fields from the complete feasibility audit; the 77-row report remains indexed.", "No shifted-anchor performance exists under the frozen pipeline.")
    s3 = json_load(repo / "artifacts/final_audit/s3_service_identity/summary.json")
    fingerprint_rows = []
    for dataset in DATASETS:
        report = s3[dataset]
        for statistic in ("feature_dimension", "empirical_majority_class_accuracy"):
            fingerprint_rows.append({"dataset": dataset, "scope": "overall", "statistic": statistic, "value": report.get(statistic), "evidence_class": "DIAGNOSTIC", "confirmatory": False, "interpretation": "service/telemetry fingerprint risk diagnostic"})
        for fold, fold_report in sorted(report.get("folds", {}).items(), key=lambda item: int(item[0])):
            for statistic in ("top1_accuracy", "macro_f1", "train_event_count", "test_event_count", "train_rows", "test_rows"):
                fingerprint_rows.append({"dataset": dataset, "scope": f"fold_{fold}", "statistic": statistic, "value": fold_report.get(statistic), "evidence_class": "DIAGNOSTIC", "confirmatory": False, "interpretation": "service/telemetry fingerprint risk diagnostic"})
    generated_csv(repo, package, assets, "data/diagnostics/service_fingerprint_summary.csv", ("dataset", "scope", "statistic", "value", "evidence_class", "confirmatory", "interpretation"), fingerprint_rows, ["artifacts/final_audit/s3_service_identity/summary.json", "docs/FINAL_RCA_CONTROL_AUDIT.md"], "DIAGNOSTIC", "service/telemetry fingerprint risk", True, "Selected high-level S3 diagnostic statistics; no explicit-leakage result is promoted to absolute no-leakage.")
    failure_rows = []
    for dataset in DATASETS:
        worst = sorted(case_rows[dataset], key=lambda row: (-int(row["root_rank"]), str(row["case_id"])))[:10]
        for row in worst:
            failure_rows.append({"dataset": dataset, "case_id": row["case_id"], "fault_type": FAULT_DISPLAY[row["fault_type"]], "root_service": row["root_service"], "root_rank": row["root_rank"], "candidate_count": row["candidate_count"], "AC@1": row["AC@1"], "AC@3": row["AC@3"], "AC@5": row["AC@5"], "Avg@5": row["Avg@5"], "MRR": row["MRR"], "evidence_class": "DIAGNOSTIC", "confirmatory": False})
    generated_csv(repo, package, assets, "data/diagnostics/failure_case_summary.csv", ("dataset", "case_id", "fault_type", "root_service", "root_rank", "candidate_count", *METRICS, "evidence_class", "confirmatory"), failure_rows, ["artifacts/final_method/re2ob/predictions.jsonl", "artifacts/final_method/re2tt/predictions.jsonl", "artifacts/source/re2ob/labels.jsonl", "artifacts/source/re2tt/labels.jsonl"], "DIAGNOSTIC", "worst-case root-rank diagnostic", True, "Selected the ten largest reconstructed root ranks per dataset; this is descriptive and not a new metric.")
    postmortem_sources = ["artifacts/postmortem/coverage_analysis.json", "artifacts/postmortem/fault_root_fold_analysis.json", "artifacts/postmortem/mi_subset_analysis.json", "artifacts/postmortem/z2_vs_z1_bootstrap.json", "artifacts/p4_g0/metrics/subgroup_diagnostics.json"]
    postmortem_rows = []
    for relative in postmortem_sources:
        value = json_load(repo / relative)
        for row in flatten_json_rows(value):
            postmortem_rows.append({"source_file": relative, "statistic": row["statistic"], "value": row["value"], "evidence_class": "DIAGNOSTIC", "confirmatory": False})
    generated_csv(repo, package, assets, "data/diagnostics/postmortem_subgroup_summary.csv", ("source_file", "statistic", "value", "evidence_class", "confirmatory"), postmortem_rows, postmortem_sources + ["docs/P3_POSTMORTEM.md", "docs/P4_G0_FAILURE_ANALYSIS.md"], "DIAGNOSTIC", "post-hoc subgroup and postmortem diagnostics", True, "Flattened committed postmortem/subgroup summaries without re-running telemetry or fitting models.")
    coverage = json_load(repo / "artifacts/postmortem/coverage_analysis.json")
    coverage_rows = []
    for dataset in DATASETS:
        for row in flatten_json_rows(coverage[dataset]):
            coverage_rows.append({"dataset": dataset, "statistic": row["statistic"], "value": row["value"], "evidence_class": "DIAGNOSTIC", "confirmatory": False})
    generated_csv(repo, package, assets, "data/diagnostics/coverage_summary.csv", ("dataset", "statistic", "value", "evidence_class", "confirmatory"), coverage_rows, ["artifacts/postmortem/coverage_analysis.json", "docs/P3_POSTMORTEM.md"], "DIAGNOSTIC", "coverage/rank-gain diagnostic", True, "Flattened committed descriptive coverage analysis.")


def frozen_configuration(repo: Path, feature_info: Mapping[str, Any]) -> Dict[str, Any]:
    features_text = (repo / "src/rca/features.py").read_text(encoding="utf-8")
    final_text = (repo / "src/rca/final_method.py").read_text(encoding="utf-8")
    if "np.percentile(observed, 90)" not in features_text or "(float(anchor_time) - 600.0)" not in features_text or "scale = 1.4826" not in features_text:
        raise ExportError("frozen feature code does not contain the expected window/Q90/robust-scale semantics")
    configs = [json_load(repo / "artifacts/final_method" / dataset / "config.json") for dataset in DATASETS]
    if any(config["feature_order_sha256"] != feature_info["feature_order_sha256"] for config in configs):
        raise ExportError("final config feature order digest disagrees with code-derived schema")
    row = {
        "scope": "Ada-RCA V1 frozen configuration",
        "event_window_pre_seconds": 600,
        "event_window_post_seconds": 600,
        "n_bins": int(parse_json_constant(repo / "src/rca/features.py", "N_BINS")),
        "bin_seconds": float(parse_json_constant(repo / "src/rca/features.py", "BIN_SECONDS")),
        "pre_bins": int(parse_json_constant(repo / "src/rca/features.py", "PRE_BINS")),
        "post_bins": int(parse_json_constant(repo / "src/rca/features.py", "POST_BINS")),
        "channels": feature_info["channels"],
        "q_percentile": 90,
        "onset_threshold": float(parse_json_constant(repo / "src/rca/features.py", "ONSET_THRESHOLD")),
        "normalization_center": "pre-event median",
        "normalization_scale": "1.4826 * pre-event MAD",
        "scale_fallback": "pre-event IQR / 1.349 when MAD < 1e-6; valid scale >= 1e-6",
        "representation_dimension": int(feature_info["dimension"]),
        "scaler_scope": "train-fold candidate rows only",
        "ranker": "event-level Conditional Logit",
        "l2_lambda": float(configs[0]["lambda"]),
        "dtype": "float64",
        "gradient_tolerance": float(configs[0]["gradient_tolerance"]),
        "outer_folds": 3,
        "ranking_tiebreak": "descending score; ascending candidate name",
        "feature_order_sha256": feature_info["feature_order_sha256"],
        "evidence_class": "CANONICAL",
        "confirmatory": True,
    }
    return row


def model_fit_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], feature_info: Mapping[str, Any]) -> None:
    rows = []
    replay_rows = []
    for dataset in DATASETS:
        manifest = json_load(repo / "artifacts/final_method" / dataset / "model_state_manifest.json")
        for fold in ("0", "1", "2"):
            state = manifest[fold]
            rows.append({"dataset": dataset, "fold": int(fold), "lambda": state["lambda"], "initial_loss": state["initial_loss"], "final_loss": state["final_loss"], "gradient_norm": state["gradient_norm"], "iterations": state["iterations"], "converged": state["converged"], "float_dtype": state["float_dtype"], "feature_dimension": state["feature_dimension"], "feature_order_sha256": state["feature_order_sha256"], "evidence_class": "CANONICAL", "confirmatory": True})
        audit = json_load(repo / "artifacts/final_method" / dataset / "replay_audit.json")
        replay_rows.append({"dataset": dataset, "case_count": audit["case_count"], "ranking_identical": all(audit[key]["ranking_identical"] for key in ("fit_to_persisted_replay", "fresh_fit_to_committed_p4_a2", "persisted_state_to_committed_p4_a2")), "max_abs_score_difference": max(audit[key]["max_abs_score_difference"] for key in ("fit_to_persisted_replay", "fresh_fit_to_committed_p4_a2", "persisted_state_to_committed_p4_a2")), "checksum_status": "PASS" if audit["integrity_status"] == "INTEGRITY_VALID" else "FAIL", "integrity_status": audit["integrity_status"], "all_folds_converged": audit["all_folds_converged"], "metrics_exact": audit["metrics_exact_between_fit_and_persisted_replay"], "evidence_class": "CANONICAL", "confirmatory": True})
    fields = ("dataset", "fold", "lambda", "initial_loss", "final_loss", "gradient_norm", "iterations", "converged", "float_dtype", "feature_dimension", "feature_order_sha256", "evidence_class", "confirmatory")
    source_paths = [f"artifacts/final_method/{dataset}/model_state_manifest.json" for dataset in DATASETS]
    generated_csv(repo, package, assets, "data/reproducibility/model_fit_diagnostics.csv", fields, rows, source_paths, "CANONICAL", "persisted model-fit numerical integrity", True, "Read-only flattening of persisted fold-state manifests; no model was refit.")
    generated_csv(repo, package, assets, "data/final/model_fit_diagnostics.csv", fields, rows, source_paths, "CANONICAL", "final model-fit numerical integrity", True, "Same persisted-state diagnostic exposed next to final performance tables; no model was refit.")
    generated_csv(repo, package, assets, "data/reproducibility/replay_integrity.csv", ("dataset", "case_count", "ranking_identical", "max_abs_score_difference", "checksum_status", "integrity_status", "all_folds_converged", "metrics_exact", "evidence_class", "confirmatory"), replay_rows, [f"artifacts/final_method/{dataset}/replay_audit.json" for dataset in DATASETS], "CANONICAL", "frozen replay integrity", True, "Read-only flattening of persisted-state replay audits.")


def final_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], case_rows: Mapping[str, Sequence[Mapping[str, Any]]], feature_info: Mapping[str, Any]) -> None:
    case_fields = ("dataset", "case_id", "fold", "fault_type", "root_service", "candidate_count", "root_rank", "AC@1", "AC@2", "AC@3", "AC@4", "AC@5", "Avg@5", "MRR")
    all_cases = [row for dataset in DATASETS for row in case_rows[dataset]]
    generated_csv(repo, package, assets, "data/final/case_root_ranks.csv", case_fields, all_cases, [f"artifacts/final_method/{dataset}/predictions.jsonl" for dataset in DATASETS] + [f"artifacts/source/{dataset}/labels.jsonl" for dataset in DATASETS] + [f"artifacts/splits/{dataset}/assignments.json" for dataset in DATASETS], "CANONICAL", "independently reconstructed case-level root ranks", True, "Joined prediction rankings to frozen label sidecars and fold assignments, then applied the frozen one-indexed rank formulas.", "This is a pure statistical reconstruction; it does not regenerate predictions.")
    case_sources = [f"artifacts/final_method/{dataset}/predictions.jsonl" for dataset in DATASETS] + [f"artifacts/source/{dataset}/labels.jsonl" for dataset in DATASETS] + [f"artifacts/splits/{dataset}/assignments.json" for dataset in DATASETS]
    generated_csv(repo, package, assets, "data/final/case_level_metrics.csv", case_fields, all_cases, case_sources, "CANONICAL", "case-level final metrics", True, "Same independently reconstructed case rows exposed as a case-metric table.")
    overall = grouped_metric_rows(case_rows, "overall")
    for row in overall:
        row.update({"evidence_class": "CANONICAL", "confirmatory": True, "reconstruction_status": "MATCHES_FROZEN_CANONICAL_WITHIN_1E-12"})
    generated_csv(repo, package, assets, "data/final/overall_metrics.csv", ("dataset", "overall", "n_cases", *METRICS, "evidence_class", "confirmatory", "reconstruction_status"), overall, case_sources + ["artifacts/evidence_closure/metric_reconstruction_v1_1.json"], "CANONICAL", "final overall metrics", True, "Aggregated independently reconstructed case root ranks and checked equality against canonical metrics.")
    fault_rows = grouped_metric_rows(case_rows, "fault_type")
    for row in fault_rows:
        row["fault_type"] = FAULT_DISPLAY[row["fault_type"]]
        row.update({"evidence_class": "CANONICAL", "confirmatory": True})
    generated_csv(repo, package, assets, "data/final/fault_level_metrics.csv", ("dataset", "fault_type", "n_cases", *METRICS, "evidence_class", "confirmatory"), fault_rows, case_sources, "CANONICAL", "fault-level final metrics", True, "Aggregated reconstructed case root ranks by the six frozen fault types.")
    root_rows = grouped_metric_rows(case_rows, "root_service")
    root_rows = [{**row, "evidence_class": "CANONICAL", "confirmatory": True} for row in root_rows]
    generated_csv(repo, package, assets, "data/final/root_level_metrics.csv", ("dataset", "root_service", "n_cases", *METRICS, "evidence_class", "confirmatory"), root_rows, case_sources, "CANONICAL", "root-level final metrics", True, "Aggregated reconstructed case root ranks by true root service.")
    fold_rows = grouped_metric_rows(case_rows, "fold")
    fold_rows = [{**row, "evidence_class": "CANONICAL", "confirmatory": True} for row in fold_rows]
    generated_csv(repo, package, assets, "data/final/fold_level_metrics.csv", ("dataset", "fold", "n_cases", *METRICS, "evidence_class", "confirmatory"), fold_rows, case_sources, "CANONICAL", "fold-level final metrics", True, "Aggregated reconstructed case root ranks by frozen outer fold.")
    distribution_rows = []
    for dataset in DATASETS:
        ranks = sorted(int(row["root_rank"]) for row in case_rows[dataset])
        counts = Counter(ranks)
        mean_rank = sum(ranks) / len(ranks)
        median_rank = median(ranks)
        p90_position = 0.90 * (len(ranks) - 1)
        lower = int(math.floor(p90_position))
        upper = int(math.ceil(p90_position))
        p90_rank = ranks[lower] if lower == upper else ranks[lower] + (ranks[upper] - ranks[lower]) * (p90_position - lower)
        cumulative = 0
        for rank in sorted(counts):
            cumulative += counts[rank]
            distribution_rows.append({"dataset": dataset, "rank": rank, "count": counts[rank], "fraction": counts[rank] / len(ranks), "cumulative_fraction": cumulative / len(ranks), "mean_rank": mean_rank, "median_rank": median_rank, "p90_rank": p90_rank, "worst_rank": max(ranks), "evidence_class": "DESCRIPTIVE", "confirmatory": False})
    generated_csv(repo, package, assets, "data/final/root_rank_distribution.csv", ("dataset", "rank", "count", "fraction", "cumulative_fraction", "mean_rank", "median_rank", "p90_rank", "worst_rank", "evidence_class", "confirmatory"), distribution_rows, case_sources, "DESCRIPTIVE", "descriptive root-rank distribution", True, "Counted independently reconstructed one-indexed root ranks; this does not replace headline metrics.")
    candidate_rows = []
    for dataset in DATASETS:
        registry = json_load(repo / "artifacts/source" / dataset / "service_registry.json")
        candidate_rows.append({"dataset": dataset, "dataset_name": registry["dataset"], "candidate_count": len(registry["services"]), "n_cases": EXPECTED_CASES[dataset], "registry_sha256": sha256_file(repo / "artifacts/source" / dataset / "service_registry.json"), "evidence_class": "CANONICAL", "confirmatory": True})
    generated_csv(repo, package, assets, "data/final/candidate_universe_summary.csv", ("dataset", "dataset_name", "candidate_count", "n_cases", "registry_sha256", "evidence_class", "confirmatory"), candidate_rows, [f"artifacts/source/{dataset}/service_registry.json" for dataset in DATASETS], "CANONICAL", "candidate universe semantics", True, "Read the frozen legal candidate registries and case counts.")
    generated_json(repo, package, assets, "data/reproducibility/frozen_configuration.json", frozen_configuration(repo, feature_info), ["src/rca/features.py", "src/rca/final_method.py", "artifacts/final_method/re2ob/config.json", "artifacts/final_method/re2tt/config.json", "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md"], "CANONICAL", "frozen method configuration", True, "Cross-checked code constants, final configs, and canonical freeze wording.")
    config_row = frozen_configuration(repo, feature_info)
    generated_csv(repo, package, assets, "data/reproducibility/frozen_configuration.csv", tuple(config_row.keys()), [config_row], ["src/rca/features.py", "src/rca/final_method.py", "artifacts/final_method/re2ob/config.json", "artifacts/final_method/re2tt/config.json", "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md"], "CANONICAL", "frozen method configuration", True, "Same frozen configuration exposed as a thesis-friendly fact table.")
    generated_csv(repo, package, assets, "data/reproducibility/feature_schema_68d.csv", ("feature_index", "channel", "family", "field"), feature_info["schema_rows"], ["src/rca/features.py", "src/rca/final_method.py"], "CANONICAL", "dynamic frozen Z2 feature schema", True, "Read field constants from the frozen implementation and computed the feature-order digest.")


def markdown_table(fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    def cell(value: Any) -> str:
        text = str(csv_value(value))
        return text.replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(fieldnames) + " |", "| " + " | ".join("---" for _ in fieldnames) + " |"]
    lines.extend("| " + " | ".join(cell(row.get(field, "")) for field in fieldnames) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def table_assets(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]]) -> None:
    table_sources = {
        "01_dataset_and_protocol": ["docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md", "docs/RCA_THESIS_RESULTS_PACKAGE.md", "data/reproducibility/frozen_configuration.csv"],
        "02_ada_rca_overall_performance": ["artifacts/evidence_closure/metric_reconstruction_v1_1.json", "artifacts/final_method/re2ob/metrics.json", "artifacts/final_method/re2tt/metrics.json", "docs/RCA_THESIS_RESULTS_PACKAGE.md"],
        "03_ada_rca_fault_level_performance": ["artifacts/final_method/re2ob/predictions.jsonl", "artifacts/final_method/re2tt/predictions.jsonl", "artifacts/source/re2ob/labels.jsonl", "artifacts/source/re2tt/labels.jsonl", "docs/RCA_THESIS_RESULTS_PACKAGE.md"],
        "04_p4_ablation": ["artifacts/p4_g0/metrics/summary.json", "artifacts/p4_g0/bootstrap/p4_g0_bootstrap.json", "docs/P4_G0_RESULTS.md", "docs/P4_G0_DECISION.md"],
        "05_p3_representation_evidence": ["artifacts/runs/p3_a2_summary.json", "artifacts/bootstrap/p3_g1_bootstrap.json", "docs/P3_G1_DECISION.md"],
        "06_falsification_controls": ["artifacts/final_audit/summary.json", "artifacts/final_audit/control_comparisons.json", "docs/FINAL_RCA_CONTROL_AUDIT.md"],
        "07_configuration_robustness": ["artifacts/opt/o4_nested/re2ob/selection_trace.json", "artifacts/opt/o4_nested/re2tt/selection_trace.json", "artifacts/evidence_closure/bootstrap_corrected_v1_1.json", "docs/OPT_NESTED_SELECTION_RESULTS.md", "docs/BOOTSTRAP_FORENSIC_AUDIT.md"],
    }
    main_rows: Dict[str, List[Dict[str, Any]]] = {}
    # Dataset/protocol table is intentionally compact and claim-safe.
    protocol_rows = [
        {"dataset": "RE2-OB", "cases": 90, "candidates": 11, "folds": 3, "test_cases_per_fold": 30, "representation": "68D Z2", "ranker": "Conditional Logit", "scope": "known-system benchmark; not untouched external", "evidence_class": "CANONICAL"},
        {"dataset": "RE2-TT", "cases": 90, "candidates": 68, "folds": 3, "test_cases_per_fold": 30, "representation": "68D Z2", "ranker": "Conditional Logit", "scope": "known-system benchmark; not untouched external", "evidence_class": "CANONICAL"},
    ]
    main_rows["01_dataset_and_protocol"] = protocol_rows
    overall_fields, overall_rows = read_csv_rows(package / "data/final/overall_metrics.csv")
    main_rows["02_ada_rca_overall_performance"] = overall_rows
    fault_fields, fault_rows = read_csv_rows(package / "data/final/fault_level_metrics.csv")
    main_rows["03_ada_rca_fault_level_performance"] = fault_rows
    p4_fields, p4_rows = read_csv_rows(package / "data/ablation/p4_a0_a1_a2_a3_metrics.csv")
    effect_fields, effect_rows = read_csv_rows(package / "data/ablation/p4_main_effects.csv")
    interaction_fields, interaction_rows = read_csv_rows(package / "data/ablation/p4_interaction.csv")
    main_rows["04_p4_ablation"] = [{"row_kind": "variant", **row} for row in p4_rows] + [{"row_kind": "effect", **row} for row in effect_rows] + [{"row_kind": "interaction", **row} for row in interaction_rows]
    p3_fields, p3_rows = read_csv_rows(package / "data/ablation/p3_representation_metrics.csv")
    _, temporal_rows = read_csv_rows(package / "data/ablation/p3_temporal_comparisons.csv")
    main_rows["05_p3_representation_evidence"] = [{"row_kind": "variant", **row} for row in p3_rows] + [{"row_kind": "temporal_comparison", **row} for row in temporal_rows]
    control_fields, control_rows = read_csv_rows(package / "data/controls/control_absolute_metrics.csv")
    _, control_bootstrap_rows = read_csv_rows(package / "data/controls/control_bootstrap.csv")
    main_rows["06_falsification_controls"] = [{"row_kind": "absolute", **row} for row in control_rows] + [{"row_kind": "bootstrap", **row} for row in control_bootstrap_rows]
    search_fields, search_rows = read_csv_rows(package / "data/optimization/representation_search_space.csv")
    _, nested_rows = read_csv_rows(package / "data/optimization/nested_selection_summary.csv")
    _, global_rows = read_csv_rows(package / "data/optimization/global_opt_metrics.csv")
    _, per_rows = read_csv_rows(package / "data/optimization/per_dataset_opt_metrics.csv")
    main_rows["07_configuration_robustness"] = [{"row_kind": "search_space", **row} for row in search_rows] + [{"row_kind": "nested_selection", **row} for row in nested_rows] + [{"row_kind": "global_opt", **row} for row in global_rows] + [{"row_kind": "per_dataset_opt", **row} for row in per_rows]
    main_fieldnames = {
        "01_dataset_and_protocol": ("dataset", "cases", "candidates", "folds", "test_cases_per_fold", "representation", "ranker", "scope", "evidence_class"),
        "02_ada_rca_overall_performance": tuple(overall_fields),
        "03_ada_rca_fault_level_performance": tuple(fault_fields),
        "04_p4_ablation": ("row_kind", "dataset", "variant", "representation", "dimension", "n_cases", "AC@1", "AC@3", "AC@5", "Avg@5", "MRR", "comparison", "metric", "point_delta", "interaction", "gate_status", "evidence_class", "confirmatory"),
        "05_p3_representation_evidence": ("row_kind", "variant", "dataset", "n_cases", "AC@1", "AC@3", "AC@5", "Avg@5", "MRR", "comparison", "point_delta_avg5", "ci_lower", "ci_upper", "gate_status", "decision", "evidence_class", "confirmatory"),
        "06_falsification_controls": ("row_kind", "dataset", "control", "n_cases", "AC@1", "AC@3", "AC@5", "Avg@5", "MRR", "metric", "point_delta", "ci_lower", "ci_upper", "direction", "state", "evidence_class", "confirmatory"),
        "07_configuration_robustness": ("row_kind", "track", "dataset", "representation", "channels", "dimension", "n_cases", "AC@1", "AC@3", "AC@5", "Avg@5", "MRR", "inner_mean_Avg@5", "inner_AC@1_mean", "ranker", "lambda", "selection_status", "full_ranking_integrity", "rank_metric_sufficient", "identical_to_v1", "evidence_class", "confirmatory"),
    }
    for name, rows in main_rows.items():
        base = f"tables/main/{name}"
        sources = table_sources[name]
        fields = main_fieldnames[name]
        generated_csv(repo, package, assets, base + ".csv", fields, rows, [source for source in sources if not source.startswith("data/")] or sources, "CANONICAL" if name in ("01_dataset_and_protocol", "02_ada_rca_overall_performance", "03_ada_rca_fault_level_performance") else "DEVELOPMENT" if name in ("04_p4_ablation", "05_p3_representation_evidence") else "SUPPORTING", "thesis-ready candidate table", True, "Generated from the corresponding frozen data asset and claim-safe evidence class.", "Development, diagnostic, and post-study rows retain their explicit limitations.")
        generated_text(repo, package, assets, base + ".md", markdown_table(fields, rows), [source for source in sources if not source.startswith("data/")] or sources, "CANONICAL" if name in ("01_dataset_and_protocol", "02_ada_rca_overall_performance", "03_ada_rca_fault_level_performance") else "DEVELOPMENT" if name in ("04_p4_ablation", "05_p3_representation_evidence") else "SUPPORTING", "thesis-ready candidate table", True, "Rendered deterministic Markdown from the corresponding CSV candidate table.", "Do not promote bounded development/diagnostic rows into universal claims.")
    appendix = {
        "root_level_performance": "data/final/root_level_metrics.csv",
        "fold_level_performance": "data/final/fold_level_metrics.csv",
        "rank_distribution": "data/final/root_rank_distribution.csv",
        "model_fit_integrity": "data/reproducibility/model_fit_diagnostics.csv",
        "telemetry_information_loss": "data/telemetry/modality_information_funnel.csv",
        "trace_error_invariant": "data/telemetry/trace_error_representation_invariant.csv",
        "service_identity_diagnostic": "data/controls/service_identity_diagnostic.csv",
        "anchor_feasibility": "data/diagnostics/anchor_feasibility_summary.csv",
        "postmortem_diagnostics": "data/diagnostics/postmortem_subgroup_summary.csv",
    }
    for name, source in appendix.items():
        fields, rows = read_csv_rows(package / source)
        source_paths = [source] if source.startswith("artifacts/") or source.startswith("docs/") else ["docs/RCA_THESIS_RESULTS_PACKAGE.md"]
        evidence_class = "DIAGNOSTIC" if name in ("service_identity_diagnostic", "anchor_feasibility", "postmortem_diagnostics") else "CANONICAL" if name in ("root_level_performance", "fold_level_performance", "model_fit_integrity", "telemetry_information_loss", "trace_error_invariant") else "DESCRIPTIVE"
        generated_csv(repo, package, assets, f"tables/appendix/{name}.csv", tuple(fields), rows, ["docs/RCA_THESIS_RESULTS_PACKAGE.md", source] if not source.startswith("data/") else ["docs/RCA_THESIS_RESULTS_PACKAGE.md"], evidence_class, "appendix evidence table", True, "Copied the deterministic data view into an appendix table.", "Diagnostic tables are not confirmatory evidence." if evidence_class == "DIAGNOSTIC" else "")
        generated_text(repo, package, assets, f"tables/appendix/{name}.md", markdown_table(fields, rows), ["docs/RCA_THESIS_RESULTS_PACKAGE.md"], evidence_class, "appendix evidence table", True, "Rendered deterministic Markdown from the appendix CSV.", "Diagnostic tables are not confirmatory evidence." if evidence_class == "DIAGNOSTIC" else "")


def readme_text(source_commit: str, exp_commit: str) -> str:
    return f"""# Ada-RCA V1 Thesis Asset Package

This directory is the single thesis-writing entry point for the frozen Ada-RCA
V1 evidence package. It contains Ada-RCA evidence only; external baseline
execution and baseline comparison are outside this package and are not included.

## Freeze identity

- source branch: `research/evidence-closure`
- source commit: `{source_commit}`
- V1 scientific reference: `{V1_REFERENCE_COMMIT}`
- frozen optimization record: `{OPTIMIZATION_COMMIT}`
- Evidence Closure decision record: `{EVIDENCE_DECISION_COMMIT}`
- exporter commit: `{exp_commit}`
- terminal scientific decision: `RCA_FREEZE_READY_WITH_LIMITATION`

Ada-RCA V1 is a supervised service-level root-cause ranking pipeline for a
confirmed failure event. Its frozen method is the candidate-wise event-relative
four-channel 68D Z2 representation followed by event-level Conditional Logit
and a complete deterministic service ranking. The package does not redefine
choice-set semantics, claim variable candidate universes, or promote the
pipeline to causal discovery.

## Where to find evidence

- `raw/final_method/`: byte-identical final metrics, predictions, configs,
  provenance, checksums, replay audits, and persisted-state manifests.
- `raw/source/` and `raw/splits/`: labels, legal candidate registries, input
  metadata, and frozen fold assignments needed for independent reconstruction.
- `raw/evidence_closure/`: canonical machine-readable semantic, metric,
  bootstrap, telemetry, Trace Error, provenance, and final-decision evidence.
- `data/final/`: independently reconstructed case/root/fault/fold/overall
  metrics, rank distributions, and candidate-universe summaries.
- `data/reproducibility/`: code-derived 68D feature schema, frozen
  configuration, persisted fit diagnostics, and replay integrity.
- `data/ablation/`: P3 and P4 development evidence. P3-G1 and P4-G0 remain
  `NO-GO / CLOSED`; their bounded comparisons are not external confirmation.
- `data/controls/`: final falsification controls and the separate S3 service
  identity diagnostic. S3 is not an RCA baseline.
- `data/optimization/`: configuration robustness / frozen optimization
  post-study evidence. Corrected bootstrap uses `Candidate - V1`; the legacy
  interval artifact is not used.
- `data/telemetry/`: candidate-case modality funnel, Trace Error information
  loss, and the exact frozen 17D Trace Error invariant. The official method
  remains four-channel 68D Z2 even where the TE block is nondiscriminative.
- `data/diagnostics/`: descriptive magnitude, anchor-feasibility,
  fingerprint, failure-case, coverage, and postmortem diagnostics. Every row
  is marked `evidence_class=DIAGNOSTIC` and `confirmatory=false`.
- `tables/`: deterministic thesis candidate tables; `tables/TABLE_CATALOG.md`
  records placement and claim boundaries.
- `refs/`: complete document, source-code, source-artifact, supersession, and
  excluded-scope indexes.
- `scripts/`: deterministic exporter and fail-closed validator.

## Evidence classes and wording boundary

`CANONICAL` is the current frozen evidence layer. `SUPPORTING` records method,
protocol, control, or provenance context. `DEVELOPMENT` covers internal P3,
P4, and post-study selection evidence. `DIAGNOSTIC` records limitations and
post-hoc mechanisms without confirmatory status. `HISTORICAL_SUPERSEDED` is
retained for traceability but cannot supply canonical metrics or bootstrap
intervals. `OUT_OF_SCOPE` material is indexed as excluded and is not copied.

The supported claim boundary is the exact matrix in
`docs/canonical/RCA_THESIS_CLAIM_MATRIX.md`. Safe claims remain bounded to
RE2-OB and RE2-TT, their fixed candidate registries, frozen folds, and the
committed protocol. The package does not support SOTA, causal discovery,
unseen-system or unseen-root generalization, untouched external confirmation,
universal representation superiority, absolute no-leakage, or tree-ranker
inferiority. XGBoost and LightGBM are explicitly `NOT EXECUTED — DEPENDENCY
UNAVAILABLE`, not negative results.

`MANIFEST.csv` records byte hashes and source provenance for every package file
except the manifest index itself, which is necessarily self-referential.
`PROVENANCE.json` records the source and exporter identities without an ambient
timestamp. Re-running the exporter after the exporter commit should produce
byte-equivalent generated outputs.
"""


def table_catalog(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]]) -> None:
    rows = [
        ("01_dataset_and_protocol", "Dataset and frozen protocol", "What data, candidate universes, folds, and method configuration define V1?", "raw/source; raw/splits; data/reproducibility/frozen_configuration.csv", "CANONICAL", "MAIN_TEXT", "Bounded task/protocol description on RE2-OB and RE2-TT.", "No unseen-system, causal, or external-confirmation claim.", "READY"),
        ("02_ada_rca_overall_performance", "Ada-RCA V1 overall performance", "What are the independently reconstructed frozen V1 ranking metrics?", "data/final/overall_metrics.csv; data/final/case_root_ranks.csv", "CANONICAL", "MAIN_TEXT", "V1 ranking performance within the two frozen benchmarks.", "No external generalization or SOTA comparison.", "READY"),
        ("03_ada_rca_fault_level_performance", "Fault-level Ada-RCA V1 performance", "How do the frozen metrics distribute across the six fault types?", "data/final/fault_level_metrics.csv", "CANONICAL", "MAIN_TEXT", "Descriptive fault-stratified V1 results.", "Does not establish universal fault invariance.", "READY"),
        ("04_p4_ablation", "P4 matched candidate-relative ablation", "Does A1-A0 satisfy the preregistered cross-dataset gate?", "data/ablation/p4_a0_a1_a2_a3_metrics.csv; data/ablation/p4_bootstrap.csv", "DEVELOPMENT", "DISCUSSION", "Exact P4 effects and the NO-GO decision.", "Cannot be post-hoc rescued by pooled improvement.", "READY_WITH_LIMITATION"),
        ("05_p3_representation_evidence", "P3 representation evidence", "What do Z0/Z1/Z2/Z3 and deterministic shuffle comparisons show?", "data/ablation/p3_representation_metrics.csv; data/ablation/p3_bootstrap.csv", "DEVELOPMENT", "DISCUSSION", "Narrow aligned-temporal evidence relative to Z3-SHUFFLE.", "Z3-vs-Z1 gate is NO-GO; not external confirmation.", "READY_WITH_LIMITATION"),
        ("06_falsification_controls", "Final falsification controls", "How do final Z2 results compare with controls and observability structures?", "data/controls/control_absolute_metrics.csv; data/controls/control_bootstrap.csv", "SUPPORTING", "LIMITATION", "Control separation and remaining fingerprint risk.", "S3 is a service-identity diagnostic, not an RCA baseline.", "READY_WITH_LIMITATION"),
        ("07_configuration_robustness", "Configuration robustness / frozen optimization post-study", "What was selected inside the predeclared representation and lambda grid?", "data/optimization/representation_search_space.csv; data/optimization/nested_selection_summary.csv; data/optimization/corrected_optimization_bootstrap.csv", "SUPPORTING", "DISCUSSION", "GLOBAL identity and bounded PER-DATASET development signal.", "Do not call this comprehensive sensitivity analysis; PER-DATASET full rankings are NOT_AUDITABLE.", "READY_WITH_LIMITATION"),
        ("A1_root_level_performance", "Root-level final performance", "How do reconstructed ranks distribute by true root service?", "tables/appendix/root_level_performance.csv", "CANONICAL", "APPENDIX", "Root-stratified descriptive V1 results.", "Known systems and candidate registries only.", "READY"),
        ("A2_fold_level_performance", "Fold-level final performance", "Are metrics visible for each frozen outer fold?", "tables/appendix/fold_level_performance.csv", "CANONICAL", "APPENDIX", "Fold-level reproducibility.", "Not an independent replication.", "READY"),
        ("A3_rank_distribution", "Root-rank distribution", "What is the descriptive distribution of one-indexed root ranks?", "tables/appendix/rank_distribution.csv", "DESCRIPTIVE", "APPENDIX", "Descriptive rank distribution and worst ranks.", "Does not replace the frozen headline metrics.", "READY"),
        ("A4_model_fit_integrity", "Model fit and replay integrity", "Do persisted folds converge and replay identically?", "data/reproducibility/model_fit_diagnostics.csv; data/reproducibility/replay_integrity.csv", "CANONICAL", "APPENDIX", "Numerical and replay integrity.", "Identity verification is not fresh performance evidence.", "READY"),
        ("A5_telemetry_information_loss", "Modality information funnel", "Where do candidate-case telemetry pairs become inactive?", "data/telemetry/modality_information_funnel.csv", "CANONICAL", "LIMITATION", "Candidate-case funnel and scale-loss evidence.", "Raw-record lineage is not fully auditable.", "READY_WITH_LIMITATION"),
        ("A6_trace_error_invariant", "Trace Error frozen invariant", "What exact TE block remains in frozen Z2?", "data/telemetry/trace_error_representation_invariant.csv", "CANONICAL", "LIMITATION", "Frozen TE block is candidate-nondiscriminative in both datasets.", "Does not show a sparse-aware replacement would improve RCA.", "READY_WITH_LIMITATION"),
        ("A7_service_identity_diagnostic", "Service identity diagnostic", "Could stable service/telemetry fingerprints explain part of control behavior?", "data/diagnostics/service_fingerprint_summary.csv; data/controls/service_identity_diagnostic.csv", "DIAGNOSTIC", "LIMITATION", "Bounded diagnostic risk evidence.", "Not an RCA baseline and not proof of absolute leakage.", "READY_WITH_LIMITATION"),
        ("A8_anchor_feasibility", "Anchor feasibility", "Is shifted-anchor robustness feasible under the frozen pipeline?", "data/diagnostics/anchor_feasibility_summary.csv", "DIAGNOSTIC", "LIMITATION", "Records ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE.", "No shifted performance was computed.", "READY_WITH_LIMITATION"),
        ("A9_postmortem_diagnostics", "Postmortem diagnostics", "What descriptive subgroup and failure patterns are preserved?", "data/diagnostics/postmortem_subgroup_summary.csv; data/diagnostics/failure_case_summary.csv", "DIAGNOSTIC", "DISCUSSION", "Descriptive limitation and mechanism evidence.", "No post-hoc subgroup is a confirmatory claim.", "READY_WITH_LIMITATION"),
    ]
    fields = ("table_id", "title", "scientific_question", "source_data", "evidence_class", "recommended_placement", "claim_supported", "claim_not_supported", "status")
    generated_text(repo, package, assets, "tables/TABLE_CATALOG.md", markdown_table(fields, [dict(zip(fields, row)) for row in rows]), ["docs/RCA_THESIS_CLAIM_MATRIX.md", "docs/RCA_THESIS_RESULTS_PACKAGE.md", "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md"], "SUPPORTING", "thesis table catalog", True, "Deterministic catalog of the generated main-text, appendix, discussion, and limitation tables.")


def provenance_and_manifest(repo: Path, package: Path, assets: MutableMapping[str, Dict[str, Any]], exp_commit: str, document_rows: Sequence[Mapping[str, Any]], source_artifacts: Sequence[Mapping[str, Any]], source_code: Sequence[Mapping[str, Any]], superseded: Sequence[Mapping[str, Any]], excluded: Sequence[Mapping[str, Any]]) -> None:
    provenance = {
        "schema_version": "ada_rca_thesis_asset_package_v1",
        "package": "thesis_assets/ada_rca_v1",
        "source_ref": SOURCE_REF,
        "source_commit": SOURCE_COMMIT,
        "v1_reference_commit": V1_REFERENCE_COMMIT,
        "frozen_optimization_commit": OPTIMIZATION_COMMIT,
        "evidence_closure_decision_commit": EVIDENCE_DECISION_COMMIT,
        "exporter_commit": exp_commit,
        "exporter_path": "thesis_assets/ada_rca_v1/scripts/export_thesis_assets.py",
        "scientific_decision": "RCA_FREEZE_READY_WITH_LIMITATION",
        "determinism": {"json_sort_keys": True, "csv_line_terminator": "\\n", "ambient_timestamp": False, "network_access": False, "model_fit": False, "optimization": False},
        "asset_counts": {"documents_scanned": len(document_rows), "documents_copied": sum(bool(row["copied"]) for row in document_rows), "source_artifacts_indexed": len(source_artifacts), "source_code_indexed": len(source_code), "superseded_artifacts_indexed": len(superseded), "excluded_scope_rows": len(excluded), "registered_assets_before_manifest": len(assets) + 1},
        "baseline_isolation": {"baseline_paths_not_read": ["artifacts/baseline_eval/", "docs/baseline_eval/", "src/baseline_eval/"], "baseline_predictions_not_included": True, "baseline_metrics_not_computed": True},
        "manifest_boundary": "MANIFEST.csv is the only package file excluded from its own hash rows because it is self-referential; PROVENANCE.json is hashed and included.",
    }
    write_json(package / "PROVENANCE.json", provenance)
    make_manifest_record(repo, package, assets, "PROVENANCE.json", ["docs/RCA_EVIDENCE_INDEX.md", "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md"], SOURCE_COMMIT, "CANONICAL", "package provenance and source boundary", True, "DERIVED", "Deterministic package provenance bound to the frozen source and exporter commit.", "No ambient timestamp is used.")
    manifest_fields = ("asset_path", "source_path", "source_commit", "source_blob_sha", "source_file_sha256", "asset_sha256", "evidence_class", "thesis_use", "citation_allowed", "derived_or_copied", "derivation", "caveat")
    manifest_rows = [assets[key] for key in sorted(assets)]
    write_csv(package / "MANIFEST.csv", manifest_fields, manifest_rows)


def run_export(repo: Path) -> Path:
    require_source_boundary(repo)
    exp_commit = exporter_commit(repo)
    package = repo / PACKAGE_REL
    package.mkdir(parents=True, exist_ok=True)
    ensure_output_dirs(package)
    assets: Dict[str, Dict[str, Any]] = {}
    copied_sources: Dict[str, bool] = {}
    case_rows = load_final_case_rows(repo)
    verify_reconstruction(repo, case_rows)
    schema_rows, feature_digest, feature_meta = feature_schema(repo)
    feature_info = {**feature_meta, "schema_rows": schema_rows, "feature_order_sha256": feature_digest}
    copy_required_raw(repo, package, assets, copied_sources)
    document_rows = copy_document_set(repo, package, assets, copied_sources)
    copy_development_raw(repo, package, assets, copied_sources)
    final_assets(repo, package, assets, case_rows, feature_info)
    p3_assets(repo, package, assets, case_rows)
    p4_assets(repo, package, assets)
    controls_assets(repo, package, assets)
    optimization_assets(repo, package, assets)
    telemetry_assets(repo, package, assets)
    diagnostics_assets(repo, package, assets, case_rows)
    model_fit_assets(repo, package, assets, feature_info)
    generated_text(repo, package, assets, "README.md", readme_text(SOURCE_COMMIT, exp_commit), ["docs/RCA_EVIDENCE_INDEX.md", "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md", "docs/RCA_THESIS_RESULTS_PACKAGE.md", "docs/RCA_THESIS_CLAIM_MATRIX.md"], "CANONICAL", "single thesis asset entry point", True, "Deterministic package guide generated from the canonical evidence boundary.")
    table_assets(repo, package, assets)
    table_catalog(repo, package, assets)
    source_artifacts = source_artifact_index(repo, assets, copied_sources)
    source_code = source_code_index(repo)
    excluded = excluded_scope_rows(repo, document_rows)
    superseded = superseded_artifact_rows(repo)
    generated_csv(repo, package, assets, "refs/source_artifact_index.csv", ("path", "type", "size", "git_blob_sha", "sha256_if_available", "scientific_role", "needed_for_thesis", "copied", "reason_not_copied"), source_artifacts, ["docs/RCA_EVIDENCE_INDEX.md", "docs/EVIDENCE_ERRATA.md"], "SUPPORTING", "complete source-artifact index", True, "Indexed every non-baseline artifact under artifacts without duplicating large arrays or legacy superseded evidence.")
    generated_csv(repo, package, assets, "refs/source_code_index.csv", ("path", "source_commit", "git_blob_sha", "sha256", "role", "canonicality", "used_for"), source_code, ["docs/RCA_EVIDENCE_INDEX.md", "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md"], "SUPPORTING", "source-code provenance index", True, "Indexed the frozen implementation and all repository scripts used by the evidence producers.")
    generated_csv(repo, package, assets, "refs/document_index.csv", ("path", "source_commit", "git_blob_sha", "title", "evidence_class", "thesis_use", "citation_allowed", "superseded_by", "copied", "asset_path", "notes"), document_rows, ["docs/RCA_EVIDENCE_INDEX.md", "docs/EVIDENCE_ERRATA.md", "docs/EVIDENCE_LEVEL_SEMANTIC_CORRECTION.md"], "SUPPORTING", "complete document inventory", True, "Scanned and explicitly classified every Markdown document under docs/." )
    generated_csv(repo, package, assets, "refs/superseded_artifacts.csv", ("path", "evidence_class", "citation_allowed", "use_boundary", "canonical_replacement", "reason"), superseded, ["docs/EVIDENCE_ERRATA.md", "docs/BOOTSTRAP_FORENSIC_AUDIT.md", "docs/TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md"], "HISTORICAL_SUPERSEDED", "superseded-artifact routing", True, "Explicitly routed legacy bootstrap and telemetry artifacts to canonical replacements.")
    generated_csv(repo, package, assets, "refs/excluded_scope.csv", ("path", "scope", "exists_in_source", "status", "reason"), excluded, ["docs/RCA_EVIDENCE_INDEX.md", "docs/RCA_THESIS_CLAIM_MATRIX.md"], "OUT_OF_SCOPE", "excluded-scope record", False, "Recorded baseline/external-comparison and other deliberately excluded scope without copying it.")
    code_files = ["thesis_assets/ada_rca_v1/scripts/export_thesis_assets.py", "thesis_assets/ada_rca_v1/scripts/validate_thesis_assets.py", "thesis_assets/ada_rca_v1/tests/test_thesis_assets.py"]
    for relative in code_files:
        if (repo / relative).is_file():
            make_manifest_record(repo, package, assets, relative[len("thesis_assets/ada_rca_v1/"):], [relative], exp_commit, "SUPPORTING", "export/validation reproducibility", True, "COPIED", "committed package exporter/validator/test source", "The package test is a lightweight validator smoke test.")
    provenance_and_manifest(repo, package, assets, exp_commit, document_rows, source_artifacts, source_code, superseded, excluded)
    return package


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_from_script())
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    try:
        package = run_export(repo)
    except ExportError as exc:
        package = repo / PACKAGE_REL
        package.mkdir(parents=True, exist_ok=True)
        report_path = package / "data/final/discrepancy_report.json"
        write_json(report_path, {"status": "FAIL_CLOSED", **exc.report})
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc), "discrepancy_report": str(report_path)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"status": "EXPORTED", "package": str(package), "source_commit": SOURCE_COMMIT, "exporter_commit": exporter_commit(repo)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
