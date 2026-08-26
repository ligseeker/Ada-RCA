#!/usr/bin/env python3
"""Extract the frozen P3-A0.5 representation without reading labels."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.features import CHANNELS, extract_case_features
from src.rca.rcaeval import CaseSource


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def source_from_row(row):
    fields = {key: row[key] for key in CaseSource.__dataclass_fields__ if key in row}
    return CaseSource(**fields)


def extract_dataset(key: str, source_root: Path, output_root: Path):
    bundle = source_root / key
    inputs = read_jsonl(bundle / "inputs.jsonl")
    sources = {row["case_id"]: source_from_row(row) for row in read_jsonl(bundle / "sources.jsonl")}
    dataset_output = output_root / key
    dataset_output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index, row in enumerate(sorted(inputs, key=lambda item: item["case_id"]), start=1):
        features = extract_case_features(
            row["case_id"], tuple(row["candidates"]), float(row["anchor_time"]), sources[row["case_id"]]
        )
        path = dataset_output / (row["case_id"] + ".npz")
        np.savez_compressed(
            path,
            case_id=np.asarray([features.case_id]),
            candidates=np.asarray(features.candidates),
            a=features.a,
            base=features.base,
            z=features.z,
            q_mask=features.q_mask,
            morphology_active=features.morphology_active,
            z2=features.z2,
            z3=features.z3,
        )
        summaries.append({
            "case_id": features.case_id,
            "candidate_count": len(features.candidates),
            "a_min": float(np.min(features.a)),
            "a_max": float(np.max(features.a)),
            "base_shape": list(features.base.shape),
            "z_shape": list(features.z.shape),
            "q_observed_ratio": float(np.mean(features.q_mask)),
            "channel_available_ratio": float(np.mean(features.base[:, :, 7])),
            "morphology_active_ratio": float(np.mean(features.morphology_active)),
            "finite": bool(np.isfinite(features.a).all() and np.isfinite(features.base).all() and np.isfinite(features.z).all()),
            "artifact": str(path.relative_to(PROJECT_ROOT)),
        })
        if index % 15 == 0:
            print("{} {}/{}".format(key, index, len(inputs)), flush=True)
    report = {
        "schema_version": "p3_a05_feature_manifest_v1",
        "dataset": key,
        "case_count": len(summaries),
        "channels": list(CHANNELS),
        "grid_bins": 80,
        "bin_seconds": 15,
        "z3_total_dimension": 676,
        "finite_all_cases": all(row["finite"] for row in summaries),
        "candidate_count_distribution": dict(sorted(Counter(row["candidate_count"] for row in summaries).items())),
        "q_observed_ratio": {
            "min": min(row["q_observed_ratio"] for row in summaries),
            "max": max(row["q_observed_ratio"] for row in summaries),
            "mean": float(np.mean([row["q_observed_ratio"] for row in summaries])),
        },
        "channel_available_ratio": {
            "min": min(row["channel_available_ratio"] for row in summaries),
            "max": max(row["channel_available_ratio"] for row in summaries),
            "mean": float(np.mean([row["channel_available_ratio"] for row in summaries])),
        },
        "morphology_active_ratio": {
            "min": min(row["morphology_active_ratio"] for row in summaries),
            "max": max(row["morphology_active_ratio"] for row in summaries),
            "mean": float(np.mean([row["morphology_active_ratio"] for row in summaries])),
        },
        "cases": summaries,
    }
    (dataset_output / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default="artifacts/source")
    parser.add_argument("--output-root", default="artifacts/features")
    args = parser.parse_args()
    started = time.time()
    source_root = PROJECT_ROOT / args.source_root
    output_root = PROJECT_ROOT / args.output_root
    report = {key: extract_dataset(key, source_root, output_root) for key in ("re2ob", "re2tt")}
    final = {"schema_version": "p3_a05_extraction_audit_v1", "elapsed_seconds": time.time() - started, "datasets": report}
    (output_root / "p3_a05_audit.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: {"cases": value["case_count"], "finite": value["finite_all_cases"], "q_ratio": value["q_observed_ratio"]} for key, value in report.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
