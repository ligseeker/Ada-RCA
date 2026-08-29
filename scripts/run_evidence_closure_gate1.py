#!/usr/bin/env python3
"""Run independent frozen root-rank metric reconstruction for Gate 1."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rca.evidence_closure import build_metric_reconstruction, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/evidence_closure/metric_reconstruction_v1_1.json",
    )
    args = parser.parse_args()
    result = build_metric_reconstruction(ROOT)
    write_json(args.output, result)
    print(json.dumps(result["gate_1"], indent=2, sort_keys=True))
    return 0 if result["gate_1"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
