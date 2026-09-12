#!/usr/bin/env python3
"""Validate the frozen Z2-XGB closure artifacts and deterministic replay."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import (
    EXPECTED_CANDIDATES,
    SEED,
    sha256_file,
)
from src.rca.supervised_baselines.xgb_ranker import XGB_CONFIG
from src.rca.supervised_baselines.z2_xgb_ranker import Z2_XGB_CONFIG


DATASETS = ("re2ob", "re2tt")
FOLDS = (0, 1, 2)
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "z2_xgb_closure"
FORMAL_ROOT = ARTIFACT_ROOT / "z2_xgb"
REPLAY_ROOT = ARTIFACT_ROOT / "replay_check"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def verify_checksums(directory):
    checksums = read_json(directory / "checksums.json")
    actual_files = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path.name != "checksums.json"
    }
    if set(checksums) != actual_files:
        raise ValueError("checksum file set mismatch: {}".format(directory))
    for relative, expected in checksums.items():
        actual = sha256_file(directory / relative)
        if actual != expected:
            raise ValueError("checksum mismatch: {}".format(directory / relative))


def assert_equal(left, right, message):
    if left != right:
        raise ValueError(message + ": {} != {}".format(left, right))


def expected_config():
    expected = dict(Z2_XGB_CONFIG)
    for key, value in XGB_CONFIG.items():
        if key not in ("method", "input"):
            expected[key] = value
    return expected


def load_candidates(dataset):
    registry = read_json(
        PROJECT_ROOT / "artifacts" / "source" / dataset / "service_registry.json"
    )
    candidates = tuple(str(value) for value in registry["services"])
    assert_equal(
        len(candidates),
        EXPECTED_CANDIDATES[dataset],
        "candidate count mismatch for {}".format(dataset),
    )
    return candidates


def validate_prediction_rows(path, dataset, expected_case_count):
    candidates = load_candidates(dataset)
    rows = read_jsonl(path)
    expected_rows = expected_case_count * len(candidates)
    assert_equal(len(rows), expected_rows, "prediction row count mismatch")
    by_case = {}
    for row in rows:
        case_id = str(row["case_id"])
        by_case.setdefault(case_id, []).append(row)
        if row["dataset"] != dataset:
            raise ValueError("dataset mismatch in prediction row")
        if not np.isfinite(float(row["score"])):
            raise ValueError("non-finite prediction score")
    assert_equal(len(by_case), expected_case_count, "prediction case count mismatch")
    for case_id, case_rows in by_case.items():
        ordered = sorted(case_rows, key=lambda row: int(row["rank"]))
        assert_equal(
            tuple(row["rank"] for row in ordered),
            tuple(range(1, len(candidates) + 1)),
            "rank permutation mismatch for {}".format(case_id),
        )
        assert_equal(
            tuple(row["candidate"] for row in ordered),
            tuple(dict.fromkeys(row["candidate"] for row in ordered)),
            "duplicate candidate in {}".format(case_id),
        )
        assert_equal(
            set(row["candidate"] for row in ordered),
            set(candidates),
            "candidate registry mismatch for {}".format(case_id),
        )
        roots = {row["root_service"] for row in ordered}
        root_ranks = {int(row["root_rank"]) for row in ordered}
        assert_equal(len(roots), 1, "root identity mismatch for {}".format(case_id))
        assert_equal(len(root_ranks), 1, "root rank mismatch for {}".format(case_id))
        root = next(iter(roots))
        if sum(row["candidate"] == root for row in ordered) != 1:
            raise ValueError("root is not present exactly once: {}".format(case_id))


def validate_fold(dataset, fold):
    directory = FORMAL_ROOT / dataset / "fold_{}".format(fold)
    verify_checksums(directory)
    status = read_json(directory / "status.json")
    assert_equal(status["status"], "COMPLETE", "formal fold is not complete")
    assert_equal(read_json(directory / "config.json"), expected_config(), "config mismatch")
    environment = read_json(directory / "environment.json")
    expected_environment = {
        "PYTHONHASHSEED": str(SEED),
        "python": "3.8.20",
        "numpy": "1.24.1",
        "pandas": "1.5.3",
        "scipy": "1.10.1",
        "scikit_learn": "1.2.1",
        "xgboost": "2.1.4",
        "representation": "frozen Z2",
        "representation_dimension": 68,
    }
    for key, value in expected_environment.items():
        assert_equal(environment.get(key), value, "environment mismatch for {}".format(key))
    firewall = read_json(directory / "label_firewall.json")
    for key, value in {
        "status": "PASS",
        "train_case_count": 60,
        "test_case_count": 30,
        "train_test_overlap": [],
        "predict_interface_label_free": True,
        "test_labels_joined_after_prediction": True,
    }.items():
        assert_equal(firewall.get(key), value, "firewall mismatch for {}".format(key))
    integrity = read_json(directory / "integrity.json")
    for key, value in {
        "status": "PASS",
        "case_count": 30,
        "candidate_row_count": 30 * EXPECTED_CANDIDATES[dataset],
        "expected_candidate_row_count": 30 * EXPECTED_CANDIDATES[dataset],
        "complete_candidate_rows": True,
        "complete_rank_permutations": True,
        "root_present_exactly_once_per_case": True,
    }.items():
        assert_equal(integrity.get(key), value, "integrity mismatch for {}".format(key))
    validate_prediction_rows(directory / "predictions.jsonl", dataset, 30)
    metrics = read_json(directory / "metrics.json")
    assert_equal(len(metrics["case_metrics"]), 30, "fold metric case count mismatch")
    provenance = read_json(directory / "provenance.json")
    assert_equal(provenance["method"], "z2_xgb", "fold method mismatch")
    assert_equal(provenance["dataset"], dataset, "fold dataset mismatch")
    assert_equal(provenance["fold"], fold, "fold identity mismatch")
    return {
        "dataset": dataset,
        "fold": fold,
        "source_commit": provenance["source_commit"],
        "candidate_rows": integrity["candidate_row_count"],
        "case_count": integrity["case_count"],
        "status": "PASS",
    }


def validate_aggregate(dataset):
    directory = FORMAL_ROOT / dataset / "aggregate"
    verify_checksums(directory)
    integrity = read_json(directory / "integrity.json")
    expected_rows = 90 * EXPECTED_CANDIDATES[dataset]
    for key, value in {
        "status": "PASS",
        "case_count": 90,
        "candidate_row_count": expected_rows,
        "expected_candidate_row_count": expected_rows,
        "complete_candidate_rankings": True,
        "folds": [0, 1, 2],
    }.items():
        assert_equal(integrity.get(key), value, "aggregate integrity mismatch for {}".format(key))
    validate_prediction_rows(directory / "predictions.jsonl", dataset, 90)
    metrics = read_json(directory / "metrics.json")
    assert_equal(len(metrics["case_metrics"]), 90, "aggregate metric case count mismatch")
    return {"dataset": dataset, "case_count": 90, "candidate_rows": expected_rows, "status": "PASS"}


def compare_replay():
    formal = FORMAL_ROOT / "re2ob" / "fold_0"
    replay = REPLAY_ROOT / "z2_xgb" / "re2ob" / "fold_0"
    verify_checksums(replay)
    assert_equal(read_json(replay / "status.json")["status"], "COMPLETE", "replay is not complete")
    exact_files = (
        "config.json",
        "environment.json",
        "integrity.json",
        "metrics.json",
        "model_state.ubj",
        "predictions.jsonl",
    )
    exact = {}
    for name in exact_files:
        exact[name] = sha256_file(formal / name) == sha256_file(replay / name)
        if not exact[name]:
            raise ValueError("deterministic replay mismatch: {}".format(name))
    formal_firewall = read_json(formal / "label_firewall.json")
    replay_firewall = read_json(replay / "label_firewall.json")
    formal_firewall.pop("prediction_completed_at", None)
    replay_firewall.pop("prediction_completed_at", None)
    firewall_equal = formal_firewall == replay_firewall
    if not firewall_equal:
        raise ValueError("deterministic replay firewall mismatch")
    return {
        "status": "PASS",
        "formal_fold": "z2_xgb/re2ob/fold_0",
        "replay_fold": "replay_check/z2_xgb/re2ob/fold_0",
        "exact_sha256_matches": exact,
        "firewall_equal_after_timestamp_normalization": firewall_equal,
        "timestamps_and_runtime_excluded": True,
    }


def current_identity():
    return {
        "commit": subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=str(PROJECT_ROOT), text=True
        ).strip(),
        "branch": subprocess.check_output(
            ("git", "branch", "--show-current"), cwd=str(PROJECT_ROOT), text=True
        ).strip(),
    }


def main():
    identity = read_json(ARTIFACT_ROOT / "representation_identity.json")
    assert_equal(identity["status"], "PASS", "representation identity is not PASS")
    for dataset in DATASETS:
        assert_equal(identity["datasets"][dataset]["dimension"], 68, "Z2 dimension mismatch")
        assert_equal(
            identity["datasets"][dataset]["candidate_count"],
            EXPECTED_CANDIDATES[dataset],
            "identity candidate count mismatch",
        )

    folds = [validate_fold(dataset, fold) for dataset in DATASETS for fold in FOLDS]
    aggregates = [validate_aggregate(dataset) for dataset in DATASETS]
    replay = compare_replay()
    validation = {
        "schema_version": "z2_xgb_closure_validation_v1",
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": current_identity(),
        "protocol": "docs/z2_xgb_closure/Z2_XGB_CLOSURE_PROTOCOL_V1.md",
        "representation_identity": "artifacts/z2_xgb_closure/representation_identity.json",
        "scorer_config": expected_config(),
        "folds": folds,
        "aggregates": aggregates,
        "deterministic_replay": replay,
    }
    output = ARTIFACT_ROOT / "validation.json"
    output.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
