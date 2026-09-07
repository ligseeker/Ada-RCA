"""Post-scope integration of the frozen BARO evidence into the final comparison.

This module is deliberately separate from the historical V1/V2 evaluators.
It gates every BARO label join on a committed composite scope lock, validates
the inherited evidence tracks, evaluates only BARO from its frozen records,
and copies the existing six-method V2 values by exact identity.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.baseline_eval import (
    adapt_native_ranking,
    assert_ada_rca_frozen_unchanged,
    assert_firewall_safe_record,
)
from src.baseline_eval.confirmatory import (
    DATASET_DISPLAY,
    DATASET_ORDER,
    INPUT_MANIFEST_RELATIVE,
    PROTOCOL_ARTIFACT_DIGESTS,
    RCAEVAL_COMMIT,
    RCAEVAL_SOURCE_DIGESTS,
    atomic_write_json,
    expected_case_ids,
    git,
    require_committed_file,
    read_json,
    read_jsonl,
    record_path,
    sha256_bytes,
    sha256_file,
    utc_now,
    verify_method_lock,
    verify_protocol_artifacts,
    verify_rcaeval_clean,
)
from src.baseline_eval.evaluation_v2 import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    FAULTS,
    FROZEN_ADA_METRIC_SHA256,
    FROZEN_ADA_METRICS,
    FROZEN_ADA_PROVENANCE_SHA256,
    _bootstrap_delta,
    _frozen_ada_case_rows,
)
from src.baseline_eval.rescue_v2 import (
    V2_COMBINED_METHODS,
    verify_v2_combined_global_prediction_lock,
)


FINAL_COMPARISON_ROOT_RELATIVE = Path("artifacts/baseline_eval/final_comparison_v3")
SCOPE_LOCK_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "scope_lock_v3.json"
AMENDMENT_RELATIVE = Path(
    "docs/baseline_eval/RCA_BASELINE_BARO_FINAL_INTEGRATION_AMENDMENT_V1.md"
)
AMENDMENT_MACHINE_RELATIVE = Path(
    "artifacts/baseline_eval/baro_final_integration_amendment_v1.json"
)
BARO_LOCK_RELATIVE = Path(
    "artifacts/baseline_eval/execution_v1/locks/baro_prediction_lock.json"
)
BARO_ENVIRONMENT_RELATIVE = Path(
    "artifacts/baseline_eval/execution_v1/environments/baro.json"
)
SIX_METHOD_LOCK_RELATIVE = Path(
    "artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json"
)
V2_EVALUATION_ROOT_RELATIVE = Path(
    "artifacts/baseline_eval/execution_v2/evaluation_causalrca"
)
FINAL_REPORT_RELATIVE = Path(
    "docs/baseline_eval/RCA_BASELINE_FINAL_COMPARISON_V3.md"
)

OVERALL_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "overall_v3.json"
FAULT_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "fault_level_v3.json"
ROBUSTNESS_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "robustness_v3.json"
COMPARABILITY_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "comparability_v3.json"
BOOTSTRAP_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "paired_bootstrap_v3.json"
PROVENANCE_RELATIVE = FINAL_COMPARISON_ROOT_RELATIVE / "provenance_v3.json"
FINAL_OUTPUT_RELATIVES = (
    PROVENANCE_RELATIVE,
    OVERALL_RELATIVE,
    FAULT_RELATIVE,
    ROBUSTNESS_RELATIVE,
    COMPARABILITY_RELATIVE,
    BOOTSTRAP_RELATIVE,
)

SCOPE_CREATION_HEAD = "a0aebe29f7e568b6aa523fb259f2bbd62002a57c"
SCOPE_FREEZE_COMMIT = "bf6349e342fa2e1ffbb1348bccbf852821503bec"
AMENDMENT_MACHINE_SHA256 = "581d9701fefd26427893e4995c1f657988c702acb2770a4b08cc618783a3b97d"
V2_EVALUATION_COMMIT = "8da9b44a495b83d4c6ecdfc3b4e919a0734490bb"
BARO_LOCK_COMMIT = "fbfb6e6e1f112f93fe544f8b6c71aca4f5b336f7"
SIX_METHOD_LOCK_COMMIT = "2778c64f137601f307e21e735e2ad23a3e14eda6"
BARO_EXECUTION_COMMIT = "5018f5d721b4323c5e9fb112d8479c6408a41cd6"

FROZEN_V2_EVALUATION_SHA256 = {
    "overall": "6d782df0878ca1790085da6f9bbd5570ee11ba74ce2bcd26a263225f37631aad",
    "fault_level": "13f74e2fba61a69e3c0e652a2e93fa980daa005c5f90a624300a48716ac36c6f",
    "robustness": "ca499f6e9a79fc4a3963b00c0ef0c85596b8fbaab4919bbef2cebef5f01ea605",
    "comparability": "ac56c630d4ed110d1647051e47c9705bdaa3a1a183e37dc988ed3181598114da",
    "paired_bootstrap": "0591b84f3ef3489c18ac7da92c718456f3d3160c7a42151502f0ea9f0117b8c1",
}

FINAL_BASELINE_METHODS = (
    "BARO",
    "CIRCA",
    "MicroCause",
    "MicroRank",
    "TraceRCA",
    "mmBARO",
    "CausalRCA",
)
FINAL_REPORT_ORDER = (*FINAL_BASELINE_METHODS, "Ada-RCA")
V1_STATUS_VALUES = (
    "SUCCESS",
    "METHOD_FAILURE",
    "ADAPTER_FAILURE",
    "DATA_FAILURE",
    "TIMEOUT",
)
EVIDENCE_TRACKS = {
    "BARO": "V1_LOCKED_COMPLETE",
    "CIRCA": "V2_RESCUE_LOCKED",
    "MicroCause": "V2_RESCUE_LOCKED",
    "MicroRank": "V2_RESCUE_LOCKED",
    "TraceRCA": "V2_RESCUE_LOCKED",
    "mmBARO": "V2_RESCUE_LOCKED",
    "CausalRCA": "V2_CPU_EXTENSION_LOCKED",
    "Ada-RCA": "FROZEN_ADA_SCIENTIFIC_V1",
}
V2_EVALUATION_RELATIVES = {
    "overall": V2_EVALUATION_ROOT_RELATIVE / "overall_v2.json",
    "fault_level": V2_EVALUATION_ROOT_RELATIVE / "fault_level_v2.json",
    "robustness": V2_EVALUATION_ROOT_RELATIVE / "robustness_v2.json",
    "comparability": V2_EVALUATION_ROOT_RELATIVE / "comparability_v2.json",
    "paired_bootstrap": V2_EVALUATION_ROOT_RELATIVE / "paired_bootstrap_v2.json",
}


class FinalComparisonBlocked(RuntimeError):
    """The frozen composite comparison cannot proceed safely."""


def _commit_for_path(root: Path, relative: Path) -> str:
    result = git(
        root,
        "log",
        "-1",
        "--format=%H",
        "--",
        relative.as_posix(),
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _require_committed(root: Path, relative: Path) -> None:
    try:
        require_committed_file(root, relative)
    except Exception as exc:  # noqa: BLE001 - normalize all gate failures
        raise FinalComparisonBlocked(
            f"required committed artifact is unavailable or mutable: {relative.as_posix()}"
        ) from exc


def _assert_file_digest(path: Path, expected_sha256: str, description: str) -> None:
    """Bind a file to an explicitly recorded digest and fail closed on drift."""

    if not path.is_file():
        raise FinalComparisonBlocked(f"bound artifact is missing: {description}")
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise FinalComparisonBlocked(f"bound artifact digest mismatch: {description}")


def _assert_bound_file(
    root: Path,
    relative: Path,
    expected_sha256: str,
    *,
    expected_commit: str | None = None,
) -> None:
    _require_committed(root, relative)
    _assert_file_digest(root / relative, expected_sha256, relative.as_posix())
    if expected_commit is not None:
        observed_commit = _commit_for_path(root, relative)
        if observed_commit != expected_commit:
            raise FinalComparisonBlocked(
                f"bound artifact commit mismatch: {relative.as_posix()}"
            )


def _load_scope_lock(root: Path) -> dict[str, Any]:
    """Require the committed scope lock before any BARO label join."""

    _require_committed(root, SCOPE_LOCK_RELATIVE)
    scope = read_json(root / SCOPE_LOCK_RELATIVE)
    if scope.get("schema_version") != "rca_baseline_final_composite_scope_lock_v3":
        raise FinalComparisonBlocked("final comparison scope lock schema is invalid")
    try:
        assert_firewall_safe_record(scope)
    except Exception as exc:  # noqa: BLE001
        raise FinalComparisonBlocked("scope lock violates the performance firewall") from exc
    if scope.get("created_from_head") != SCOPE_CREATION_HEAD:
        raise FinalComparisonBlocked("scope lock was not created from the recorded Starting HEAD")
    if scope.get("status") != "SCOPE_FROZEN_BEFORE_BARO_METRIC_EVALUATION":
        raise FinalComparisonBlocked("scope lock is not a pre-BARO-evaluation freeze")
    if scope.get("baseline_method_order") != list(FINAL_BASELINE_METHODS):
        raise FinalComparisonBlocked("scope lock baseline method order is invalid")
    if scope.get("final_report_order") != list(FINAL_REPORT_ORDER):
        raise FinalComparisonBlocked("scope lock final report order is invalid")
    if scope.get("datasets") != {
        "order": list(DATASET_ORDER),
        "case_counts": {"re2ob": 90, "re2tt": 90},
        "pooling": "FORBIDDEN",
    }:
        raise FinalComparisonBlocked("scope lock dataset universe is invalid")
    decision = scope.get("decision", {})
    if decision.get("type") != "SCOPE_COMPLETENESS":
        raise FinalComparisonBlocked("BARO inclusion is not frozen as scope completeness")
    if decision.get("performance_independent") is not True:
        raise FinalComparisonBlocked("BARO scope decision is not performance-independent")
    if decision.get("baro_metrics_inspected_before_scope_freeze") is not False:
        raise FinalComparisonBlocked("scope lock records pre-freeze BARO metric inspection")
    prohibitions = scope.get("prohibitions", {})
    for key in (
        "baro_prediction_rerun",
        "existing_six_method_rerun",
        "ada_rca_retraining",
        "algorithm_change",
        "adapter_search",
        "candidate_completion",
        "dataset_pooling",
    ):
        if prohibitions.get(key) is not True:
            raise FinalComparisonBlocked(f"scope lock does not prohibit {key}")
    if scope.get("seven_method_original_global_prelabel_lock") is not False:
        raise FinalComparisonBlocked("scope lock mislabels the seven-method chronology")

    amendment = scope.get("integration_amendment", {})
    if amendment.get("path") != AMENDMENT_RELATIVE.as_posix():
        raise FinalComparisonBlocked("scope lock amendment path is invalid")
    if amendment.get("commit_required") is not True:
        raise FinalComparisonBlocked("scope lock does not require a committed amendment")
    _assert_bound_file(root, AMENDMENT_RELATIVE, amendment.get("sha256", ""))
    if _commit_for_path(root, AMENDMENT_RELATIVE) != SCOPE_FREEZE_COMMIT:
        raise FinalComparisonBlocked("integration amendment is not in the scope-freeze commit")
    _assert_bound_file(
        root,
        AMENDMENT_MACHINE_RELATIVE,
        AMENDMENT_MACHINE_SHA256,
        expected_commit=SCOPE_FREEZE_COMMIT,
    )
    amendment_machine = read_json(root / AMENDMENT_MACHINE_RELATIVE)
    if (
        amendment_machine.get("schema_version")
        != "rca_baseline_baro_final_integration_amendment_v1"
        or amendment_machine.get("rationale") != "scope completeness"
        or amendment_machine.get("baro_rerun") is not False
        or amendment_machine.get("six_baseline_rerun") is not False
        or amendment_machine.get("ada_rca_retraining") is not False
        or amendment_machine.get("baro_metrics_inspected_before_scope_freeze") is not False
        or amendment_machine.get("six_method_metrics_preexisting") is not True
        or amendment_machine.get("seven_method_original_global_prelabel_lock") is not False
    ):
        raise FinalComparisonBlocked("machine-readable BARO integration amendment is invalid")

    input_binding = scope.get("input_manifest", {})
    if input_binding.get("path") != INPUT_MANIFEST_RELATIVE.as_posix():
        raise FinalComparisonBlocked("scope lock input-manifest path is invalid")
    _assert_bound_file(root, INPUT_MANIFEST_RELATIVE, input_binding.get("sha256", ""))

    if scope.get("rcaeval", {}).get("commit") != RCAEVAL_COMMIT:
        raise FinalComparisonBlocked("scope lock RCAEval commit is invalid")
    if scope.get("frozen_ada_rca_identity", {}).get("scientific_v1_reference") != (
        "bed295326e567395e725caa82840a534dcc0b1de"
    ):
        raise FinalComparisonBlocked("scope lock Ada-RCA scientific identity is invalid")
    return scope


def _manifest_sources(root: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    payload = read_json(root / INPUT_MANIFEST_RELATIVE)
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise FinalComparisonBlocked("input manifest case rows are invalid")
    result = {}
    for row in rows:
        key = (row.get("dataset"), row.get("case_id"))
        result[key] = row.get("sources")
    if len(result) != 180 or any(not isinstance(value, list) for value in result.values()):
        raise FinalComparisonBlocked("input manifest does not cover 180 source bundles")
    return result


def verify_baro_v1_lock(root: Path, scope: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Verify BARO's frozen V1 lock and records without joining labels."""

    if scope is None:
        scope = _load_scope_lock(root)
    binding = scope.get("baro_v1_prediction_lock", {})
    if binding.get("path") != BARO_LOCK_RELATIVE.as_posix():
        raise FinalComparisonBlocked("scope lock BARO lock path is invalid")
    _assert_bound_file(
        root,
        BARO_LOCK_RELATIVE,
        binding.get("sha256", ""),
        expected_commit=binding.get("commit"),
    )
    if binding.get("commit") != BARO_LOCK_COMMIT:
        raise FinalComparisonBlocked("scope lock BARO lock commit is invalid")
    lock = verify_method_lock(root, "BARO", require_committed=True)
    if lock.get("method") != "BARO" or lock.get("disposition") != "EXECUTION_COMPLETE":
        raise FinalComparisonBlocked("BARO V1 lock is not execution-complete")
    if lock.get("contains_evaluation") is not False:
        raise FinalComparisonBlocked("BARO V1 lock contains evaluation")
    expected_counts = {dataset: 90 for dataset in DATASET_ORDER}
    if lock.get("record_counts") != expected_counts:
        raise FinalComparisonBlocked("BARO V1 record denominators are not 90+90")
    expected_status_counts = {
        dataset: {status: (90 if status == "SUCCESS" else 0) for status in V1_STATUS_VALUES}
        for dataset in DATASET_ORDER
    }
    if lock.get("status_counts") != expected_status_counts:
        raise FinalComparisonBlocked("BARO V1 status counts are not 90 SUCCESS per dataset")

    _require_committed(root, BARO_ENVIRONMENT_RELATIVE)
    environment = read_json(root / BARO_ENVIRONMENT_RELATIVE)
    if lock.get("environment_digest") != environment.get("environment_digest"):
        raise FinalComparisonBlocked("BARO lock and environment digest differ")
    if lock.get("input_manifest_digest") != sha256_file(root / INPUT_MANIFEST_RELATIVE):
        raise FinalComparisonBlocked("BARO lock input-manifest digest differs")
    if lock.get("rcaeval_commit") != RCAEVAL_COMMIT:
        raise FinalComparisonBlocked("BARO lock RCAEval commit differs")

    protocol = read_json(root / "artifacts/baseline_eval/protocol_freeze_v1.json")
    candidate_registry_digests: dict[str, str] = {}
    for dataset in DATASET_ORDER:
        registry_relative = Path(protocol["datasets"][dataset]["candidate_registry"])
        observed = sha256_file(root / registry_relative)
        expected = protocol["datasets"][dataset]["candidate_registry_sha256"]
        if observed != expected:
            raise FinalComparisonBlocked(f"{dataset} candidate registry digest changed")
        candidate_registry_digests[dataset] = observed

    manifest_sources = _manifest_sources(root)
    records: dict[str, list[dict[str, Any]]] = {dataset: [] for dataset in DATASET_ORDER}
    digest_rows = lock.get("terminal_record_digests")
    if not isinstance(digest_rows, list) or len(digest_rows) != 180:
        raise FinalComparisonBlocked("BARO lock does not bind 180 record digests")
    bound_digests: dict[tuple[str, str], str] = {}
    for item in digest_rows:
        key = (item.get("dataset"), item.get("case_id"))
        if key in bound_digests or not isinstance(item.get("sha256"), str):
            raise FinalComparisonBlocked("BARO lock has duplicate or malformed record digest")
        bound_digests[key] = item["sha256"]

    execution_commits: set[str] = set()
    source_digest = RCAEVAL_SOURCE_DIGESTS["RCAEval/e2e/baro.py"]
    for dataset in DATASET_ORDER:
        expected_ids = expected_case_ids(root, dataset)
        if lock.get("expected_case_ids", {}).get(dataset) != list(expected_ids):
            raise FinalComparisonBlocked(f"BARO lock case order differs for {dataset}")
        for case_id in expected_ids:
            key = (dataset, case_id)
            path = record_path(root, "BARO", lock["attempt_id"], dataset, case_id)
            expected_digest = bound_digests.get(key)
            if expected_digest is None:
                raise FinalComparisonBlocked(
                    f"BARO record digest binding is missing for {dataset} {case_id}"
                )
            _assert_file_digest(path, expected_digest, f"BARO record {dataset} {case_id}")
            row = read_json(path)
            if row.get("method_source_digest") != source_digest:
                raise FinalComparisonBlocked("BARO record source digest differs")
            if row.get("environment_digest") != lock["environment_digest"]:
                raise FinalComparisonBlocked("BARO record environment digest differs")
            if row.get("input_manifest_digest") != lock["input_manifest_digest"]:
                raise FinalComparisonBlocked("BARO record input-manifest digest differs")
            consumed_sources = [
                source
                for source in manifest_sources[key]
                if source.get("logical_source_role") in {"inject_time", "simple_metrics"}
            ]
            if row.get("source_record_digests") != consumed_sources:
                raise FinalComparisonBlocked("BARO record source provenance differs")
            if row.get("candidate_registry_digest") != candidate_registry_digests[dataset]:
                raise FinalComparisonBlocked("BARO record candidate registry digest differs")
            if row.get("terminal_status") != "SUCCESS":
                raise FinalComparisonBlocked("BARO lock status and record status differ")
            projected = adapt_native_ranking(
                row.get("native_ranking", []),
                json.loads((root / protocol["datasets"][dataset]["candidate_registry"]).read_text())[
                    "services"
                ],
            )
            if list(projected.services) != row.get("adapted_ranking"):
                raise FinalComparisonBlocked("BARO adapted service projection differs")
            if list(projected.duplicates) != row.get("duplicate_native_items"):
                raise FinalComparisonBlocked("BARO duplicate projection differs")
            if list(projected.unmapped) != row.get("unmapped_native_items"):
                raise FinalComparisonBlocked("BARO unmapped projection differs")
            execution_commit = row.get("execution_commit")
            if not isinstance(execution_commit, str):
                raise FinalComparisonBlocked("BARO execution commit is missing")
            execution_commits.add(execution_commit)
            records[dataset].append(row)
    if execution_commits != {BARO_EXECUTION_COMMIT}:
        raise FinalComparisonBlocked("BARO records do not share the frozen execution commit")
    return {
        "lock": lock,
        "lock_sha256": sha256_file(root / BARO_LOCK_RELATIVE),
        "lock_commit": _commit_for_path(root, BARO_LOCK_RELATIVE),
        "environment_manifest_sha256": sha256_file(root / BARO_ENVIRONMENT_RELATIVE),
        "environment_digest": lock["environment_digest"],
        "candidate_registry_digests": candidate_registry_digests,
        "records": records,
        "execution_commit": next(iter(execution_commits)),
    }


def verify_six_method_v2_lock(
    root: Path, scope: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Verify the inherited six-method V2 combined prediction lock."""

    if scope is None:
        scope = _load_scope_lock(root)
    binding = scope.get("six_method_v2_combined_prediction_lock", {})
    if binding.get("path") != SIX_METHOD_LOCK_RELATIVE.as_posix():
        raise FinalComparisonBlocked("scope lock six-method lock path is invalid")
    if binding.get("commit") != SIX_METHOD_LOCK_COMMIT:
        raise FinalComparisonBlocked("scope lock six-method lock commit is invalid")
    _assert_bound_file(
        root,
        SIX_METHOD_LOCK_RELATIVE,
        binding.get("sha256", ""),
        expected_commit=SIX_METHOD_LOCK_COMMIT,
    )
    try:
        lock = verify_v2_combined_global_prediction_lock(root, require_committed=True)
    except Exception as exc:  # noqa: BLE001 - normalize the inherited-lock gate
        raise FinalComparisonBlocked("six-method V2 combined lock verification failed") from exc
    if lock.get("method_order") != list(V2_COMBINED_METHODS):
        raise FinalComparisonBlocked("six-method V2 combined lock method order is invalid")
    if lock.get("labels_joined") is not False or lock.get("contains_evaluation") is not False:
        raise FinalComparisonBlocked("six-method V2 combined lock is not pre-evaluation")
    return {
        "lock": lock,
        "lock_sha256": sha256_file(root / SIX_METHOD_LOCK_RELATIVE),
        "lock_commit": _commit_for_path(root, SIX_METHOD_LOCK_RELATIVE),
    }


def _load_labels_after_scope(
    root: Path,
) -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, Any]]:
    protocol = read_json(root / "artifacts/baseline_eval/protocol_freeze_v1.json")
    labels: dict[str, dict[str, dict[str, str]]] = {}
    metadata: dict[str, Any] = {}
    for dataset in DATASET_ORDER:
        path = root / "artifacts/source" / dataset / "labels.jsonl"
        rows = read_jsonl(path)
        expected_ids = expected_case_ids(root, dataset)
        mapping: dict[str, dict[str, str]] = {}
        for row in rows:
            case_id = row.get("case_id")
            if case_id in mapping:
                raise FinalComparisonBlocked(f"duplicate frozen label case for {dataset}")
            mapping[case_id] = {
                "root_service": row.get("root_service"),
                "fault_type": str(row.get("fault_type", "")).lower(),
            }
        if tuple(mapping) != expected_ids:
            raise FinalComparisonBlocked(f"frozen label case universe differs for {dataset}")
        expected_sha = protocol["datasets"][dataset]["root_mapping_sha256"]
        observed_sha = sha256_file(path)
        if observed_sha != expected_sha:
            raise FinalComparisonBlocked(f"frozen label mapping digest changed for {dataset}")
        registry = json.loads(
            (root / protocol["datasets"][dataset]["candidate_registry"]).read_text()
        )["services"]
        if any(row["root_service"] not in registry for row in mapping.values()):
            raise FinalComparisonBlocked(f"frozen root mapping leaves candidate universe for {dataset}")
        fault_counts = Counter(row["fault_type"] for row in mapping.values())
        if set(fault_counts) != set(FAULTS):
            raise FinalComparisonBlocked(f"frozen fault taxonomy differs for {dataset}")
        labels[dataset] = mapping
        metadata[dataset] = {
            "path": str(path.relative_to(root)),
            "sha256": observed_sha,
            "case_count": len(mapping),
            "fault_case_counts": dict(sorted(fault_counts.items())),
        }
    return labels, metadata


def _load_frozen_v2_evidence(root: Path) -> dict[str, Any]:
    paths = {}
    payloads = {}
    for name, relative in V2_EVALUATION_RELATIVES.items():
        _assert_bound_file(
            root,
            relative,
            FROZEN_V2_EVALUATION_SHA256[name],
            expected_commit=V2_EVALUATION_COMMIT,
        )
        paths[name] = relative
        payloads[name] = read_json(root / relative)

    overall = payloads["overall"]
    if tuple(overall.get("method_scope", ())) != V2_COMBINED_METHODS:
        raise FinalComparisonBlocked("frozen V2 overall scope is not the six-method scope")
    overall_rows = overall.get("table_a", {}).get("rows", [])
    overall_by_method = {row.get("Method"): row for row in overall_rows}
    expected_old_methods = (*V2_COMBINED_METHODS, "Ada-RCA")
    if tuple(row.get("Method") for row in overall_rows) != expected_old_methods:
        raise FinalComparisonBlocked("frozen V2 overall method order changed")
    if set(overall.get("method_dataset_metrics", {})) != {
        f"{method}__{dataset}"
        for method in expected_old_methods
        for dataset in DATASET_ORDER
    }:
        raise FinalComparisonBlocked("frozen V2 method-dataset metric keys changed")
    for dataset in DATASET_ORDER:
        metrics = overall["method_dataset_metrics"][f"Ada-RCA__{dataset}"]
        for metric, expected in FROZEN_ADA_METRICS[dataset].items():
            if metrics.get(metric) != expected:
                raise FinalComparisonBlocked(f"frozen Ada-RCA V2 metric changed: {dataset} {metric}")
        row = overall_by_method["Ada-RCA"]
        display = "OB" if dataset == "re2ob" else "TT"
        for metric in ("AC@1", "AC@3", "AC@5", "Avg@5"):
            if row[f"{display} {metric}"] != metrics[metric]:
                raise FinalComparisonBlocked("frozen V2 Ada-RCA table and metric payload differ")

    fault_rows = payloads["fault_level"].get("rows", [])
    fault_index = {
        (row.get("method"), row.get("dataset"), row.get("fault")): row
        for row in fault_rows
    }
    expected_fault_keys = {
        (method, dataset, fault.upper())
        for method in expected_old_methods
        for dataset in DATASET_ORDER
        for fault in FAULTS
    }
    if set(fault_index) != expected_fault_keys:
        raise FinalComparisonBlocked("frozen V2 fault-level key universe changed")

    robustness = payloads["robustness"].get("table_c", {})
    robustness_rows = robustness.get("rows", [])
    robustness_index = {(row.get("method"), row.get("dataset")): row for row in robustness_rows}
    if set(robustness_index) != {
        (method, dataset) for method in V2_COMBINED_METHODS for dataset in DATASET_ORDER
    }:
        raise FinalComparisonBlocked("frozen V2 robustness key universe changed")

    comparability_rows = payloads["comparability"].get("table_d", {}).get("rows", [])
    comparability_index = {row.get("method"): row for row in comparability_rows}
    if tuple(row.get("method") for row in comparability_rows) != expected_old_methods:
        raise FinalComparisonBlocked("frozen V2 comparability order changed")

    bootstrap = payloads["paired_bootstrap"]
    bootstrap_rows = bootstrap.get("rows", [])
    bootstrap_index = {(row.get("method"), row.get("dataset")): row for row in bootstrap_rows}
    if set(bootstrap_index) != {
        (method, dataset) for method in V2_COMBINED_METHODS for dataset in DATASET_ORDER
    }:
        raise FinalComparisonBlocked("frozen V2 bootstrap key universe changed")
    if bootstrap.get("resamples") != BOOTSTRAP_RESAMPLES or bootstrap.get("seed") != BOOTSTRAP_SEED:
        raise FinalComparisonBlocked("frozen V2 bootstrap design changed")

    return {
        "paths": paths,
        "payloads": payloads,
        "overall_by_method": overall_by_method,
        "fault_index": fault_index,
        "robustness_columns": robustness.get("columns", []),
        "robustness_index": robustness_index,
        "comparability_index": comparability_index,
        "bootstrap_index": bootstrap_index,
    }


def _aggregate_case_rows(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(case_rows) != 90:
        raise FinalComparisonBlocked("BARO metric denominator is not exactly 90")
    values = {
        f"AC@{k}": sum(int(row[f"AC@{k}"]) for row in case_rows) / 90
        for k in range(1, 6)
    }
    values["Avg@5"] = sum(values[f"AC@{k}"] for k in range(1, 6)) / 5
    status_counts = {
        status: sum(1 for row in case_rows if row["terminal_status"] == status)
        for status in V1_STATUS_VALUES
    }
    return {
        **values,
        "MRR": "NOT-IDENTIFIABLE",
        "MRR_legality": "NOT-IDENTIFIABLE",
        "cases": 90,
        "status_counts": status_counts,
        "success_cases": status_counts["SUCCESS"],
        "robustness_zero_method_failures": status_counts["METHOD_FAILURE"],
    }


def _baro_case_rows(
    records: Sequence[Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, str]],
    expected_ids: Sequence[str],
) -> list[dict[str, Any]]:
    by_case = {row.get("case_id"): row for row in records}
    if tuple(by_case) != tuple(expected_ids):
        raise FinalComparisonBlocked("BARO records cannot be aligned to frozen case order")
    output = []
    for case_id in expected_ids:
        record = by_case[case_id]
        status = record["terminal_status"]
        if status == "METHOD_FAILURE":
            hits = (0, 0, 0, 0, 0)
        elif status == "SUCCESS":
            ranking = record.get("adapted_ranking", [])
            target = labels[case_id]["root_service"]
            hits = tuple(int(target in ranking[:k]) for k in range(1, 6))
        else:
            raise FinalComparisonBlocked(f"BARO status {status} cannot enter final evaluation")
        output.append({
            "case_id": case_id,
            "fault_type": labels[case_id]["fault_type"],
            "terminal_status": status,
            **{f"AC@{k}": hits[k - 1] for k in range(1, 6)},
            "Avg@5": sum(hits) / 5,
        })
    return output


def _fault_rows(
    method: str,
    dataset: str,
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for fault in FAULTS:
        selected = [row for row in case_rows if row["fault_type"] == fault]
        if not selected:
            result.append({
                "method": method,
                "dataset": dataset,
                "fault": fault.upper(),
                "cases": 0,
                "AC@1": "N/A",
                "AC@3": "N/A",
                "AC@5": "N/A",
                "Avg@5": "N/A",
            })
            continue
        result.append({
            "method": method,
            "dataset": dataset,
            "fault": fault.upper(),
            "cases": len(selected),
            **{
                f"AC@{k}": sum(float(row[f"AC@{k}"]) for row in selected) / len(selected)
                for k in (1, 3, 5)
            },
            "Avg@5": sum(float(row["Avg@5"]) for row in selected) / len(selected),
        })
    return result


def _baro_comparability_row() -> dict[str, Any]:
    return {
        "method": "BARO",
        "input": "metric",
        "supervision": "case-wise unsupervised",
        "native_granularity": "indicator",
        "service_projection": "partial service projection",
        "complete_service_ranking": "NO",
        "MRR_legality": "NOT-IDENTIFIABLE",
        "evidence_track": EVIDENCE_TRACKS["BARO"],
    }


def _make_provenance(
    root: Path,
    scope: Mapping[str, Any],
    baro_audit: Mapping[str, Any],
    v2: Mapping[str, Any],
    label_metadata: Mapping[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    scope_sha = sha256_file(root / SCOPE_LOCK_RELATIVE)
    amendment_sha = sha256_file(root / AMENDMENT_RELATIVE)
    code_relative = Path("src/baseline_eval/final_comparison.py")
    code_commit = _commit_for_path(root, code_relative)
    if not code_commit:
        raise FinalComparisonBlocked("final comparison code must be committed before evaluation")
    return {
        "schema_version": "rca_baseline_final_composite_provenance_v3",
        "generated_at": generated_at,
        "scope": {
            "id": scope["scope_id"],
            "path": SCOPE_LOCK_RELATIVE.as_posix(),
            "sha256": scope_sha,
            "commit": _commit_for_path(root, SCOPE_LOCK_RELATIVE),
            "freeze_commit": SCOPE_FREEZE_COMMIT,
            "baro_metrics_inspected_before_scope_freeze": False,
        },
        "integration_amendment": {
            "path": AMENDMENT_RELATIVE.as_posix(),
            "sha256": amendment_sha,
            "commit": _commit_for_path(root, AMENDMENT_RELATIVE),
            "machine_readable_path": AMENDMENT_MACHINE_RELATIVE.as_posix(),
        },
        "baro_v1_evidence": {
            "method": "BARO",
            "evidence_track": EVIDENCE_TRACKS["BARO"],
            "prediction_lock_path": BARO_LOCK_RELATIVE.as_posix(),
            "prediction_lock_sha256": baro_audit["lock_sha256"],
            "prediction_lock_commit": baro_audit["lock_commit"],
            "attempt_id": baro_audit["lock"]["attempt_id"],
            "execution_commit": baro_audit["execution_commit"],
            "environment_manifest_path": BARO_ENVIRONMENT_RELATIVE.as_posix(),
            "environment_manifest_sha256": baro_audit["environment_manifest_sha256"],
            "environment_digest": baro_audit["environment_digest"],
            "lock_environment_digest_identity": "PASS",
            "record_counts": {dataset: 90 for dataset in DATASET_ORDER},
            "status_counts": baro_audit["lock"]["status_counts"],
            "evaluation_source": "frozen V1 case records after committed V3 scope lock",
            "rerun": False,
            "live_environment_re_resolution": "NOT_REQUIRED_FOR_INHERITED_FROZEN_EVIDENCE",
        },
        "six_method_v2_evidence": {
            "evidence_track": "V2_COMBINED_LOCKED",
            "prediction_lock_path": SIX_METHOD_LOCK_RELATIVE.as_posix(),
            "prediction_lock_sha256": sha256_file(root / SIX_METHOD_LOCK_RELATIVE),
            "prediction_lock_commit": SIX_METHOD_LOCK_COMMIT,
            "evaluation_source_paths": {
                name: {
                    "path": relative.as_posix(),
                    "sha256": sha256_file(root / relative),
                    "commit": V2_EVALUATION_COMMIT,
                }
                for name, relative in v2["paths"].items()
            },
            "metrics_preexisting": True,
            "rerun": False,
            "byte_identity_checked": True,
        },
        "input_manifest": {
            "path": INPUT_MANIFEST_RELATIVE.as_posix(),
            "sha256": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        },
        "labels_after_scope": label_metadata,
        "candidate_registry_digests": baro_audit["candidate_registry_digests"],
        "adapter_contract": {
            "protocol_artifacts": {
                path: sha256_file(root / path)
                for path in sorted(PROTOCOL_ARTIFACT_DIGESTS)
                if "ADAPTER_SPEC" in path or "PROTOCOL_FREEZE" in path
            },
            "implementation": "src/baseline_eval/__init__.py::adapt_native_ranking",
            "implementation_sha256": sha256_file(root / "src/baseline_eval/__init__.py"),
            "alias_policy": "frontendservice[_...] -> frontend[_...]",
            "projection_policy": "longest legal prefix; first occurrence retained; duplicates and unmapped entries omitted",
            "candidate_completion": "NONE",
            "metric_legality": {
                "AC@1": "ADAPTED-BUT-VALID",
                "AC@3": "ADAPTED-BUT-VALID",
                "AC@5": "ADAPTED-BUT-VALID",
                "Avg@5": "ADAPTED-BUT-VALID",
                "MRR": "NOT-IDENTIFIABLE",
            },
        },
        "rcaeval": {
            "checkout": "/home/zhangll24/RCA_project/RCAEval-clean",
            "commit": RCAEVAL_COMMIT,
            "clean": True,
        },
        "ada_rca_frozen_identity": {
            "scientific_v1_reference": "bed295326e567395e725caa82840a534dcc0b1de",
            "evidence_closure_reference": "9342e06db91945be2e44703437229ba45b18bda8",
            "metrics": {
                dataset: {
                    "path": f"artifacts/final_method/{dataset}/metrics.json",
                    "sha256": FROZEN_ADA_METRIC_SHA256[dataset],
                }
                for dataset in DATASET_ORDER
            },
            "provenance": {
                dataset: {
                    "path": f"artifacts/final_method/{dataset}/provenance.json",
                    "sha256": FROZEN_ADA_PROVENANCE_SHA256[dataset],
                }
                for dataset in DATASET_ORDER
            },
            "retraining": False,
        },
        "method_order": list(FINAL_BASELINE_METHODS),
        "final_report_order": list(FINAL_REPORT_ORDER),
        "evidence_tracks": EVIDENCE_TRACKS,
        "newly_evaluated_methods": ["BARO"],
        "existing_six_method_values_identity_asserted": True,
        "historical_v2_evidence_byte_immutable": True,
        "labels_joined_after_scope_lock": True,
        "pooling": "FORBIDDEN",
        "statistical_design": {
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "stratification": "fault",
            "datasets_separate": True,
            "primary": "Ada-RCA - BARO Avg@5",
            "secondary": "Ada-RCA - BARO AC@1",
        },
        "claim_boundary": {
            "sota_claim": False,
            "same_protocol_superiority_claim": False,
            "causal_superiority_claim": False,
            "unseen_system_generalization_claim": False,
            "unseen_root_generalization_claim": False,
        },
        "final_output_paths": {
            "overall": OVERALL_RELATIVE.as_posix(),
            "fault_level": FAULT_RELATIVE.as_posix(),
            "robustness": ROBUSTNESS_RELATIVE.as_posix(),
            "comparability": COMPARABILITY_RELATIVE.as_posix(),
            "paired_bootstrap": BOOTSTRAP_RELATIVE.as_posix(),
        },
    }


def evaluate_final_comparison(root: Path) -> dict[str, Path]:
    """Evaluate BARO and compose the seven-baseline final evidence layer."""

    scope = _load_scope_lock(root)
    if any((root / relative).exists() for relative in FINAL_OUTPUT_RELATIVES):
        raise FinalComparisonBlocked("final comparison output already exists and is immutable")
    verify_protocol_artifacts(root)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    baro_audit = verify_baro_v1_lock(root, scope)
    verify_six_method_v2_lock(root, scope)
    v2 = _load_frozen_v2_evidence(root)
    labels, label_metadata = _load_labels_after_scope(root)

    baro_case_rows: dict[str, list[dict[str, Any]]] = {}
    baro_metrics: dict[str, dict[str, Any]] = {}
    baro_fault_rows: dict[str, list[dict[str, Any]]] = {}
    ada_case_rows: dict[str, list[dict[str, Any]]] = {}
    for dataset in DATASET_ORDER:
        expected_ids = expected_case_ids(root, dataset)
        baro_case_rows[dataset] = _baro_case_rows(
            baro_audit["records"][dataset], labels[dataset], expected_ids
        )
        baro_metrics[dataset] = _aggregate_case_rows(baro_case_rows[dataset])
        baro_fault_rows[dataset] = _fault_rows("BARO", dataset, baro_case_rows[dataset])
        ada_case_rows[dataset], _ = _frozen_ada_case_rows(root, dataset)
        ada_fault_counts = Counter(row["fault_type"] for row in ada_case_rows[dataset])
        if dict(sorted(ada_fault_counts.items())) != label_metadata[dataset]["fault_case_counts"]:
            raise FinalComparisonBlocked(f"frozen Ada-RCA fault universe differs for {dataset}")
        for method in (*V2_COMBINED_METHODS, "Ada-RCA"):
            for fault in FAULTS:
                old = v2["fault_index"][(method, dataset, fault.upper())]
                if old["cases"] != label_metadata[dataset]["fault_case_counts"][fault]:
                    raise FinalComparisonBlocked(f"frozen V2 fault denominator differs for {dataset} {fault}")

    old_overall_by_method = v2["overall_by_method"]
    overall_rows = []
    for method in FINAL_REPORT_ORDER:
        if method == "BARO":
            row = {"Method": "BARO"}
            for dataset, display in (("re2ob", "OB"), ("re2tt", "TT")):
                for metric in ("AC@1", "AC@3", "AC@5", "Avg@5"):
                    row[f"{display} {metric}"] = baro_metrics[dataset][metric]
        else:
            row = deepcopy(old_overall_by_method[method])
        overall_rows.append(row)
    overall_metrics = {
        f"BARO__{dataset}": baro_metrics[dataset]
        for dataset in DATASET_ORDER
    }
    for method in (*V2_COMBINED_METHODS, "Ada-RCA"):
        for dataset in DATASET_ORDER:
            overall_metrics[f"{method}__{dataset}"] = deepcopy(
                v2["payloads"]["overall"]["method_dataset_metrics"][f"{method}__{dataset}"]
            )

    old_fault_index = v2["fault_index"]
    final_fault_rows = []
    for dataset in DATASET_ORDER:
        baro_by_fault = {
            row["fault"]: row for row in baro_fault_rows[dataset]
        }
        for method in FINAL_REPORT_ORDER:
            for fault in FAULTS:
                key = (method, dataset, fault.upper())
                final_fault_rows.append(
                    deepcopy(baro_by_fault[fault.upper()])
                    if method == "BARO"
                    else deepcopy(old_fault_index[key])
                )

    old_robustness_index = v2["robustness_index"]
    robustness_columns = [
        "Method",
        "Dataset",
        "Evidence track",
        "Cases",
        "SUCCESS",
        "METHOD_FAILURE",
        "DATA_FAILURE",
        "ADAPTER_FAILURE",
        "ENVIRONMENT_FAILURE",
        "INPUT_INTEGRITY_FAILURE",
        "PROCESS_CRASH/OOM",
        "TIMEOUT",
    ]
    robustness_rows = []
    for dataset in DATASET_ORDER:
        for method in FINAL_BASELINE_METHODS:
            if method != "BARO":
                row = deepcopy(old_robustness_index[(method, dataset)])
                row["evidence_track"] = EVIDENCE_TRACKS[method]
                row["status_taxonomy"] = "V2"
            else:
                counts = baro_audit["lock"]["status_counts"][dataset]
                row = {
                    "method": "BARO",
                    "dataset": dataset,
                    "evidence_track": EVIDENCE_TRACKS["BARO"],
                    "status_taxonomy": "V1",
                    "cases": 90,
                    "SUCCESS": counts["SUCCESS"],
                    "METHOD_FAILURE": counts["METHOD_FAILURE"],
                    "DATA_FAILURE": counts["DATA_FAILURE"],
                    "ADAPTER_FAILURE": counts["ADAPTER_FAILURE"],
                    "ENVIRONMENT_FAILURE": "N/A (V1 schema)",
                    "INPUT_INTEGRITY_FAILURE": "N/A (V1 schema)",
                    "PROCESS_CRASH/OOM": "N/A (V1 schema)",
                    "TIMEOUT": counts["TIMEOUT"],
                }
            robustness_rows.append(row)

    old_comparability_index = v2["comparability_index"]
    comparability_columns = [
        "Method",
        "Input",
        "Supervision",
        "Native granularity",
        "Service projection",
        "Complete service ranking",
        "MRR legality",
        "Evidence track",
    ]
    comparability_rows = []
    for method in FINAL_REPORT_ORDER:
        if method == "BARO":
            comparability_rows.append(_baro_comparability_row())
        else:
            row = deepcopy(old_comparability_index[method])
            row["evidence_track"] = EVIDENCE_TRACKS[method]
            comparability_rows.append(row)

    bootstrap_rows = []
    for dataset in DATASET_ORDER:
        for method in FINAL_BASELINE_METHODS:
            if method == "BARO":
                bootstrap_rows.append({
                    "method": "BARO",
                    "dataset": dataset,
                    "primary_delta_avg5": _bootstrap_delta(
                        ada_case_rows[dataset], baro_case_rows[dataset], metric="Avg@5"
                    ),
                    "secondary_delta_ac1": _bootstrap_delta(
                        ada_case_rows[dataset], baro_case_rows[dataset], metric="AC@1"
                    ),
                })
            else:
                bootstrap_rows.append(
                    deepcopy(v2["bootstrap_index"][(method, dataset)])
                )

    generated_at = utc_now()
    provenance = _make_provenance(
        root,
        scope,
        baro_audit,
        v2,
        label_metadata,
        generated_at=generated_at,
    )
    payloads = {
        PROVENANCE_RELATIVE: provenance,
        OVERALL_RELATIVE: {
            "schema_version": "rca_baseline_final_composite_overall_v3",
            "evaluated_at": generated_at,
            "provenance": provenance,
            "table_a": {
                "columns": [
                    "Method",
                    "OB AC@1",
                    "OB AC@3",
                    "OB AC@5",
                    "OB Avg@5",
                    "TT AC@1",
                    "TT AC@3",
                    "TT AC@5",
                    "TT Avg@5",
                ],
                "rows": overall_rows,
                "pooling": "FORBIDDEN; RE2-OB and RE2-TT remain separate",
            },
            "method_dataset_metrics": overall_metrics,
            "baseline_mrr": "NOT-IDENTIFIABLE",
            "labels_joined_after_scope_lock": True,
            "new_metric_evaluation": ["BARO"],
            "existing_six_method_values_identity_asserted": True,
        },
        FAULT_RELATIVE: {
            "schema_version": "rca_baseline_final_composite_fault_level_v3",
            "provenance": provenance,
            "faults": list(FAULTS),
            "rows": final_fault_rows,
            "absent_fault_policy": "N/A",
        },
        ROBUSTNESS_RELATIVE: {
            "schema_version": "rca_baseline_final_composite_robustness_v3",
            "provenance": provenance,
            "table_c": {
                "columns": robustness_columns,
                "rows": robustness_rows,
                "status_taxonomy_note": "N/A (V1 schema) means the status was not recorded by V1 and is not a zero.",
            },
        },
        COMPARABILITY_RELATIVE: {
            "schema_version": "rca_baseline_final_composite_comparability_v3",
            "provenance": provenance,
            "table_d": {
                "columns": comparability_columns,
                "rows": comparability_rows,
            },
        },
        BOOTSTRAP_RELATIVE: {
            "schema_version": "rca_baseline_final_composite_paired_fault_stratified_bootstrap_v3",
            "provenance": provenance,
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "datasets_separate": True,
            "rows": bootstrap_rows,
            "new_metric_rows": ["BARO"],
            "existing_six_method_rows_identity_asserted": True,
        },
    }
    for relative, payload in payloads.items():
        atomic_write_json(root / relative, payload)
    return {relative.stem: root / relative for relative in FINAL_OUTPUT_RELATIVES}


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.10f}"
    return str(value)


def _markdown_table(columns: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    def value_for(row: Mapping[str, Any], column: str) -> Any:
        if column in row:
            return row[column]
        normalized = column.lower().replace(" ", "_")
        if normalized in row:
            return row[normalized]
        for key, value in row.items():
            if str(key).lower().replace(" ", "_") == normalized:
                return value
        return "N/A"

    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    lines.extend(
        "| " + " | ".join(_fmt(value_for(row, column)) for column in columns) + " |"
        for row in rows
    )
    return "\n".join(lines)


def validate_final_outputs(root: Path, *, require_committed: bool = False) -> dict[str, Any]:
    """Validate the final layer and exact identity of all inherited V2 rows."""

    scope = _load_scope_lock(root)
    if require_committed:
        for relative in FINAL_OUTPUT_RELATIVES:
            _require_committed(root, relative)
    missing = [relative.as_posix() for relative in FINAL_OUTPUT_RELATIVES if not (root / relative).is_file()]
    if missing:
        raise FinalComparisonBlocked("final comparison outputs are incomplete: " + ", ".join(missing))
    baro_audit = verify_baro_v1_lock(root, scope)
    verify_six_method_v2_lock(root, scope)
    v2 = _load_frozen_v2_evidence(root)
    labels, label_metadata = _load_labels_after_scope(root)
    final = {relative.stem.removesuffix("_v3"): read_json(root / relative) for relative in FINAL_OUTPUT_RELATIVES}
    overall = final["overall"]
    if [row.get("Method") for row in overall["table_a"]["rows"]] != list(FINAL_REPORT_ORDER):
        raise FinalComparisonBlocked("final overall table does not contain the exact eight-row order")
    old_overall_rows = v2["overall_by_method"]
    final_overall_by_method = {row["Method"]: row for row in overall["table_a"]["rows"]}
    for method in (*V2_COMBINED_METHODS, "Ada-RCA"):
        if final_overall_by_method[method] != old_overall_rows[method]:
            raise FinalComparisonBlocked(f"final overall row changed frozen V2 identity: {method}")
        for dataset in DATASET_ORDER:
            key = f"{method}__{dataset}"
            if overall["method_dataset_metrics"][key] != v2["payloads"]["overall"]["method_dataset_metrics"][key]:
                raise FinalComparisonBlocked(f"final metric payload changed frozen V2 identity: {key}")
    for dataset in DATASET_ORDER:
        baro = overall["method_dataset_metrics"][f"BARO__{dataset}"]
        if baro.get("MRR") != "NOT-IDENTIFIABLE" or baro.get("MRR_legality") != "NOT-IDENTIFIABLE":
            raise FinalComparisonBlocked("BARO MRR was made identifiable")
        baro_case_rows = _baro_case_rows(
            baro_audit["records"][dataset],
            labels[dataset],
            expected_case_ids(root, dataset),
        )
        rebuilt_metrics = _aggregate_case_rows(baro_case_rows)
        if overall["method_dataset_metrics"][f"BARO__{dataset}"] != rebuilt_metrics:
            raise FinalComparisonBlocked(f"final BARO metrics cannot be independently rebuilt: {dataset}")
        if rebuilt_metrics["cases"] != label_metadata[dataset]["case_count"]:
            raise FinalComparisonBlocked(f"final BARO denominator differs from labels: {dataset}")
        expected_fault_rows = _fault_rows("BARO", dataset, baro_case_rows)
        actual_fault_rows = [
            row
            for row in final["fault_level"]["rows"]
            if row["method"] == "BARO" and row["dataset"] == dataset
        ]
        if actual_fault_rows != expected_fault_rows:
            raise FinalComparisonBlocked(f"final BARO fault rows cannot be independently rebuilt: {dataset}")
        ada_rows, _ = _frozen_ada_case_rows(root, dataset)
        bootstrap_rows = {
            row["method"]: row
            for row in final["paired_bootstrap"]["rows"]
            if row["dataset"] == dataset
        }
        for metric, key in (("Avg@5", "primary_delta_avg5"), ("AC@1", "secondary_delta_ac1")):
            expected_bootstrap = _bootstrap_delta(ada_rows, baro_case_rows, metric=metric)
            if bootstrap_rows["BARO"][key] != expected_bootstrap:
                raise FinalComparisonBlocked(
                    f"final BARO bootstrap cannot be independently rebuilt: {dataset} {metric}"
                )

    final_fault = final["fault_level"]["rows"]
    final_fault_index = {(row["method"], row["dataset"], row["fault"]): row for row in final_fault}
    for key, row in v2["fault_index"].items():
        if final_fault_index.get(key) != row:
            raise FinalComparisonBlocked(f"final fault row changed frozen V2 identity: {key}")
    if set(method for method, _, _ in final_fault_index) != set(FINAL_REPORT_ORDER):
        raise FinalComparisonBlocked("final fault table method set is invalid")

    final_robustness = final["robustness"]["table_c"]
    final_robustness_index = {(row["method"], row["dataset"]): row for row in final_robustness["rows"]}
    old_columns = v2["robustness_columns"]
    for key, row in v2["robustness_index"].items():
        final_row = final_robustness_index[key]
        projected = {column: final_row[column] for column in row}
        if projected != row:
            raise FinalComparisonBlocked(f"final robustness row changed frozen V2 identity: {key}")
    if set(method for method, _ in final_robustness_index) != set(FINAL_BASELINE_METHODS):
        raise FinalComparisonBlocked("final robustness method set is invalid")
    if final_robustness_index[("BARO", "re2ob")]["ENVIRONMENT_FAILURE"] != "N/A (V1 schema)":
        raise FinalComparisonBlocked("BARO V1 absent status was normalized as a false zero")

    final_comparability = final["comparability"]["table_d"]["rows"]
    final_comparability_index = {row["method"]: row for row in final_comparability}
    for method, row in v2["comparability_index"].items():
        projected = {
            key: final_comparability_index[method][key]
            for key in row
        }
        if projected != row:
            raise FinalComparisonBlocked(f"final comparability row changed frozen V2 identity: {method}")
    baro_comparability = final_comparability_index["BARO"]
    if baro_comparability["MRR_legality"] != "NOT-IDENTIFIABLE" or baro_comparability["complete_service_ranking"] != "NO":
        raise FinalComparisonBlocked("BARO comparability incorrectly claims a complete ranking")

    final_bootstrap = final["paired_bootstrap"]
    final_bootstrap_index = {(row["method"], row["dataset"]): row for row in final_bootstrap["rows"]}
    for key, row in v2["bootstrap_index"].items():
        if final_bootstrap_index.get(key) != row:
            raise FinalComparisonBlocked(f"final bootstrap row changed frozen V2 identity: {key}")
    if set(method for method, _ in final_bootstrap_index) != set(FINAL_BASELINE_METHODS):
        raise FinalComparisonBlocked("final bootstrap method set is invalid")
    if final_bootstrap.get("resamples") != BOOTSTRAP_RESAMPLES or final_bootstrap.get("seed") != BOOTSTRAP_SEED:
        raise FinalComparisonBlocked("final bootstrap design changed")
    return {"scope": scope, "final": final, "v2": v2}


def render_report_v3(root: Path) -> Path:
    data = validate_final_outputs(root, require_committed=True)
    final = data["final"]
    provenance = final["provenance"]
    overall = final["overall"]
    fault = final["fault_level"]
    robustness = final["robustness"]
    comparability = final["comparability"]
    bootstrap = final["paired_bootstrap"]

    table_b_rows = [
        {
            **row,
            "Dataset": DATASET_DISPLAY.get(row["dataset"], row["dataset"]),
            "Method": row["method"],
            "Fault": row["fault"],
            "Cases": row["cases"],
        }
        for row in fault["rows"]
    ]
    table_c_rows = [
        {
            **row,
            "Method": row["method"],
            "Dataset": DATASET_DISPLAY.get(row["dataset"], row["dataset"]),
            "Evidence track": row["evidence_track"],
        }
        for row in robustness["table_c"]["rows"]
    ]
    table_d_rows = [
        {
            **row,
            "Method": row["method"],
            "Evidence track": row["evidence_track"],
        }
        for row in comparability["table_d"]["rows"]
    ]
    provenance_rows = []
    for method in FINAL_REPORT_ORDER:
        if method == "BARO":
            lock_path = provenance["baro_v1_evidence"]["prediction_lock_path"]
            evaluation_source = "BARO V1 records; new post-scope evaluation"
            generation = "V1 execution / V3 evaluation"
        elif method in V2_COMBINED_METHODS:
            lock_path = provenance["six_method_v2_evidence"]["prediction_lock_path"]
            evaluation_source = "immutable execution_v2/evaluation_causalrca JSON"
            generation = provenance["evidence_tracks"][method]
        else:
            lock_path = "frozen Ada-RCA Scientific V1 evidence"
            evaluation_source = "artifacts/final_method/*/metrics.json and provenance.json"
            generation = "frozen user-method evidence"
        provenance_rows.append({
            "Method": method,
            "Execution generation": generation,
            "Evidence track": provenance["evidence_tracks"][method],
            "Prediction lock": lock_path,
            "Evaluation source": evaluation_source,
        })
    baro_bootstrap = [row for row in bootstrap["rows"] if row["method"] == "BARO"]
    statistical_rows = []
    for row in baro_bootstrap:
        statistical_rows.append({
            "Dataset": DATASET_DISPLAY[row["dataset"]],
            "Delta Avg@5": row["primary_delta_avg5"]["point_estimate"],
            "95% CI Avg@5": json.dumps(row["primary_delta_avg5"]["ci_95_percent"]),
            "Delta AC@1": row["secondary_delta_ac1"]["point_estimate"],
            "95% CI AC@1": json.dumps(row["secondary_delta_ac1"]["ci_95_percent"]),
        })

    branch = git(root, "branch", "--show-current").stdout.strip()
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    report = f"""# Ada-RCA — RCAEval Seven-Baseline Final Composite Comparison

## Material Passport

- Material ID: `ada-rca-rcaeval-final-composite-v3`
- Type: `Experiment Result`
- Verification status: `VERIFIED`
- Scope: `FINAL_COMPOSITE_SEVEN_BASELINE_COMPARISON`

The previous six-baseline V2 evaluation remains immutable. BARO is incorporated
from its previously frozen V1 label-free prediction lock without rerunning
BARO. The final seven-baseline table is therefore a composite comparison
across frozen evidence tracks, not a claim that all seven baselines were
executed under one original pre-label global lock.

## Table A — Overall RCA Performance

{_markdown_table(overall['table_a']['columns'], overall['table_a']['rows'])}

## Table B — Fault-Level Performance

{_markdown_table(('Method', 'Dataset', 'Fault', 'Cases', 'AC@1', 'AC@3', 'AC@5', 'Avg@5'), table_b_rows)}

Fault denominators are taken from the frozen label mapping and verified before
reporting; RE2-OB and RE2-TT are never pooled.

## Table C — Execution Robustness / Evidence Track

The rows retain each track's own status taxonomy. BARO's V1 schema did not
record V2-only `ENVIRONMENT_FAILURE`, `INPUT_INTEGRITY_FAILURE`, or
`PROCESS_CRASH/OOM` fields; `N/A (V1 schema)` means not present in that schema,
not zero. The six inherited rows are copied from the immutable V2 JSON.

{_markdown_table(robustness['table_c']['columns'], table_c_rows)}

## Table D — Protocol / Output Comparability

Ada-RCA is a root-supervised, cross-case-trained method with a native complete
service ranking. The RCAEval baselines are primarily case-wise unsupervised
methods whose native indicator or operation outputs are projected to partial
service rankings. Baseline MRR is therefore `NOT-IDENTIFIABLE`; no candidate
completion is performed.

{_markdown_table(comparability['table_d']['columns'], table_d_rows)}

## Table E — Evidence Provenance

{_markdown_table(('Method', 'Execution generation', 'Evidence track', 'Prediction lock', 'Evaluation source'), provenance_rows)}

BARO is `V1_LOCKED_COMPLETE`; CIRCA, MicroCause, MicroRank, TraceRCA, and
mmBARO are `V2_RESCUE_LOCKED`; CausalRCA is `V2_CPU_EXTENSION_LOCKED`; and
Ada-RCA is frozen Scientific V1 user-method evidence.

## Statistical Comparison — Paired Fault-Stratified Bootstrap

The BARO rows below are the only newly computed statistical rows. The primary
estimand is Ada-RCA minus BARO `Avg@5`, and the secondary estimand is Ada-RCA
minus BARO `AC@1`. RE2-OB and RE2-TT are analyzed separately with
`{BOOTSTRAP_RESAMPLES}` resamples and seed `{BOOTSTRAP_SEED}`.

{_markdown_table(('Dataset', 'Delta Avg@5', '95% CI Avg@5', 'Delta AC@1', '95% CI AC@1'), statistical_rows)}

The six inherited baseline bootstrap rows are copied from
`artifacts/baseline_eval/execution_v2/evaluation_causalrca/paired_bootstrap_v2.json`
and pass exact identity checks; they are not reinterpreted or recomputed.

## Scientific Limitations and Claim Boundary

- BARO is a complete V1 locked execution; the other five rescue baselines are
  V2 rescue evidence; CausalRCA is a V2 CPU additive extension.
- BARO was not rerun, and the existing six-method V2 outputs were not
  recomputed or overwritten.
- Metric semantics are aligned where legally identifiable, but execution
  provenance, native granularity, preprocessing, candidate coverage, and
  output completeness are not identical.
- Baseline MRR is unavailable because no audited RCAEval baseline guarantees a
  complete legal service ranking.
- Ada-RCA is supervised cross-case service ranking, whereas the RCAEval
  baselines are mostly case-wise unsupervised partial rankings.
- This evidence does not support an SOTA, universally superior, same-protocol
  superiority, causal superiority, unseen-system generalization, or unseen-root
  generalization claim.

The supported statement is limited to comparison under the frozen RE2-OB and
RE2-TT case universes and the legally aligned top-k service-projection metrics
against seven reproduced RCAEval baselines: BARO, CIRCA, MicroCause, MicroRank,
TraceRCA, mmBARO, and CausalRCA.

## Repository Provenance

- Branch at report generation: `{branch}`
- HEAD at report generation: `{head}`
- Scope-freeze commit: `{provenance['scope']['commit']}`
- BARO lock commit: `{provenance['baro_v1_evidence']['prediction_lock_commit']}`
- Six-method V2 combined lock commit: `{provenance['six_method_v2_evidence']['prediction_lock_commit']}`
- Final comparison code commit: `{_commit_for_path(root, Path('src/baseline_eval/final_comparison.py'))}`
- Input manifest: `{provenance['input_manifest']['sha256']}`
- RCAEval: `{provenance['rcaeval']['commit']}`

Final status: `SEVEN_BASELINE_FINAL_COMPOSITE_COMPARISON_READY`
"""
    path = root / FINAL_REPORT_RELATIVE
    if path.exists():
        raise FinalComparisonBlocked("final comparison report already exists and is immutable")
    path.write_text(report, encoding="utf-8")
    return path


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("audit-scope-v3")
    sub.add_parser("evaluate-v3")
    sub.add_parser("validate-v3")
    sub.add_parser("render-report-v3")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if args.command == "audit-scope-v3":
        audit = verify_baro_v1_lock(root)
        print("BARO_SCOPE_AUDIT=PASS")
        print(audit["lock"]["disposition"])
        print(audit["lock"]["status_counts"])
    elif args.command == "evaluate-v3":
        for path in evaluate_final_comparison(root).values():
            print(path)
    elif args.command == "validate-v3":
        validate_final_outputs(root, require_committed=False)
        print("FINAL_COMPARISON_V3_VALID=PASS")
    else:
        print(render_report_v3(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
