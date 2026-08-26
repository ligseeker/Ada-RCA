#!/usr/bin/env python3
"""Validate P3-A0 input/label separation and candidate completeness."""

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def audit_bundle(bundle: Path):
    inputs = read_jsonl(bundle / "inputs.jsonl")
    labels = read_jsonl(bundle / "labels.jsonl")
    sources = read_jsonl(bundle / "sources.jsonl")
    registry = json.loads((bundle / "service_registry.json").read_text(encoding="utf-8"))
    input_ids = [row["case_id"] for row in inputs]
    label_ids = [row["case_id"] for row in labels]
    source_ids = [row["case_id"] for row in sources]
    forbidden = ("root_service", "fault_type", "relative_directory", "metrics_path", "source_root", "injection_target")
    serialized_inputs = (bundle / "inputs.jsonl").read_text(encoding="utf-8")
    forbidden_hits = {token: serialized_inputs.count(token) for token in forbidden}
    roots = {row["root_service"] for row in labels}
    candidate_sets = {tuple(row["candidates"]) for row in inputs}
    root_violations = [row["case_id"] for row in labels if row["root_service"] not in registry["services"]]
    candidate_violations = [row["case_id"] for row in inputs if tuple(row["candidates"]) != tuple(registry["services"])]
    report = {
        "bundle": str(bundle),
        "cases": len(inputs),
        "unique_input_ids": len(set(input_ids)) == len(input_ids),
        "input_label_source_ids_match": set(input_ids) == set(label_ids) == set(source_ids),
        "input_forbidden_token_hits": forbidden_hits,
        "label_free_input_pass": all(value == 0 for value in forbidden_hits.values()),
        "registry_label_free_derivation": bool(registry.get("label_free")),
        "registry_count": len(registry["services"]),
        "candidate_set_count": len(candidate_sets),
        "candidate_completeness_pass": not candidate_violations,
        "root_registry_violations": root_violations,
        "candidate_registry_violations": candidate_violations,
        "fault_counts": dict(sorted(Counter(row["fault_type"] for row in labels).items())),
        "root_counts": dict(sorted(Counter(row["root_service"] for row in labels).items())),
        "passed": (
            len(inputs) == 90 and len(set(input_ids)) == 90
            and set(input_ids) == set(label_ids) == set(source_ids)
            and all(value == 0 for value in forbidden_hits.values())
            and not root_violations and not candidate_violations
        ),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default="artifacts/source")
    args = parser.parse_args()
    root = PROJECT_ROOT / args.source_root
    report = {key: audit_bundle(root / key) for key in ("re2ob", "re2tt")}
    output = root / "p3_a0_audit.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not all(row["passed"] for row in report.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
