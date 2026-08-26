#!/usr/bin/env python3
"""Freeze the protocol's deterministic RE2-OB/RE2-TT three-fold OOF split."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_split(bundle: Path, output_root: Path, seed: int = 20260826):
    inputs = read_jsonl(bundle / "inputs.jsonl")
    labels = {row["case_id"]: row for row in read_jsonl(bundle / "labels.jsonl")}
    registry = json.loads((bundle / "service_registry.json").read_text(encoding="utf-8"))
    if len(inputs) != 90 or len(labels) != 90:
        raise ValueError("split requires exactly 90 cases and labels")
    assignments = []
    for row in sorted(inputs, key=lambda item: item["case_id"]):
        case_id = row["case_id"]
        label = labels[case_id]
        source_dir = next(path for path in read_jsonl(bundle / "sources.jsonl") if path["case_id"] == case_id)["relative_directory"]
        replicate = int(source_dir.rsplit("/", 1)[1])
        if replicate not in (1, 2, 3):
            raise ValueError("unexpected replicate {} for {}".format(replicate, case_id))
        assignments.append({
            "case_id": case_id,
            "fold": replicate - 1,
            "root_service": label["root_service"],
            "fault_type": label["fault_type"],
        })
    folds = {str(index): sorted((row for row in assignments if row["fold"] == index), key=lambda item: item["case_id"]) for index in range(3)}
    for index, rows in folds.items():
        if len(rows) != 30:
            raise ValueError("fold {} has {} cases, expected 30".format(index, len(rows)))
        strata = Counter((row["root_service"], row["fault_type"]) for row in rows)
        if len(strata) != 30 or any(value != 1 for value in strata.values()):
            raise ValueError("fold {} does not have one case per root x fault stratum".format(index))
    all_ids = [row["case_id"] for row in assignments]
    if len(set(all_ids)) != 90:
        raise ValueError("split assignments contain duplicate case IDs")
    output = output_root / bundle.name
    output.mkdir(parents=True, exist_ok=True)
    (output / "assignments.json").write_text(json.dumps(assignments, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    train_test = {
        str(index): {
            "test_case_ids": [row["case_id"] for row in folds[str(index)]],
            "train_case_ids": [row["case_id"] for row in assignments if row["fold"] != index],
        }
        for index in range(3)
    }
    (output / "folds.json").write_text(json.dumps(train_test, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "schema_version": "p3_a0_three_fold_split_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "dataset": bundle.name,
        "case_count": 90,
        "candidate_count": len(registry["services"]),
        "fold_count": 3,
        "fold_sizes": {key: len(value) for key, value in folds.items()},
        "train_sizes": {key: 60 for key in folds},
        "seed": seed,
        "assignment_rule": "within each root x fault stratum, repetition 1 -> fold 0, repetition 2 -> fold 1, repetition 3 -> fold 2",
        "source_manifest_sha256": sha256(bundle / "manifest.json"),
        "assignments_sha256": sha256(output / "assignments.json"),
        "folds_sha256": sha256(output / "folds.json"),
        "root_fault_per_fold": {
            key: {"{}|{}".format(root, fault): count for (root, fault), count in sorted(Counter((row["root_service"], row["fault_type"]) for row in value).items())}
            for key, value in folds.items()
        },
        "passed": True,
    }
    (output / "split_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / (bundle.name + "_3fold.json")).write_text(
        json.dumps({"split_manifest": summary, "assignments": assignments, "folds": train_test}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default="artifacts/source")
    parser.add_argument("--output-root", default="artifacts/splits")
    parser.add_argument("--seed", type=int, default=20260826)
    args = parser.parse_args()
    source_root = PROJECT_ROOT / args.source_root
    output_root = PROJECT_ROOT / args.output_root
    summaries = {key: build_split(source_root / key, output_root, args.seed) for key in ("re2ob", "re2tt")}
    (output_root / "split_summary.json").write_text(json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: {"fold_sizes": value["fold_sizes"], "passed": value["passed"]} for key, value in summaries.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
