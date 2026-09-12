"""Shared, fail-closed data and artifact helpers for supervised baselines."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np

from ..features import CHANNELS, N_BINS
from ..evaluator import aggregate_case_metrics, evaluate_case
from ..p4_stats import FAULT_ORDER


DATASETS = ("re2ob", "re2tt")
FOLDS = (0, 1, 2)
SEED = 20260826
EXPECTED_CASES = 90
EXPECTED_FOLD_TEST_CASES = 30
EXPECTED_FOLD_TRAIN_CASES = 60
EXPECTED_CANDIDATES = {"re2ob": 11, "re2tt": 68}
FROZEN_SHA256 = {
    "re2ob": {
        "feature_manifest": "cc171f32c7642c6ddbe59b5b52bb6f8351dd8d8a35289144277900bbbb1da4ed",
        "split_manifest": "a672d12be89e91efd7fe69cdf81713b3d18482bba6b46620b0bfd0b4ff7bfd62",
        "assignments": "ca576819554ebe3d1cddd8f261bb661e7111896ff7b7dd6258e9f5daafad5195",
        "candidate_registry": "9eae7e79662ade83e0f6034073ab5c424bbf93be5765bd4bc5ea51d90c0efd19",
    },
    "re2tt": {
        "feature_manifest": "ac0424a4018624a61e993649e2b94c678838a2d02dfc4bf8f5c1b0694a145256",
        "split_manifest": "3c3947d6377433507ca1ea6b69d88f6d8f359b42937bbcff1a7ac98422f05d7e",
        "assignments": "88b4615ed3c950569ed7e4c4e9c66a302e8f88adf1715a8457540e00390b68e7",
        "candidate_registry": "67ad834a58be40802d9a8071ae849b7812ee390b87b08b5d82567596a39d236a",
    },
}


@dataclass(frozen=True)
class SupervisedEvent:
    """Prediction-visible event; deliberately contains no root or fault label."""

    case_id: str
    dataset: str
    fold: int
    candidates: Tuple[str, ...]
    z1: np.ndarray
    trajectory: np.ndarray
    z2: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        z1 = np.asarray(self.z1, dtype=np.float64)
        trajectory = np.asarray(self.trajectory, dtype=np.float64)
        z2 = None if self.z2 is None else np.asarray(self.z2, dtype=np.float64)
        candidate_count = len(self.candidates)
        if self.dataset not in DATASETS or self.fold not in FOLDS:
            raise ValueError("invalid dataset or fold")
        if len(set(self.candidates)) != candidate_count or candidate_count < 2:
            raise ValueError("candidates must be unique")
        if z1.shape != (candidate_count, 32):
            raise ValueError("Z1 must be candidate x 32")
        if z2 is not None and z2.shape != (candidate_count, 68):
            raise ValueError("Z2 must be candidate x 68")
        if trajectory.shape != (candidate_count, 8, N_BINS):
            raise ValueError("trajectory must be candidate x 8 x 80")
        if not np.all(np.isfinite(z1)) or not np.all(np.isfinite(trajectory)):
            raise ValueError("supervised baseline inputs must be finite")
        if z2 is not None and not np.all(np.isfinite(z2)):
            raise ValueError("Z2 inputs must be finite")
        mask = trajectory[:, len(CHANNELS):, :]
        if not np.all((mask == 0.0) | (mask == 1.0)):
            raise ValueError("trajectory masks must be binary")
        if np.any(trajectory[:, :len(CHANNELS), :][mask == 0.0] != 0.0):
            raise ValueError("missing trajectory cells must retain zero fill")
        object.__setattr__(self, "z1", z1)
        object.__setattr__(self, "trajectory", trajectory)
        object.__setattr__(self, "z2", z2)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _verify_frozen_files(project_root: Path, dataset: str) -> None:
    if dataset not in DATASETS:
        raise ValueError("dataset must be re2ob or re2tt")
    paths = {
        "feature_manifest": project_root / "artifacts" / "features" / dataset / "manifest.json",
        "split_manifest": project_root / "artifacts" / "splits" / dataset / "split_manifest.json",
        "assignments": project_root / "artifacts" / "splits" / dataset / "assignments.json",
        "candidate_registry": project_root / "artifacts" / "source" / dataset / "service_registry.json",
    }
    for name, path in paths.items():
        actual = sha256_file(path)
        if actual != FROZEN_SHA256[dataset][name]:
            raise ValueError("frozen {} digest mismatch for {}".format(name, dataset))


def load_prediction_events(project_root: Path, dataset: str) -> Mapping[str, SupervisedEvent]:
    """Load only prediction-visible arrays and folds; never open labels.jsonl."""

    _verify_frozen_files(project_root, dataset)
    registry_doc = read_json(project_root / "artifacts" / "source" / dataset / "service_registry.json")
    candidates = tuple(str(value) for value in registry_doc["services"])
    if len(candidates) != EXPECTED_CANDIDATES[dataset]:
        raise ValueError("candidate registry size mismatch")
    assignment_rows = read_json(project_root / "artifacts" / "splits" / dataset / "assignments.json")
    assignments = {str(row["case_id"]): int(row["fold"]) for row in assignment_rows}
    if len(assignments) != EXPECTED_CASES or set(assignments.values()) != set(FOLDS):
        raise ValueError("frozen assignment universe mismatch")

    feature_dir = project_root / "artifacts" / "features" / dataset
    feature_paths = tuple(sorted(feature_dir.glob("*.npz")))
    if len(feature_paths) != EXPECTED_CASES:
        raise ValueError("expected exactly 90 feature archives")
    events: Dict[str, SupervisedEvent] = {}
    for path in feature_paths:
        with np.load(path) as data:
            case_id = str(data["case_id"][0])
            event_candidates = tuple(str(value) for value in data["candidates"])
            base = np.asarray(data["base"], dtype=np.float64)
            morphology = np.asarray(data["z2"], dtype=np.float64)
            z = np.asarray(data["z"], dtype=np.float64)
            q_mask = np.asarray(data["q_mask"], dtype=np.float64)
        if path.stem != case_id or event_candidates != candidates:
            raise ValueError("feature case identity or canonical candidate order mismatch")
        if case_id not in assignments or case_id in events:
            raise ValueError("feature and split case universes differ")
        events[case_id] = SupervisedEvent(
            case_id=case_id,
            dataset=dataset,
            fold=assignments[case_id],
            candidates=event_candidates,
            z1=base.reshape(len(candidates), -1),
            trajectory=np.concatenate((z, q_mask), axis=1),
            z2=np.concatenate((base, morphology), axis=2).reshape(len(candidates), -1),
        )
    if set(events) != set(assignments):
        raise ValueError("features and assignments must align exactly")
    return events


def partition_fold(
    events: Mapping[str, SupervisedEvent], fold: int
) -> Tuple[Tuple[SupervisedEvent, ...], Tuple[SupervisedEvent, ...]]:
    if fold not in FOLDS:
        raise ValueError("fold must be 0, 1, or 2")
    train = tuple(events[case_id] for case_id in sorted(events) if events[case_id].fold != fold)
    test = tuple(events[case_id] for case_id in sorted(events) if events[case_id].fold == fold)
    if len(train) != EXPECTED_FOLD_TRAIN_CASES or len(test) != EXPECTED_FOLD_TEST_CASES:
        raise ValueError("outer fold must contain exactly 60 train and 30 test events")
    if {event.case_id for event in train} & {event.case_id for event in test}:
        raise ValueError("outer train/test overlap")
    return train, test


def load_label_subset(
    project_root: Path, dataset: str, allowed_case_ids: Sequence[str]
) -> Mapping[str, Mapping[str, str]]:
    """Return labels only for an explicit phase-owned case subset."""

    allowed = frozenset(str(value) for value in allowed_case_ids)
    if not allowed:
        raise ValueError("label subset must be non-empty")
    result: Dict[str, Mapping[str, str]] = {}
    path = project_root / "artifacts" / "source" / dataset / "labels.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = str(row["case_id"])
        if case_id in allowed:
            result[case_id] = {
                "root_service": str(row["root_service"]),
                "fault_type": str(row["fault_type"]),
            }
    if set(result) != set(allowed):
        raise ValueError("requested label subset is incomplete")
    return result


def rank_scores(candidates: Sequence[str], scores: Sequence[float]) -> Tuple[str, ...]:
    if len(candidates) != len(scores) or len(set(candidates)) != len(candidates):
        raise ValueError("candidate scores must be complete and unique")
    values = np.asarray(scores, dtype=np.float64)
    if values.shape != (len(candidates),) or not np.all(np.isfinite(values)):
        raise ValueError("candidate scores must be finite")
    order = sorted(range(len(candidates)), key=lambda index: (-float(values[index]), index))
    return tuple(candidates[index] for index in order)


def evaluate_fold_scores(
    project_root: Path,
    dataset: str,
    fold: int,
    test_events: Sequence[SupervisedEvent],
    scores_by_case: Mapping[str, Sequence[float]],
) -> Tuple[Tuple[Mapping[str, object], ...], Mapping[str, object]]:
    """Join outer-test labels only after complete scores already exist."""

    test_ids = tuple(event.case_id for event in test_events)
    if set(scores_by_case) != set(test_ids):
        raise ValueError("prediction scores must cover the exact test fold")
    rankings = {}
    for event in test_events:
        rankings[event.case_id] = rank_scores(event.candidates, scores_by_case[event.case_id])

    labels = load_label_subset(project_root, dataset, test_ids)
    candidate_rows = []
    prediction_rows = []
    candidates_by_case = {}
    roots = {}
    for event in test_events:
        label = labels[event.case_id]
        root = label["root_service"]
        if root not in event.candidates:
            raise ValueError("test root is absent from candidate registry")
        ranking = rankings[event.case_id]
        root_rank = ranking.index(root) + 1
        score_map = {
            candidate: float(np.asarray(scores_by_case[event.case_id])[index])
            for index, candidate in enumerate(event.candidates)
        }
        prediction_rows.append({
            "case_id": event.case_id,
            "dataset": dataset,
            "fault_type": label["fault_type"],
            "fold": fold,
            "root_service": root,
            "candidate_scores": score_map,
            "ranking": list(ranking),
        })
        for rank, candidate in enumerate(ranking, start=1):
            candidate_rows.append({
                "case_id": event.case_id,
                "candidate": candidate,
                "score": score_map[candidate],
                "rank": rank,
                "root_service": root,
                "root_rank": root_rank,
                "fold": fold,
                "dataset": dataset,
                "fault_type": label["fault_type"],
            })
        candidates_by_case[event.case_id] = event.candidates
        roots[event.case_id] = root
    case_metrics = []
    for prediction in prediction_rows:
        case_id = str(prediction["case_id"])
        values = evaluate_case(
            tuple(prediction["ranking"]), roots[case_id], tuple(candidates_by_case[case_id])
        )
        case_metrics.append({
            **values,
            "case_id": case_id,
            "fault_type": prediction["fault_type"],
            "fold": fold,
            "root_service": roots[case_id],
        })
    metrics = {
        "overall_cases": aggregate_case_metrics(case_metrics),
        "by_fault": {
            fault: aggregate_case_metrics([row for row in case_metrics if row["fault_type"] == fault])
            for fault in FAULT_ORDER
        },
        "by_root": {
            root: aggregate_case_metrics([row for row in case_metrics if row["root_service"] == root])
            for root in sorted(set(roots.values()))
        },
        "by_fold": {str(fold): aggregate_case_metrics(case_metrics)},
        "case_metrics": case_metrics,
    }
    return tuple(candidate_rows), metrics


def current_git_identity(project_root: Path) -> Mapping[str, object]:
    head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=str(project_root), text=True).strip()
    branch = subprocess.check_output(("git", "branch", "--show-current"), cwd=str(project_root), text=True).strip()
    status = subprocess.check_output(
        ("git", "status", "--porcelain", "--untracked-files=all"),
        cwd=str(project_root),
        text=True,
    ).splitlines()
    return {"head": head, "branch": branch, "dirty_entries": tuple(status)}


def base_environment() -> Mapping[str, object]:
    import pandas
    import scipy
    import sklearn

    return {
        "python": platform.python_version(),
        "python_executable": __import__("sys").executable,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
    }


def create_run_directory(path: Path, config: Mapping[str, object]) -> str:
    if path.exists():
        raise FileExistsError("formal output directory already exists: {}".format(path))
    path.mkdir(parents=True)
    started_at = datetime.now(timezone.utc).isoformat()
    write_json(path / "status.json", {"status": "RUNNING", "started_at": started_at})
    write_json(path / "config.json", config)
    return started_at


def _allowed_untracked_artifact_prefixes(
    project_root: Path, output_root: Path
) -> Tuple[str, ...]:
    """Return Git-porcelain prefixes for approved supervised artifact roots."""

    project_root = project_root.resolve()
    canonical_root = project_root / "artifacts" / "supervised_baselines"
    roots = (canonical_root, output_root.resolve())
    prefixes = []
    for root in roots:
        try:
            relative = root.relative_to(project_root)
        except ValueError:
            # An output root outside the worktree cannot make this worktree dirty.
            continue
        parts = relative.parts
        is_supervised_namespace = (
            len(parts) >= 2
            and parts[0] == "artifacts"
            and (
                parts[1] == "supervised_baselines"
                or parts[1].startswith("supervised_baselines_")
                or parts[1] == "z2_xgb_closure"
            )
        )
        if not is_supervised_namespace:
            raise ValueError(
                "in-worktree output root must use artifacts/supervised_baselines[_*]: "
                "{}".format(root)
            )
        if len(parts) >= 2 and parts[1] == "z2_xgb_closure":
            # The closure namespace may contain isolated replay/audit roots.
            prefix = "?? artifacts/z2_xgb_closure/"
        else:
            prefix = "?? {}/".format(relative.as_posix().rstrip("/"))
        if prefix not in prefixes:
            prefixes.append(prefix)
    return tuple(prefixes)


def finalize_run_directory(
    run_dir: Path,
    candidate_rows: Sequence[Mapping[str, object]],
    metrics: Mapping[str, object],
    environment: Mapping[str, object],
    provenance: Mapping[str, object],
    firewall: Mapping[str, object],
    integrity: Mapping[str, object],
    runtime: Mapping[str, object],
) -> None:
    write_jsonl(run_dir / "predictions.jsonl", candidate_rows)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "environment.json", environment)
    write_json(run_dir / "provenance.json", provenance)
    write_json(run_dir / "label_firewall.json", firewall)
    write_json(run_dir / "integrity.json", integrity)
    write_json(run_dir / "runtime.json", runtime)
    completed_at = datetime.now(timezone.utc).isoformat()
    write_json(run_dir / "status.json", {"status": "COMPLETE", "completed_at": completed_at})
    checksums = {
        str(path.relative_to(run_dir)): sha256_file(path)
        for path in sorted(run_dir.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }
    write_json(run_dir / "checksums.json", checksums)


def run_fold(
    project_root: Path,
    dataset: str,
    fold: int,
    method: str,
    output_root: Path,
    config: Mapping[str, object],
    fit_and_score: Callable[
        [Sequence[SupervisedEvent], Mapping[str, str], Sequence[SupervisedEvent], Path],
        Mapping[str, Sequence[float]],
    ],
    environment_extra: Mapping[str, object],
) -> Mapping[str, object]:
    git_identity = current_git_identity(project_root)
    if os.environ.get("PYTHONHASHSEED") != str(SEED):
        raise RuntimeError("formal run requires PYTHONHASHSEED={}".format(SEED))
    allowed_artifact_prefixes = _allowed_untracked_artifact_prefixes(
        project_root, output_root
    )
    disallowed_dirty = [
        entry for entry in git_identity["dirty_entries"]
        if not any(entry.startswith(prefix) for prefix in allowed_artifact_prefixes)
    ]
    if disallowed_dirty:
        raise RuntimeError(
            "formal run rejects non-artifact worktree changes: {}".format(disallowed_dirty)
        )
    events = load_prediction_events(project_root, dataset)
    train_events, test_events = partition_fold(events, fold)
    run_dir = output_root / method / dataset / "fold_{}".format(fold)
    started_at = create_run_directory(run_dir, config)
    train_ids = tuple(event.case_id for event in train_events)
    test_ids = tuple(event.case_id for event in test_events)
    train_labels = load_label_subset(project_root, dataset, train_ids)
    train_roots = {case_id: row["root_service"] for case_id, row in train_labels.items()}

    import time
    started_clock = time.monotonic()
    try:
        scores_by_case = fit_and_score(train_events, train_roots, test_events, run_dir)
    except Exception as exc:
        write_json(run_dir / "status.json", {
            "status": "FAILED",
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise
    prediction_completed_at = datetime.now(timezone.utc).isoformat()
    candidate_rows, metrics = evaluate_fold_scores(
        project_root, dataset, fold, test_events, scores_by_case
    )
    elapsed = time.monotonic() - started_clock
    expected_rows = EXPECTED_FOLD_TEST_CASES * EXPECTED_CANDIDATES[dataset]
    complete = len(candidate_rows) == expected_rows
    ranks_complete = all(
        sorted(row["rank"] for row in candidate_rows if row["case_id"] == case_id)
        == list(range(1, EXPECTED_CANDIDATES[dataset] + 1))
        for case_id in test_ids
    )
    integrity = {
        "status": "PASS" if complete and ranks_complete else "FAIL",
        "case_count": len(test_ids),
        "candidate_row_count": len(candidate_rows),
        "expected_candidate_row_count": expected_rows,
        "complete_candidate_rows": complete,
        "complete_rank_permutations": ranks_complete,
        "root_present_exactly_once_per_case": all(
            sum(row["candidate"] == row["root_service"] for row in candidate_rows if row["case_id"] == case_id) == 1
            for case_id in test_ids
        ),
    }
    if integrity["status"] != "PASS":
        raise RuntimeError("supervised baseline output integrity failed")
    firewall = {
        "status": "PASS",
        "train_case_count": len(train_ids),
        "test_case_count": len(test_ids),
        "train_test_overlap": sorted(set(train_ids) & set(test_ids)),
        "fit_label_case_ids_sha256": hashlib.sha256("\n".join(train_ids).encode("utf-8")).hexdigest(),
        "predict_interface_label_free": True,
        "test_labels_joined_after_prediction": True,
        "prediction_completed_at": prediction_completed_at,
        "normalization_scope": config.get("normalization", "none"),
    }
    environment = dict(base_environment())
    environment.update(environment_extra)
    provenance = {
        "schema_version": "supervised_baseline_fold_v1",
        "method": method,
        "dataset": dataset,
        "fold": fold,
        "source_commit": git_identity["head"],
        "branch": git_identity["branch"],
        "protocol": "docs/supervised_baselines/SUPERVISED_BASELINE_PROTOCOL_V1.md",
        "frozen_input_sha256": FROZEN_SHA256[dataset],
        "started_at": started_at,
    }
    finalize_run_directory(
        run_dir,
        candidate_rows,
        metrics,
        environment,
        provenance,
        firewall,
        integrity,
        {"elapsed_seconds": elapsed, "train_cases": len(train_ids), "test_cases": len(test_ids)},
    )
    return {"run_dir": str(run_dir), "metrics": metrics["overall_cases"], "integrity": integrity}
