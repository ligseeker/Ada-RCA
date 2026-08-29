"""Paired rank-metric bootstrap for the amended evidence-closure audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

import numpy as np

from .evidence_closure import (
    METRIC_TOLERANCE,
    aggregate_independent_rank_metrics,
    independent_case_metrics,
    load_frozen_rank_cases,
    sha256_file,
)


FAULT_ORDER = ("cpu", "mem", "disk", "socket", "delay", "loss")
BOOTSTRAP_METRICS = ("Avg@5", "AC@1", "MRR")
BOOTSTRAP_ITERATIONS = 10000
BOOTSTRAP_SEED = 20260829
LEGACY_BOOTSTRAP_SHA256 = "23cd9e27592746191f116a163341f5b8d241ad290a7572aef2ea882f711d927e"


def _case_map(cases: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for case in cases:
        case_id = str(case["case_id"])
        if case_id in mapped:
            raise ValueError(f"duplicate case ID: {case_id}")
        mapped[case_id] = {
            "case_id": case_id,
            "fault_type": str(case["fault_type"]),
            "root_rank": int(case["root_rank"]),
            "metrics": independent_case_metrics(int(case["root_rank"])),
        }
    return mapped


def validate_pair_alignment(
    candidate_cases: Sequence[Mapping[str, Any]],
    v1_cases: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    candidate = _case_map(candidate_cases)
    v1 = _case_map(v1_cases)
    if set(candidate) != set(v1):
        raise ValueError("paired case IDs differ")
    fault_mismatches = sorted(
        case_id
        for case_id in candidate
        if candidate[case_id]["fault_type"] != v1[case_id]["fault_type"]
    )
    if fault_mismatches:
        raise ValueError(f"paired fault strata differ: {fault_mismatches}")
    counts = {
        fault: sum(row["fault_type"] == fault for row in candidate.values())
        for fault in FAULT_ORDER
    }
    if any(count != 15 for count in counts.values()) or sum(counts.values()) != 90:
        raise ValueError(f"expected six 15-case fault strata, observed {counts}")
    return {
        "status": "PASS",
        "case_count": len(candidate),
        "identical_case_ids": True,
        "identical_fault_assignments": True,
        "sampled_case_ids_shared_by_construction": True,
        "fault_counts": counts,
    }


def build_sample_plan(
    cases: Sequence[Mapping[str, Any]],
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> Tuple[Dict[str, Tuple[str, ...]], np.ndarray, str]:
    mapped = _case_map(cases)
    strata = {
        fault: tuple(sorted(case_id for case_id, row in mapped.items() if row["fault_type"] == fault))
        for fault in FAULT_ORDER
    }
    if any(len(ids) != 15 for ids in strata.values()):
        raise ValueError("sample plan requires exactly 15 cases per fault stratum")
    rng = np.random.RandomState(seed)
    indices = np.empty((int(iterations), len(FAULT_ORDER), 15), dtype=np.int16)
    for iteration in range(int(iterations)):
        for fault_index, fault in enumerate(FAULT_ORDER):
            indices[iteration, fault_index, :] = rng.randint(0, len(strata[fault]), len(strata[fault]))
    digest_payload = json.dumps(strata, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    digest = hashlib.sha256(digest_payload + indices.tobytes()).hexdigest()
    return strata, indices, digest


def paired_fault_stratified_rank_bootstrap(
    candidate_cases: Sequence[Mapping[str, Any]],
    v1_cases: Sequence[Mapping[str, Any]],
    metric: str,
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = BOOTSTRAP_SEED,
    sample_plan: Tuple[Dict[str, Tuple[str, ...]], np.ndarray, str] | None = None,
) -> Dict[str, Any]:
    if metric not in BOOTSTRAP_METRICS:
        raise ValueError(f"unsupported bootstrap metric: {metric}")
    alignment = validate_pair_alignment(candidate_cases, v1_cases)
    candidate = _case_map(candidate_cases)
    v1 = _case_map(v1_cases)
    strata, indices, plan_sha256 = sample_plan or build_sample_plan(v1_cases, iterations, seed)
    if indices.shape != (int(iterations), len(FAULT_ORDER), 15):
        raise ValueError("sample plan shape violates fault-stratified accounting")
    arrays: Dict[str, np.ndarray] = {}
    sampled_parts = []
    for fault_index, fault in enumerate(FAULT_ORDER):
        ids = strata[fault]
        delta = np.asarray(
            [candidate[case_id]["metrics"][metric] - v1[case_id]["metrics"][metric] for case_id in ids],
            dtype=np.float64,
        )
        arrays[fault] = delta
        sampled_parts.append(delta[indices[:, fault_index, :]])
    samples = np.concatenate(sampled_parts, axis=1).mean(axis=1)
    point = float(np.concatenate([arrays[fault] for fault in FAULT_ORDER]).mean())
    return {
        "metric": metric,
        "direction": "Candidate - V1",
        "point_delta": point,
        "ci95": [
            float(np.percentile(samples, 2.5)),
            float(np.percentile(samples, 97.5)),
        ],
        "iterations": int(iterations),
        "seed": int(seed),
        "sampling_unit": "failure case",
        "fault_stratified": True,
        "sample_plan_sha256": plan_sha256,
        "delta_by_fault": {fault: float(arrays[fault].mean()) for fault in FAULT_ORDER},
        "pair_alignment": alignment,
    }


def _invariant_audit(
    candidate_cases: Sequence[Mapping[str, Any]],
    v1_cases: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    plan: Tuple[Dict[str, Tuple[str, ...]], np.ndarray, str],
    iterations: int,
    seed: int,
) -> Dict[str, Any]:
    alignment = validate_pair_alignment(candidate_cases, v1_cases)
    deterministic_plan = build_sample_plan(v1_cases, iterations, seed)
    deterministic = plan[2] == deterministic_plan[2] and np.array_equal(plan[1], deterministic_plan[1])
    identity_details: Dict[str, Any] = {}
    antisymmetry_details: Dict[str, Any] = {}
    direct_details: Dict[str, Any] = {}
    candidate_aggregate = aggregate_independent_rank_metrics(candidate_cases)
    v1_aggregate = aggregate_independent_rank_metrics(v1_cases)
    for metric in BOOTSTRAP_METRICS:
        identity = paired_fault_stratified_rank_bootstrap(
            v1_cases, v1_cases, metric, iterations, seed, plan
        )
        reverse = paired_fault_stratified_rank_bootstrap(
            v1_cases, candidate_cases, metric, iterations, seed, plan
        )
        forward = results[metric]
        identity_pass = identity["point_delta"] == 0.0 and identity["ci95"] == [0.0, 0.0]
        antisymmetry_pass = (
            abs(float(forward["point_delta"]) + float(reverse["point_delta"])) <= METRIC_TOLERANCE
            and abs(float(forward["ci95"][0]) + float(reverse["ci95"][1])) <= METRIC_TOLERANCE
            and abs(float(forward["ci95"][1]) + float(reverse["ci95"][0])) <= METRIC_TOLERANCE
        )
        expected_point = candidate_aggregate[metric] - v1_aggregate[metric]
        direct_pass = abs(float(forward["point_delta"]) - expected_point) <= METRIC_TOLERANCE
        identity_details[metric] = {
            "status": "PASS" if identity_pass else "FAIL",
            "point_delta": identity["point_delta"],
            "ci95": identity["ci95"],
        }
        antisymmetry_details[metric] = {
            "status": "PASS" if antisymmetry_pass else "FAIL",
            "forward_point": forward["point_delta"],
            "reverse_point": reverse["point_delta"],
            "forward_ci95": forward["ci95"],
            "reverse_ci95": reverse["ci95"],
        }
        direct_details[metric] = {
            "status": "PASS" if direct_pass else "FAIL",
            "bootstrap_point": forward["point_delta"],
            "direct_candidate_minus_v1": expected_point,
            "absolute_difference": abs(float(forward["point_delta"]) - expected_point),
            "tolerance": METRIC_TOLERANCE,
        }
    accounting_pass = plan[1].shape == (iterations, 6, 15) and alignment["fault_counts"] == {
        fault: 15 for fault in FAULT_ORDER
    }
    checks = {
        "identity": all(detail["status"] == "PASS" for detail in identity_details.values()),
        "antisymmetry": all(detail["status"] == "PASS" for detail in antisymmetry_details.values()),
        "direct_point_consistency": all(detail["status"] == "PASS" for detail in direct_details.values()),
        "pair_alignment": alignment["status"] == "PASS",
        "fault_stratum_accounting": accounting_pass,
        "deterministic_seed": deterministic,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
        "identity": identity_details,
        "antisymmetry": antisymmetry_details,
        "direct_point_consistency": direct_details,
        "pair_alignment": alignment,
        "fault_stratum_accounting": {
            "status": "PASS" if accounting_pass else "FAIL",
            "original_size_by_stratum": alignment["fault_counts"],
            "bootstrap_size_by_stratum_per_iteration": {fault: 15 for fault in FAULT_ORDER},
            "total_cases_per_iteration": 90,
            "sample_plan_shape": list(plan[1].shape),
        },
        "deterministic_seed": {
            "status": "PASS" if deterministic else "FAIL",
            "seed": seed,
            "first_plan_sha256": plan[2],
            "repeat_plan_sha256": deterministic_plan[2],
        },
    }


def build_bootstrap_forensic_audit(
    root: Path,
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> Dict[str, Any]:
    root = root.resolve()
    gate_1_path = root / "artifacts/evidence_closure/metric_reconstruction_v1_1.json"
    gate_1 = json.loads(gate_1_path.read_text(encoding="utf-8"))
    if gate_1["gate_1"]["status"] != "PASS":
        raise ValueError("Gate 1 did not authorize bootstrap")
    comparisons: Dict[str, Any] = {}
    invariants: Dict[str, Any] = {}
    cases_by_track_dataset: Dict[Tuple[str, str], Sequence[Mapping[str, Any]]] = {}
    for track in ("V1-SCIENTIFIC", "GLOBAL-OPT", "PER-DATASET-OPT"):
        for dataset in ("re2ob", "re2tt"):
            cases_by_track_dataset[(track, dataset)] = load_frozen_rank_cases(root, track, dataset)
    for candidate in ("GLOBAL-OPT", "PER-DATASET-OPT"):
        comparison_name = f"{candidate}_minus_V1"
        comparison_datasets: Dict[str, Any] = {}
        invariant_datasets: Dict[str, Any] = {}
        for dataset in ("re2ob", "re2tt"):
            candidate_cases = cases_by_track_dataset[(candidate, dataset)]
            v1_cases = cases_by_track_dataset[("V1-SCIENTIFIC", dataset)]
            plan = build_sample_plan(v1_cases, iterations, seed)
            metric_results = {
                metric: paired_fault_stratified_rank_bootstrap(
                    candidate_cases, v1_cases, metric, iterations, seed, plan
                )
                for metric in BOOTSTRAP_METRICS
            }
            comparison_datasets[dataset] = {
                "candidate": candidate,
                "baseline": "V1-SCIENTIFIC",
                "direction": "Candidate - V1",
                "metrics": metric_results,
            }
            invariant_datasets[dataset] = _invariant_audit(
                candidate_cases, v1_cases, metric_results, plan, iterations, seed
            )
        comparisons[comparison_name] = {"datasets": comparison_datasets}
        invariants[comparison_name] = {"datasets": invariant_datasets}

    legacy_path = root / "artifacts/opt/final/bootstrap.json"
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    legacy_comparison: Dict[str, Any] = {}
    legacy_names = {
        "GLOBAL-OPT": "V1_vs_GLOBAL_OPT",
        "PER-DATASET-OPT": "V1_vs_PER_DATASET_OPT",
    }
    for candidate, legacy_name in legacy_names.items():
        by_dataset: Dict[str, Any] = {}
        corrected_name = f"{candidate}_minus_V1"
        for dataset in ("re2ob", "re2tt"):
            legacy_record = legacy[legacy_name][dataset]
            by_metric: Dict[str, Any] = {}
            for index, metric in enumerate(legacy_record["metrics"]):
                corrected = comparisons[corrected_name]["datasets"][dataset]["metrics"][metric]
                legacy_point = float(legacy_record["point_delta"][index])
                legacy_ci = [float(value) for value in legacy_record["ci95"][index]]
                point_matches = abs(legacy_point - float(corrected["point_delta"])) <= METRIC_TOLERANCE
                forward_ci_matches = all(
                    abs(legacy_ci[position] - float(corrected["ci95"][position])) <= METRIC_TOLERANCE
                    for position in (0, 1)
                )
                reverse_ci = [-float(corrected["ci95"][1]), -float(corrected["ci95"][0])]
                reverse_ci_matches = all(
                    abs(legacy_ci[position] - reverse_ci[position]) <= METRIC_TOLERANCE
                    for position in (0, 1)
                )
                by_metric[metric] = {
                    "legacy_point": legacy_point,
                    "corrected_candidate_minus_v1_point": corrected["point_delta"],
                    "legacy_point_direction_status": (
                        "MATCHES_CANDIDATE_MINUS_V1" if point_matches else "MISMATCH"
                    ),
                    "legacy_ci95": legacy_ci,
                    "corrected_candidate_minus_v1_ci95": corrected["ci95"],
                    "corrected_v1_minus_candidate_ci95": reverse_ci,
                    "legacy_ci_matches_candidate_minus_v1_estimator": forward_ci_matches,
                    "legacy_ci_matches_v1_minus_candidate_estimator": reverse_ci_matches,
                }
            by_dataset[dataset] = {"metrics": by_metric}
        legacy_comparison[candidate] = {"datasets": by_dataset}

    all_invariants_pass = all(
        dataset["status"] == "PASS"
        for comparison in invariants.values()
        for dataset in comparison["datasets"].values()
    )
    per_dataset_details = [
        detail
        for dataset in legacy_comparison["PER-DATASET-OPT"]["datasets"].values()
        for detail in dataset["metrics"].values()
    ]
    documentation_direction_error = all(
        detail["legacy_point_direction_status"] == "MATCHES_CANDIDATE_MINUS_V1"
        for detail in per_dataset_details
    )
    estimator_mismatch = any(
        not detail["legacy_ci_matches_candidate_minus_v1_estimator"]
        and not detail["legacy_ci_matches_v1_minus_candidate_estimator"]
        for detail in per_dataset_details
    )
    if documentation_direction_error and estimator_mismatch:
        discrepancy_classification = "MULTIPLE_CAUSES"
    elif documentation_direction_error:
        discrepancy_classification = "DOCUMENTATION_DIRECTION_ERROR"
    elif estimator_mismatch:
        discrepancy_classification = "ESTIMATOR_MISMATCH"
    else:
        discrepancy_classification = "EXPECTED_BOOTSTRAP_BEHAVIOR"
    legacy_source_unchanged = sha256_file(legacy_path) == LEGACY_BOOTSTRAP_SHA256
    gate_pass = all_invariants_pass and legacy_source_unchanged
    return {
        "schema_version": "ada_rca_bootstrap_corrected_v1_1",
        "audit_type": "PAIRED_BOOTSTRAP_FORENSIC_AUDIT",
        "gate_1_input": {
            "path": "artifacts/evidence_closure/metric_reconstruction_v1_1.json",
            "sha256": sha256_file(gate_1_path),
            "status": gate_1["gate_1"]["status"],
        },
        "statistical_contract": {
            "scientific_input_fields": ["case_id", "fault_type", "root_rank"],
            "direction": "Candidate - V1",
            "sampling_unit": "failure case",
            "pairing": "identical sampled case IDs for Candidate and V1",
            "stratification": "within fault type, 15 draws with replacement from 15 cases",
            "iterations": int(iterations),
            "seed": int(seed),
            "interval": "95% percentile interval",
            "conditionality": "fixed frozen root ranks only",
        },
        "comparisons": comparisons,
        "invariants": invariants,
        "legacy_forensic": {
            "source": "artifacts/opt/final/bootstrap.json",
            "sha256": sha256_file(legacy_path),
            "expected_frozen_sha256": LEGACY_BOOTSTRAP_SHA256,
            "source_unchanged": legacy_source_unchanged,
            "generator_source": "NOT_COMMITTED_WITH_LEGACY_ARTIFACT",
            "documented_direction": "V1 - PER-DATASET-OPT",
            "point_value_direction": "PER-DATASET-OPT - V1",
            "discrepancy_classification": discrepancy_classification,
            "causes": {
                "DOCUMENTATION_DIRECTION_ERROR": (
                    "CONFIRMED: prose labels V1 minus PER-DATASET while all stored point values equal PER-DATASET minus V1"
                    if documentation_direction_error
                    else "NOT CONFIRMED"
                ),
                "ESTIMATOR_MISMATCH": (
                    "CONFIRMED: legacy CIs match neither direction of the specified paired case-ID estimator"
                    if estimator_mismatch
                    else "NOT CONFIRMED"
                ),
                "IMPLEMENTATION_ERROR": (
                    "UNRESOLVED: the legacy generator source was not committed, so no low-level bug is asserted"
                ),
                "EXPECTED_BOOTSTRAP_BEHAVIOR": (
                    "REJECTED: deterministic reconstruction under the frozen estimator does not reproduce the legacy CIs"
                    if estimator_mismatch
                    else "CONSISTENT"
                ),
            },
            "comparison": legacy_comparison,
        },
        "gate_2": {
            "status": "PASS" if gate_pass else "FAIL",
            "invariants_status": "PASS" if all_invariants_pass else "FAIL",
            "legacy_source_immutability": "PASS" if legacy_source_unchanged else "FAIL",
            "telemetry_authorization": "GATE_3_AUTHORIZED" if gate_pass else "STOP",
            "terminal_state_if_failed": "RCA_EVIDENCE_NOT_CLOSED" if not gate_pass else None,
        },
    }
