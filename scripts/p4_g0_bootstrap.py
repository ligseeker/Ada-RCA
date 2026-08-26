#!/usr/bin/env python3
"""Bootstrap skeleton for frozen P4-G0 paired case-level comparisons."""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.p4_stats import paired_fault_stratified_bootstrap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    left_rows = {row["case_id"]: row for row in (json.loads(line) for line in Path(args.left).read_text().splitlines() if line.strip())}
    right_rows = {row["case_id"]: row for row in (json.loads(line) for line in Path(args.right).read_text().splitlines() if line.strip())}
    result = paired_fault_stratified_bootstrap(left_rows, right_rows)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
