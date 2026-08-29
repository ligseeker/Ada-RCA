#!/usr/bin/env python3
"""Generate the read-only frozen Trace Error Z2 invariant artifact."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rca.evidence_closure import write_json
from src.rca.evidence_trace_error import build_trace_error_representation_invariant


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT
            / "artifacts/evidence_closure/trace_error_representation_invariant.json"
        ),
    )
    args = parser.parse_args()
    result = build_trace_error_representation_invariant(ROOT)
    write_json(args.output, result)
    print(
        json.dumps(
            {
                "datasets": {
                    name: {
                        "rows": value["total_candidate_case_rows"],
                        "unique_vectors": value["unique_trace_error_vectors"],
                        "discriminative_cases": value[
                            "within_case_candidate_discriminative_variation"
                        ]["case_count"],
                    }
                    for name, value in result["datasets"].items()
                },
                "final_classification": result["final_classification"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
