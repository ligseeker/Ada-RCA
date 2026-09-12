#!/usr/bin/env python3
"""Audit the committed Ada-RCA Z2 archives without regenerating features."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.final_method import FINAL_Z2_FEATURE_ORDER_SHA256
from src.rca.supervised_baselines.common import (
    EXPECTED_CANDIDATES,
    EXPECTED_CASES,
    FROZEN_SHA256,
    sha256_file,
)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_identity():
    return {
        "commit": subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=str(PROJECT_ROOT), text=True
        ).strip(),
        "branch": subprocess.check_output(
            ("git", "branch", "--show-current"), cwd=str(PROJECT_ROOT), text=True
        ).strip(),
    }


def audit_dataset(dataset: str):
    feature_root = PROJECT_ROOT / "artifacts" / "features" / dataset
    registry = _read_json(PROJECT_ROOT / "artifacts" / "source" / dataset / "service_registry.json")
    candidates = tuple(str(value) for value in registry["services"])
    assignments = {
        str(row["case_id"]): int(row["fold"])
        for row in _read_json(PROJECT_ROOT / "artifacts" / "splits" / dataset / "assignments.json")
    }
    paths = tuple(sorted(feature_root.glob("*.npz")))
    if len(paths) != EXPECTED_CASES:
        raise ValueError("{} must contain exactly 90 feature archives".format(dataset))
    archive_hashes = {}
    case_ids = []
    for path in paths:
        with np.load(path) as data:
            case_id_values = tuple(str(value) for value in data["case_id"])
            event_candidates = tuple(str(value) for value in data["candidates"])
            base = np.asarray(data["base"], dtype=np.float64)
            morphology = np.asarray(data["z2"], dtype=np.float64)
        if case_id_values != (path.stem,):
            raise ValueError("filename and embedded case ID differ: {}".format(path))
        if path.stem not in assignments:
            raise ValueError("feature case is absent from frozen assignments: {}".format(path))
        if event_candidates != candidates:
            raise ValueError("candidate order differs from frozen registry: {}".format(path))
        expected_base = (len(candidates), 4, 8)
        expected_morphology = (len(candidates), 4, 9)
        if base.shape != expected_base or morphology.shape != expected_morphology:
            raise ValueError("Z1/Z2 block shape mismatch: {}".format(path))
        values = np.concatenate((base, morphology), axis=2).reshape(len(candidates), -1)
        if values.shape != (len(candidates), 68) or not np.all(np.isfinite(values)):
            raise ValueError("invalid frozen Z2 values: {}".format(path))
        case_ids.append(path.stem)
        archive_hashes[path.stem] = sha256_file(path)
    if set(case_ids) != set(assignments):
        raise ValueError("feature and assignment case universes differ")
    identity_lines = [
        "dataset={}".format(dataset),
        "feature_order_sha256={}".format(FINAL_Z2_FEATURE_ORDER_SHA256),
    ]
    identity_lines.extend(
        "{}={}".format(case_id, archive_hashes[case_id])
        for case_id in sorted(archive_hashes)
    )
    representation_checksum = hashlib.sha256(
        ("\n".join(identity_lines) + "\n").encode("utf-8")
    ).hexdigest()
    return {
        "dataset": dataset,
        "case_count": EXPECTED_CASES,
        "candidate_count": EXPECTED_CANDIDATES[dataset],
        "dimension": 68,
        "feature_order_sha256": FINAL_Z2_FEATURE_ORDER_SHA256,
        "feature_manifest_sha256": sha256_file(feature_root / "manifest.json"),
        "candidate_registry_sha256": sha256_file(
            PROJECT_ROOT / "artifacts" / "source" / dataset / "service_registry.json"
        ),
        "assignment_sha256": sha256_file(
            PROJECT_ROOT / "artifacts" / "splits" / dataset / "assignments.json"
        ),
        "expected_frozen_sha256": FROZEN_SHA256[dataset],
        "archive_sha256": archive_hashes,
        "representation_checksum": representation_checksum,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/z2_xgb_closure/representation_identity.json",
    )
    args = parser.parse_args()
    output = PROJECT_ROOT / args.output
    if output.exists():
        raise FileExistsError("identity artifact already exists: {}".format(output))
    datasets = {dataset: audit_dataset(dataset) for dataset in ("re2ob", "re2tt")}
    payload = {
        "schema_version": "z2_xgb_representation_identity_v1",
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": _git_identity(),
        "representation": "Ada-RCA frozen Z2 = base 32D + morphology 36D",
        "datasets": datasets,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "output": str(output),
        "representation_checksums": {
            dataset: value["representation_checksum"]
            for dataset, value in datasets.items()
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
