"""Provenance and claim normalization for Evidence Closure Gate 4."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping, Set

from .evidence_closure import FROZEN_COMMIT, sha256_file


DATASETS = ("re2ob", "re2tt")


def _matches_frozen_commit(root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ("git", "diff", "--quiet", FROZEN_COMMIT, "--", relative_path),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _collect_rankers(value: Any) -> Set[str]:
    rankers: Set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "ranker" and isinstance(child, str):
                rankers.add(child)
            rankers.update(_collect_rankers(child))
    elif isinstance(value, list):
        for child in value:
            rankers.update(_collect_rankers(child))
    return rankers


def build_provenance_normalization(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    historical_root = root / "artifacts/opt/o1_historical"
    historical_files = sorted(
        str(path.relative_to(root)) for path in historical_root.iterdir() if path.is_file()
    )
    historical_records = [
        {"path": path, "sha256": sha256_file(root / path)} for path in historical_files
    ]
    replay_capable_suffixes = (
        "predictions.jsonl",
        "case_ranks.csv",
        "outer_predictions.csv",
        "model_state_manifest.json",
        "replay_audit.json",
    )
    replay_capable_files = [
        path for path in historical_files if path.endswith(replay_capable_suffixes)
    ]
    compatibility_path = root / "docs/OPT_HISTORICAL_COMPATIBILITY_AUDIT.md"
    replay_results_path = root / "docs/OPT_HISTORICAL_REPLAY_RESULTS.md"
    compatibility = compatibility_path.read_text(encoding="utf-8")
    replay_results = replay_results_path.read_text(encoding="utf-8")
    no_class_a = "no historical candidate qualifies as a direct Class A replay" in compatibility
    byte_replay_unavailable = "exact byte-level canonical replay" in compatibility and "unavailable" in compatibility
    copied_read_only = "copied read-only" in replay_results
    recovered_status_supported = (
        no_class_a and byte_replay_unavailable and copied_read_only and not replay_capable_files
    )

    ranker_configs: Dict[str, Any] = {}
    selected_rankers: Set[str] = set()
    configs_consistent = True
    for dataset in DATASETS:
        config_path = root / f"artifacts/opt/o4_nested/{dataset}/config.json"
        trace_path = root / f"artifacts/opt/o4_nested/{dataset}/selection_trace.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        rankers = config["rankers"]
        dataset_status = {
            "Conditional Logit": (
                "EXECUTED" if rankers["R0-ConditionalLogit"]["available"] else "NOT EXECUTED"
            ),
            "XGBoost": (
                "EXECUTED"
                if rankers["R1-XGBoost"]["available"]
                else "NOT EXECUTED — DEPENDENCY UNAVAILABLE"
            ),
            "LightGBM": (
                "EXECUTED"
                if rankers["R2-LightGBM"]["available"]
                else "NOT EXECUTED — DEPENDENCY UNAVAILABLE"
            ),
        }
        configs_consistent = configs_consistent and dataset_status == {
            "Conditional Logit": "EXECUTED",
            "XGBoost": "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
            "LightGBM": "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
        }
        selected_rankers.update(_collect_rankers(trace))
        ranker_configs[dataset] = {
            "status": dataset_status,
            "config_path": str(config_path.relative_to(root)),
            "config_sha256": sha256_file(config_path),
            "selection_trace_path": str(trace_path.relative_to(root)),
            "selection_trace_sha256": sha256_file(trace_path),
        }
    only_conditional_logit_in_trace = selected_rankers == {"R0-ConditionalLogit"}
    legacy_unchanged = _matches_frozen_commit(root, "artifacts/opt/o1_historical")
    gate_pass = (
        recovered_status_supported
        and configs_consistent
        and only_conditional_logit_in_trace
        and legacy_unchanged
    )
    return {
        "schema_version": "ada_rca_provenance_normalization_v1_1",
        "audit_type": "PROVENANCE_AND_CLAIM_NORMALIZATION",
        "historical_reference": {
            "legacy_term": "HIST-BEST-REPLAYED-REFERENCE",
            "normalized_term": "HIST-BEST-RECOVERED-REFERENCE",
            "required_qualifier": (
                "Recovered legacy result; not canonically replayed; not an unbiased comparator."
            ),
            "status": "PASS" if recovered_status_supported else "FAIL",
            "evidence": {
                "no_direct_class_a_replay": no_class_a,
                "byte_level_canonical_replay_unavailable": byte_replay_unavailable,
                "summaries_copied_read_only": copied_read_only,
                "replay_capable_historical_files": replay_capable_files,
            },
            "source_records": historical_records,
            "legacy_artifacts_match_frozen_commit": legacy_unchanged,
        },
        "ranker_execution": {
            "canonical_status": {
                "Conditional Logit": "EXECUTED",
                "XGBoost": "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
                "LightGBM": "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
            },
            "selection_trace_rankers": sorted(selected_rankers),
            "only_conditional_logit_in_selection_trace": only_conditional_logit_in_trace,
            "dataset_records": ranker_configs,
        },
        "claim_boundary": {
            "historical_reference": "POST-HOC DESCRIPTIVE CONTEXT ONLY",
            "unavailable_rankers": "ABSENCE OF EXECUTION IS NOT A NEGATIVE PERFORMANCE RESULT",
            "optimization_scope": "LIMITED TO ACTUALLY EXECUTED CONDITIONAL-LOGIT SEARCH",
        },
        "gate_4": {
            "status": "PASS" if gate_pass else "FAIL",
            "final_decision_authorization": "GATE_5_AUTHORIZED" if gate_pass else "STOP",
            "terminal_state_if_failed": "RCA_EVIDENCE_NOT_CLOSED" if not gate_pass else None,
        },
    }
