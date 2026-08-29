#!/usr/bin/env python3
"""Run static audits and smoke qualification for the frozen Tier-A baselines."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.p6_e4 import assert_baseline_branch
from src.rca.p6_baselines import write_static_semantic_audits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
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
    write_static_semantic_audits(args.output_root, args.rcaeval_root.resolve())
    if not args.audit_only:
        raise RuntimeError("smoke execution is not enabled until static audits are committed")
    print("P6-E4 static semantic audits generated; no Tier-A callable invoked")


if __name__ == "__main__":
    main()
