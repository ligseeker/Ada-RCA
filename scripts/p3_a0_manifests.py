#!/usr/bin/env python3
"""Create P3-A0 label-separated manifests and canonical service registries."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.rcaeval import RE2OB, RE2TT, load_cases


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(_json(row) + "\n")


def build_manifest(profile, output_root: Path):
    result = load_cases(profile)
    by_id = {label.case_id: label for label in result.labels}
    source_by_id = {source.case_id: source for source in result.sources}
    registry = sorted({service for case in result.inputs for service in case.services})
    dataset_root = Path(profile.root_path)
    output = output_root / profile.key
    output.mkdir(parents=True, exist_ok=True)

    input_rows = []
    label_rows = []
    source_rows = []
    for case in result.inputs:
        label = by_id[case.case_id]
        source = source_by_id[case.case_id]
        input_rows.append({
            "case_id": case.case_id,
            "dataset": case.dataset,
            "anchor_time": int(case.anchor_time),
            "candidates": list(case.services),
            "metrics": case.metrics.__dict__ if case.metrics else None,
            "logs": case.logs.__dict__ if case.logs else None,
            "traces": case.traces.__dict__ if case.traces else None,
            "metadata": dict(case.metadata),
        })
        label_rows.append({"case_id": label.case_id, "root_service": label.root_service, "fault_type": label.fault_type})
        source_rows.append({**source.__dict__, "source_root": str(dataset_root)})

    write_jsonl(output / "inputs.jsonl", input_rows)
    write_jsonl(output / "labels.jsonl", label_rows)
    write_jsonl(output / "sources.jsonl", source_rows)
    (output / "service_registry.json").write_text(
        json.dumps({
            "schema_version": "p3_a0_service_registry_v1",
            "dataset": profile.dataset,
            "dataset_key": profile.key,
            "derivation": "union of simple_metrics CPU/memory entity columns, excluding fixed auxiliary entities",
            "label_free": True,
            "services": registry,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = {}
    for path in sorted(output.iterdir()):
        if path.is_file():
            files[path.name] = {"bytes": path.stat().st_size, "sha256": _digest(path)}
    manifest = {
        "schema_version": "p3_a0_manifest_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "dataset": profile.dataset,
        "dataset_key": profile.key,
        "source_root": str(dataset_root),
        "case_count": len(result.inputs),
        "excluded_count": len(result.excluded),
        "candidate_count": len(registry),
        "candidate_registry": registry,
        "files": files,
        "label_sidecar_only": True,
        "input_forbidden_fields": ["root_service", "fault_type", "relative_directory", "source_path", "injection_target"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="artifacts/source")
    args = parser.parse_args()
    root = PROJECT_ROOT / args.output_root
    summaries = {profile.key: build_manifest(profile, root) for profile in (RE2OB, RE2TT)}
    print(json.dumps({key: {"cases": value["case_count"], "candidates": value["candidate_count"]} for key, value in summaries.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
