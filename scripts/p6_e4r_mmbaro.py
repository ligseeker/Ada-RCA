#!/usr/bin/env python3
"""Run the human-authorized official-RE2 mmBARO integration smoke only."""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.p6_e4 import assert_baseline_branch, write_json
from src.rca.p6_baselines import (
    build_mmbaro_input_dictionary_audit,
    load_clean_source_module,
    run_mmbaro_smoke,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rcaeval-root", type=Path, default=Path("/home/zhangll24/RCA_project/RCAEval-clean"))
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "artifacts" / "p6_e4r")
    args = parser.parse_args()
    assert_baseline_branch(PROJECT_ROOT)
    rcaeval_root = args.rcaeval_root.resolve()
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "mmbaro").mkdir(parents=True, exist_ok=True)
    source = rcaeval_root / "RCAEval/e2e/baro.py"
    write_json(args.output_root / "mmbaro" / "input_dictionary_audit.json", build_mmbaro_input_dictionary_audit(source))
    write_json(args.output_root / "mmbaro" / "dataset_alias_audit.json", {
        "schema_version": "p6_e4r_mmbaro_dataset_alias_audit_v1",
        "official_dataset_identifiers": ["re2-ob", "re2-tt"],
        "rejected_aliases": {"re2-ob": "mm-ob", "re2-tt": "mm-tt"},
        "alias_used": False,
        "decision_basis": "human resolution rejected unsupported aliases; official code and path semantics only",
        "performance_evidence_used": False,
        "status": "OFFICIAL_RE2_IDENTIFIERS_FROZEN",
    })
    write_json(args.output_root / "mmbaro" / "modality_activation_audit.json", {
        "schema_version": "p6_e4r_mmbaro_modality_activation_audit_v1",
        "dataset_identifiers": ["re2-ob", "re2-tt"],
        "active_score_modalities": ["metric", "log_time_series"],
        "trace_error_time_series": "NOT_USED_BY_SCORE",
        "trace_latency_time_series": "NOT_USED_BY_SCORE",
        "raw_logs": "NOT_USED_BY_SCORE",
        "raw_spans": "NOT_USED_BY_SCORE",
        "cluster_info": "NOT_USED_BY_SCORE",
        "trace_branches_active": False,
        "tri_modal_claim_permitted": False,
    })
    summary = run_mmbaro_smoke(args.output_root, rcaeval_root)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
