#!/usr/bin/env python3
"""Run static audits and smoke qualification for the frozen Tier-A baselines."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.p6_e4 import assert_baseline_branch
from src.rca.p6_baselines import (
    blocked_mmbaro_summary,
    run_baro_smoke,
    run_tracerca_smoke,
    write_overall_qualification,
    write_static_semantic_audits,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--audit-only", action="store_true")
    modes.add_argument("--run-smoke", action="store_true")
    parser.add_argument(
        "--rcaeval-root",
        type=Path,
        default=Path("/home/zhangll24/RCA_project/RCAEval-clean"),
    )
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "artifacts" / "p6_e4"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assert_baseline_branch(PROJECT_ROOT)
    if args.audit_only:
        write_static_semantic_audits(args.output_root, args.rcaeval_root.resolve())
        print("P6-E4 static semantic audits generated; no Tier-A callable invoked")
        return
    baro = run_baro_smoke(args.output_root, args.rcaeval_root.resolve())
    tracerca = run_tracerca_smoke(args.output_root, args.rcaeval_root.resolve())
    mmbaro = blocked_mmbaro_summary(args.output_root)
    overall = write_overall_qualification(args.output_root, baro, tracerca, mmbaro)
    print(overall["p6_g1"])


if __name__ == "__main__":
    main()
