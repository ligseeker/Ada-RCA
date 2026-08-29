#!/usr/bin/env python3
"""Generate the P6-E4 artifacts that must precede Tier-A invocation."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.p6_e4 import (
    DATASETS,
    assert_baseline_branch,
    build_all_case_schema_audit,
    build_smoke_manifest,
    build_upstream_provenance,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
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
    provenance = build_upstream_provenance(args.rcaeval_root.resolve())
    manifest = build_smoke_manifest(DATASETS)
    write_json(args.output_root / "upstream_provenance.json", provenance)
    write_json(args.output_root / "smoke_case_manifest.json", manifest)
    schema_audit = build_all_case_schema_audit(DATASETS)
    write_json(args.output_root / "all_case_schema_audit.json", schema_audit)
    print("P6-E4 pre-invocation artifacts generated for 180 cases")


if __name__ == "__main__":
    main()
