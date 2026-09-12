#!/usr/bin/env python3
"""Create the frozen, label-blind raw-source/FDG audit for DejaVu."""

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import FROZEN_SHA256, read_json, sha256_file, write_json
from src.rca.supervised_baselines.dejavu_adapter import audit_source_registry


OFFICIAL_DEJAVU_COMMIT = "d1f082b086cef5597f5301a7b02882b5d0238ebe"
EXPECTED_CANDIDATES = {"re2ob": 11, "re2tt": 68}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=("re2ob", "re2tt"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--output-root",
        default="artifacts/supervised_baselines/dejavu/source_audit",
    )
    args = parser.parse_args()

    source_dir = PROJECT_ROOT / "artifacts" / "source" / args.dataset
    sources_path = source_dir / "sources.jsonl"
    registry_path = source_dir / "service_registry.json"
    source_manifest = read_json(source_dir / "manifest.json")
    if sha256_file(sources_path) != source_manifest["files"]["sources.jsonl"]["sha256"]:
        raise ValueError("sources.jsonl differs from its committed source manifest")
    if sha256_file(registry_path) != FROZEN_SHA256[args.dataset]["candidate_registry"]:
        raise ValueError("candidate registry differs from the supervised protocol freeze")

    result = dict(
        audit_source_registry(
            sources_path,
            registry_path,
            args.dataset,
            expected_cases=90,
            workers=args.workers,
        )
    )
    if result["candidate_count"] != EXPECTED_CANDIDATES[args.dataset]:
        raise ValueError("candidate count differs from the supervised protocol")
    result["official_dejavu_commit"] = OFFICIAL_DEJAVU_COMMIT
    result["adapter_protocol"] = {
        "path": "docs/supervised_baselines/DEJAVU_ADAPTER_PROTOCOL_V1.md",
        "sha256": sha256_file(
            PROJECT_ROOT / "docs" / "supervised_baselines" / "DEJAVU_ADAPTER_PROTOCOL_V1.md"
        ),
    }

    output_path = PROJECT_ROOT / args.output_root / args.dataset / "source_audit.json"
    write_json(output_path, result)
    print(json.dumps({
        "status": result["status"],
        "dataset": args.dataset,
        "case_count": result["case_count"],
        "union_edge_count": len(result["union_edges"]),
        "failure_count": len(result["failures"]),
        "output": str(output_path),
    }, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
