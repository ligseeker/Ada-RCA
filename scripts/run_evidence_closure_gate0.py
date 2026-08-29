#!/usr/bin/env python3
"""Generate the read-only Gate 0 frozen-evidence inventory."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rca.evidence_closure import build_input_manifest, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/evidence_closure/input_manifest.json",
    )
    args = parser.parse_args()
    manifest = build_input_manifest(ROOT)
    write_json(args.output, manifest)
    print(json.dumps(manifest["gate_0"], indent=2, sort_keys=True))
    return 0 if manifest["gate_0"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

