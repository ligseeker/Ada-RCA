#!/usr/bin/env python3
"""Prepare label-free metric tensors and source-FDG specs for DejaVu."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import read_json, sha256_file, write_json
from src.rca.supervised_baselines.dejavu_adapter import build_graph_spec, prepare_metric_tensor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=("re2ob", "re2tt"))
    parser.add_argument(
        "--source-audit-root",
        default="artifacts/supervised_baselines/dejavu/source_audit_a2",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/supervised_baselines/dejavu/prepared",
    )
    args = parser.parse_args()

    source_dir = PROJECT_ROOT / "artifacts" / "source" / args.dataset
    source_rows = {
        row["case_id"]: row
        for row in (
            json.loads(line)
            for line in (source_dir / "sources.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    candidate_path = source_dir / "service_registry.json"
    candidates = tuple(str(value) for value in read_json(candidate_path)["services"])
    audit_path = PROJECT_ROOT / args.source_audit_root / args.dataset / "source_audit.json"
    audit = read_json(audit_path)
    if audit["status"] != "PASS" or audit["dataset"] != args.dataset:
        raise ValueError("source audit is not a PASS for this dataset")
    if audit["source_registry"]["sha256"] != sha256_file(source_dir / "sources.jsonl"):
        raise ValueError("source registry differs from source audit")
    if audit["candidate_registry"]["sha256"] != sha256_file(candidate_path):
        raise ValueError("candidate registry differs from source audit")
    if set(source_rows) != {case["case_id"] for case in audit["cases"]}:
        raise ValueError("source audit and source registry case universes differ")

    output_dir = PROJECT_ROOT / args.output_root / args.dataset
    if output_dir.exists():
        raise FileExistsError("prepared output is create-once: {}".format(output_dir))
    output_dir.mkdir(parents=True)
    files = []
    edge_counts = []
    for case_audit in sorted(audit["cases"], key=lambda row: row["case_id"]):
        case_id = str(case_audit["case_id"])
        tensor = prepare_metric_tensor(source_rows[case_id], candidates)
        graph = build_graph_spec(candidates, case_audit["edges"])
        path = output_dir / "{}.npz".format(case_id)
        np.savez_compressed(
            path,
            case_id=np.asarray([case_id]),
            candidates=np.asarray(candidates),
            metric_tensor=tensor,
            source_indices=np.asarray(graph["source_indices"], dtype=np.int64),
            destination_indices=np.asarray(graph["destination_indices"], dtype=np.int64),
        )
        edge_counts.append(len(graph["source_indices"]))
        files.append({
            "case_id": case_id,
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "metric_shape": list(tensor.shape),
            "source_edge_count": len(graph["source_indices"]),
            "node_count": graph["node_count"],
        })

    manifest = {
        "schema_version": "dejavu_re2_prepared_v1",
        "status": "PASS",
        "dataset": args.dataset,
        "label_free": True,
        "forbidden_fields": ["root_service", "fault_type", "condition"],
        "case_count": len(files),
        "candidate_count": len(candidates),
        "candidates": list(candidates),
        "metric_order": ["cpu", "mem"],
        "metric_shape_per_case": [len(candidates), 2, 20],
        "source_graph_semantics": "directed_trace_parent_service_to_child_service",
        "source_audit": {
            "path": str(audit_path.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(audit_path),
        },
        "adapter_protocol_sha256": sha256_file(
            PROJECT_ROOT / "docs" / "supervised_baselines" / "DEJAVU_ADAPTER_PROTOCOL_V1.md"
        ),
        "source_edge_count_min": min(edge_counts),
        "source_edge_count_max": max(edge_counts),
        "files": files,
    }
    write_json(output_dir / "manifest.json", manifest)
    print(json.dumps({
        "status": manifest["status"],
        "dataset": args.dataset,
        "case_count": manifest["case_count"],
        "metric_shape": manifest["metric_shape_per_case"],
        "source_edge_count_min": manifest["source_edge_count_min"],
        "source_edge_count_max": manifest["source_edge_count_max"],
        "output": str(output_dir),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
