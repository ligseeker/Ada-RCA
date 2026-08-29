#!/usr/bin/env python3
"""Generate the canonical Gate 5 evidence-semantic correction layer."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rca.evidence_closure import write_json
from src.rca.evidence_semantics import build_evidence_semantic_correction


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT
            / "artifacts/evidence_closure/evidence_semantic_correction_v1_1.json"
        ),
    )
    args = parser.parse_args()
    result = build_evidence_semantic_correction(ROOT)
    write_json(args.output, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["genuine_fail_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
