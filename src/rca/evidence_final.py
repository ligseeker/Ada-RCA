"""Final limitation-qualified decision for the RCA evidence closure audit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

from .evidence_closure import FROZEN_COMMIT, V1_REFERENCE_COMMIT, sha256_file


GATE_ARTIFACTS = {
    "gate_1": "artifacts/evidence_closure/metric_reconstruction_v1_1.json",
    "gate_2": "artifacts/evidence_closure/bootstrap_corrected_v1_1.json",
    "gate_3": "artifacts/evidence_closure/telemetry_information_loss_v1_1.json",
    "gate_4": "artifacts/evidence_closure/provenance_normalization_v1_1.json",
}
INTERPRETATION_ARTIFACTS = {
    "evidence_semantic_correction": (
        "artifacts/evidence_closure/evidence_semantic_correction_v1_1.json"
    ),
    "trace_error_representation_invariant": (
        "artifacts/evidence_closure/trace_error_representation_invariant.json"
    ),
}
FROZEN_PREDICTIVE_PATHS = (
    "artifacts/final_method",
    "artifacts/opt/final",
    "artifacts/opt/o4_nested",
    "artifacts/features",
    "artifacts/source",
    "artifacts/splits",
    "docs/OPT_SEARCH_SPACE_FREEZE_V1.md",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=root, text=True).strip()


def _load(root: Path, relative_path: str) -> Dict[str, Any]:
    return json.loads((root / relative_path).read_text(encoding="utf-8"))


def build_final_evidence_decision(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    gates = {name: _load(root, path) for name, path in GATE_ARTIFACTS.items()}
    metric = gates["gate_1"]
    bootstrap = gates["gate_2"]
    telemetry = gates["gate_3"]
    provenance = gates["gate_4"]
    semantic = _load(root, INTERPRETATION_ARTIFACTS["evidence_semantic_correction"])
    trace_error = _load(
        root, INTERPRETATION_ARTIFACTS["trace_error_representation_invariant"]
    )

    gate_statuses = {
        "gate_1": metric["gate_1"]["status"],
        "gate_2": bootstrap["gate_2"]["status"],
        "gate_3": telemetry["gate_3"]["status"],
        "gate_4": provenance["gate_4"]["status"],
    }
    v1_full_integrity = all(
        metric["evidence_levels"]["V1-SCIENTIFIC"]["datasets"][dataset][
            "FULL_RANKING_INTEGRITY"
        ]["status"]
        == "FULL_RANKING_INTEGRITY_PASS"
        for dataset in ("re2ob", "re2tt")
    )
    v1_rank_metrics = all(
        metric["tracks"]["V1-SCIENTIFIC"]["datasets"][dataset]["status"] == "PASS"
        for dataset in ("re2ob", "re2tt")
    )
    per_rank_sufficient = all(
        metric["evidence_levels"]["PER-DATASET-OPT"]["datasets"][dataset][
            "RANK_METRIC_SUFFICIENT"
        ]["status"]
        == "RANK_METRIC_SUFFICIENT_PASS"
        for dataset in ("re2ob", "re2tt")
    )
    per_full_unverifiable = all(
        metric["evidence_levels"]["PER-DATASET-OPT"]["datasets"][dataset][
            "FULL_RANKING_INTEGRITY"
        ]["status"]
        == "FULL_RANKING_INTEGRITY_NOT_AUDITABLE"
        for dataset in ("re2ob", "re2tt")
    )

    replay_statuses = {
        dataset: _load(root, f"artifacts/final_method/{dataset}/replay_audit.json")[
            "integrity_status"
        ]
        for dataset in ("re2ob", "re2tt")
    }
    valid_v1_provenance = all(status == "INTEGRITY_VALID" for status in replay_statuses.values())
    shortcut = _load(root, "artifacts/opt/diagnostics/shortcut_audit.json")
    no_explicit_label_leakage = (
        shortcut["fault_type"]["status"] == "PASS"
        and not shortcut["fault_type"]["predictive_feature"]
        and shortcut["root_frequency"]["status"] == "PASS"
        and not shortcut["root_frequency"]["predictive_feature"]
        and shortcut["nested_leakage"]["status"] == "PASS"
        and shortcut["scaler_leakage"]["status"] == "PASS"
    )

    global_comparison = bootstrap["comparisons"]["GLOBAL-OPT_minus_V1"]
    global_identity = all(
        metric_record["point_delta"] == 0.0 and metric_record["ci95"] == [0.0, 0.0]
        for dataset in global_comparison["datasets"].values()
        for metric_record in dataset["metrics"].values()
    )
    per_comparison = bootstrap["comparisons"]["PER-DATASET-OPT_minus_V1"]["datasets"]
    per_avg_points = {
        dataset: float(record["metrics"]["Avg@5"]["point_delta"])
        for dataset, record in per_comparison.items()
    }
    per_avg_cis = {
        dataset: [float(value) for value in record["metrics"]["Avg@5"]["ci95"]]
        for dataset, record in per_comparison.items()
    }
    no_consistent_avg5_gain = (
        per_avg_points["re2ob"] < 0.0
        and per_avg_points["re2tt"] > 0.0
        and per_avg_cis["re2tt"][0] <= 0.0 <= per_avg_cis["re2tt"][1]
    )
    method_selection_not_overturned = global_identity and no_consistent_avg5_gain

    semantic_integrity = (
        semantic["summary"]["genuine_fail_count"] == 0
        and semantic["summary"]["per_dataset_full_ranking_status"]
        == "FULL_RANKING_INTEGRITY_NOT_AUDITABLE"
        and semantic["summary"]["per_dataset_rank_metric_status"]
        == "RANK_METRIC_SUFFICIENT_PASS"
    )
    trace_error_feature_integrity = all(
        record["case_count"] == 90
        and record["trace_error_dimension"] == 17
        and record["provenance"]["all_feature_files_match_frozen_commit"]
        for record in trace_error["datasets"].values()
    )
    trace_error_classification_valid = trace_error["final_classification"] in {
        "TRACE_ERROR_EFFECTIVELY_NONDISCRIMINATIVE_IN_FROZEN_Z2",
        "TRACE_ERROR_RETAINS_CANDIDATE_DISCRIMINATIVE_INFORMATION",
        "TRACE_ERROR_STATUS_MIXED",
    }

    changed_frozen_paths = _git(
        root, "diff", "--name-only", FROZEN_COMMIT, "--", *FROZEN_PREDICTIVE_PATHS
    ).splitlines()
    optimization_branch_unchanged = (
        _git(root, "rev-parse", "research/performance-optimization") == FROZEN_COMMIT
    )
    amendment = metric["protocol_amendment"]
    amendment_transparent_and_prior = (
        amendment["status"] == "POST-AUDIT PROTOCOL CLARIFICATION"
        and amendment["commit_is_ancestor_of_execution_head"]
        and all(amendment["corrected_outputs_absent_at_amendment_commit"].values())
    )

    integrity_conditions = {
        "all_downstream_gates_pass": all(value == "PASS" for value in gate_statuses.values()),
        "v1_full_ranking_evidence_valid": v1_full_integrity,
        "v1_metrics_independently_reconstructed": v1_rank_metrics,
        "v1_provenance_valid": valid_v1_provenance,
        "no_explicit_root_or_fault_leakage_detected": no_explicit_label_leakage,
        "bootstrap_valid": bootstrap["gate_2"]["invariants_status"] == "PASS",
        "per_dataset_rank_metric_sufficient": per_rank_sufficient,
        "per_dataset_full_ranking_unverifiable": per_full_unverifiable,
        "post_audit_amendment_transparent_and_prior": amendment_transparent_and_prior,
        "evidence_semantic_correction_valid": semantic_integrity,
        "trace_error_feature_integrity_valid": trace_error_feature_integrity,
        "trace_error_classification_valid": trace_error_classification_valid,
        "frozen_predictive_artifacts_and_search_space_unchanged": not changed_frozen_paths,
        "performance_optimization_branch_unchanged": optimization_branch_unchanged,
    }
    conditions = {
        **integrity_conditions,
        "corrected_evidence_does_not_materially_overturn_v1_selection": (
            method_selection_not_overturned
        ),
    }
    integrity_pass = all(integrity_conditions.values())
    if not integrity_pass:
        decision = "RCA_EVIDENCE_NOT_CLOSED"
    elif not method_selection_not_overturned:
        decision = "RCA_EVIDENCE_CLOSED_HUMAN_DECISION_REQUIRED"
    else:
        decision = "RCA_FREEZE_READY_WITH_LIMITATION"

    tt_ac1 = per_comparison["re2tt"]["metrics"]["AC@1"]
    return {
        "schema_version": "ada_rca_evidence_closure_final_v1_1",
        "audit_type": "LIMITATION_QUALIFIED_SCIENTIFIC_FREEZE_DECISION",
        "gate_artifacts": {
            name: {
                "path": path,
                "sha256": sha256_file(root / path),
                "status": gate_statuses[name],
            }
            for name, path in GATE_ARTIFACTS.items()
        },
        "interpretation_artifacts": {
            name: {"path": path, "sha256": sha256_file(root / path)}
            for name, path in INTERPRETATION_ARTIFACTS.items()
        },
        "conditions": conditions,
        "integrity_conditions_pass": integrity_pass,
        "v1_scientific_integrity": {
            "full_ranking_integrity": (
                "FULL_RANKING_INTEGRITY_PASS" if v1_full_integrity else "FAIL"
            ),
            "independent_rank_metrics": "PASS" if v1_rank_metrics else "FAIL",
            "provenance": replay_statuses,
            "leakage_boundary": (
                "NO_EXPLICIT_LABEL_LEAKAGE_DETECTED" if no_explicit_label_leakage else "FAIL"
            ),
            "service_fingerprint": shortcut["service_fingerprint"],
            "no_fatal_evidence_defect_discovered_in_gate_5": integrity_pass,
        },
        "optimization_post_study_integrity": {
            "global_opt_byte_identical_to_v1": global_identity,
            "per_dataset_rank_metric_sufficiency": (
                "RANK_METRIC_SUFFICIENT_PASS" if per_rank_sufficient else "FAIL"
            ),
            "per_dataset_full_ranking_integrity": (
                "FULL_RANKING_INTEGRITY_NOT_AUDITABLE" if per_full_unverifiable else "FAIL"
            ),
            "corrected_avg5_candidate_minus_v1": {
                dataset: {"point": per_avg_points[dataset], "ci95": per_avg_cis[dataset]}
                for dataset in ("re2ob", "re2tt")
            },
            "tt_ac1_candidate_minus_v1": {
                "point": float(tt_ac1["point_delta"]),
                "ci95": [float(value) for value in tt_ac1["ci95"]],
                "interpretation": "DATASET_SPECIFIC_POSITIVE_SIGNAL",
            },
            "shared_gain": False,
            "method_selection_interpretation": "NO_CLEAR_OPTIMIZATION_GAIN",
            "fully_reproducible_candidate_score_ranking_experiment": False,
            "executed_scope": (
                "Conditional Logit, six frozen representation combinations, "
                "and lambda grid {0.1, 1.0, 10.0}"
            ),
            "tree_rankers": provenance["ranker_execution"]["canonical_status"],
        },
        "telemetry_boundary": telemetry["auditability"],
        "trace_error_representation": {
            "final_classification": trace_error["final_classification"],
            "datasets": {
                dataset: {
                    "rows": record["total_candidate_case_rows"],
                    "all_zero_rows": record["all_zero_rows"],
                    "nonzero_rows": record["nonzero_rows"],
                    "unique_vectors": record["unique_trace_error_vectors"],
                    "dimensions_with_nonzero_variance": record[
                        "dimensions_with_nonzero_variance"
                    ],
                    "candidate_discriminative_cases": record[
                        "within_case_candidate_discriminative_variation"
                    ]["case_count"],
                }
                for dataset, record in trace_error["datasets"].items()
            },
            "optimization_trace_cross_check": trace_error[
                "optimization_trace_cross_check"
            ]["status"],
        },
        "historical_and_ranker_semantics": {
            "historical_reference": provenance["historical_reference"]["normalized_term"],
            "historical_qualifier": provenance["historical_reference"]["required_qualifier"],
            "rankers": provenance["ranker_execution"]["canonical_status"],
        },
        "immutability": {
            "frozen_commit": FROZEN_COMMIT,
            "v1_scientific_reference_commit": V1_REFERENCE_COMMIT,
            "changed_frozen_predictive_paths": changed_frozen_paths,
            "performance_optimization_branch_head": _git(
                root, "rev-parse", "research/performance-optimization"
            ),
        },
        "limitations": [
            "POST-AUDIT PROTOCOL CLARIFICATION; not the original preregistration",
            "PER-DATASET complete candidate scores/rankings are unavailable",
            "PER-DATASET FULL_RANKING_INTEGRITY_NOT_AUDITABLE",
            "development benchmarks were reused; no untouched external test was run",
            "Trace Error is globally nonzero but candidate-nondiscriminative in frozen Z2",
            "RE2-OB zero-baseline/post-positive Trace Error can be lost at robust scaling",
            "raw-record to derived-cell lineage is not fully auditable",
            "service/telemetry fingerprints remain possible",
            "XGBoost and LightGBM rankers were not executed",
            "fixed-prediction bootstrap excludes search, reuse, and system-sampling uncertainty",
        ],
        "final_decision": decision,
        "maximum_protocol_allowed_state": "RCA_FREEZE_READY_WITH_LIMITATION",
        "unconditional_scientific_freeze_ready": False,
    }
