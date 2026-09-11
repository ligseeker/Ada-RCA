#!/usr/bin/env python3
"""Aggregate completed folds or evaluate the preregistered DejaVu gate."""

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.aggregate import (
    METHODS,
    aggregate_method_dataset,
    evaluate_dejavu_gate,
    persist_dejavu_gate,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--dataset", choices=("re2ob", "re2tt"))
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--output-root", default="artifacts/supervised_baselines")
    args = parser.parse_args()
    artifact_root = PROJECT_ROOT / args.output_root
    if args.gate:
        if args.method is not None or args.dataset is not None:
            parser.error("--gate cannot be combined with --method/--dataset")
        gate = evaluate_dejavu_gate(PROJECT_ROOT, artifact_root)
        path = persist_dejavu_gate(artifact_root, gate)
        print(json.dumps({"gate": gate, "artifact": str(path)}, indent=2, sort_keys=True))
        return
    if args.method is None or args.dataset is None:
        parser.error("--method and --dataset are required unless --gate is used")
    result = aggregate_method_dataset(PROJECT_ROOT, artifact_root, args.method, args.dataset)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
