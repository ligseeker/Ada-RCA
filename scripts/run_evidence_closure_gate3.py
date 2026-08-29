#!/usr/bin/env python3
"""Run the candidate-case telemetry information-loss audit for Gate 3."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rca.evidence_closure import write_json
from src.rca.evidence_telemetry import build_telemetry_information_loss_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/evidence_closure/telemetry_information_loss_v1_1.json",
    )
    args = parser.parse_args()
    result = build_telemetry_information_loss_audit(ROOT)
    write_json(args.output, result)
    print(json.dumps(result["gate_3"], indent=2, sort_keys=True))
    return 0 if result["gate_3"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
