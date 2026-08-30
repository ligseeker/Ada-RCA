#!/usr/bin/env python3
"""Generate the final limitation-qualified RCA evidence decision."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rca.evidence_closure import write_json
from src.rca.evidence_final import build_final_evidence_decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/evidence_closure/final_decision_v1_1.json",
    )
    args = parser.parse_args()
    result = build_final_evidence_decision(ROOT)
    write_json(args.output, result)
    print(json.dumps({"final_decision": result["final_decision"], "conditions": result["conditions"]}, indent=2, sort_keys=True))
    return 0 if result["final_decision"] == "RCA_FREEZE_READY_WITH_LIMITATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
