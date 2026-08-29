"""Label-free utilities for P6-E4 baseline integration qualification."""

import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd


BASE_SHA = "bed295326e567395e725caa82840a534dcc0b1de"
RCAEVAL_SHA = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
RCAEVAL_REMOTE = "https://github.com/phamquiluan/RCAEval.git"
WINDOW_SECONDS = 600
FORMAL_FILES = (
    "metrics.csv",
    "simple_metrics.csv",
    "logs.csv",
    "logts.csv",
    "traces.csv",
    "tracets_err.csv",
    "tracets_lat.csv",
    "inject_time.txt",
)
SOURCE_CHECKSUM_PATHS = (
    "RCAEval/e2e/baro.py",
    "RCAEval/e2e/tracerca.py",
    "RCAEval/e2e/__init__.py",
    "RCAEval/io/time_series.py",
    "main.py",
)
DATASETS = {
    "re2-ob": Path("/home/zhangll24/RCA_project/datasets/RCAEval/RE2-OB"),
    "re2-tt": Path("/home/zhangll24/RCA_project/datasets/RCAEval/RE2/RE2-TT"),
}
FAULT_SUFFIXES = frozenset(("cpu", "mem", "disk", "socket", "delay", "loss"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def git_output(path: Path, *args: str) -> str:
    return subprocess.check_output(("git",) + args, cwd=str(path), text=True).strip()


def assert_baseline_branch(project_root: Path) -> None:
    branch = git_output(project_root, "branch", "--show-current")
    if branch != "exp/p6-baselines":
        raise RuntimeError("P6-E4 preparation requires exp/p6-baselines")
    merge_base = git_output(project_root, "merge-base", "HEAD", "main")
    if merge_base != BASE_SHA:
        raise RuntimeError("baseline branch base SHA mismatch: {}".format(merge_base))


def assert_clean_upstream(rcaeval_root: Path) -> Mapping[str, object]:
    head = git_output(rcaeval_root, "rev-parse", "HEAD")
    status = git_output(rcaeval_root, "status", "--porcelain")
    remote = git_output(rcaeval_root, "remote", "get-url", "origin")
    if head != RCAEVAL_SHA:
        raise RuntimeError("RCAEval HEAD mismatch: {}".format(head))
    if status:
        raise RuntimeError("RCAEval worktree is dirty")
    if remote != RCAEVAL_REMOTE:
        raise RuntimeError("RCAEval remote mismatch: {}".format(remote))
    return {"head": head, "clean": True, "status": [], "remote": remote}


def legal_case_directories(dataset_root: Path) -> Tuple[Path, ...]:
    cases: List[Path] = []
    for condition in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        if "_" not in condition.name:
            continue
        suffix = condition.name.rsplit("_", 1)[1]
        if suffix not in FAULT_SUFFIXES:
            continue
        for replicate in ("1", "2", "3"):
            case = condition / replicate
            if case.is_dir() and all((case / name).is_file() for name in FORMAL_FILES):
                cases.append(case)
    return tuple(cases)


def normalized_relative_path(case_path: Path, dataset_root: Path) -> str:
    return case_path.relative_to(dataset_root).as_posix()


def build_smoke_manifest(dataset_roots: Mapping[str, Path]) -> Mapping[str, object]:
    selected: Dict[str, List[Mapping[str, str]]] = {}
    enumerated: Dict[str, int] = {}
    for dataset, root in sorted(dataset_roots.items()):
        cases = legal_case_directories(root)
        if len(cases) != 90:
            raise RuntimeError("{} legal case count is {}, expected 90".format(dataset, len(cases)))
        rows = []
        for case in cases:
            relative = normalized_relative_path(case, root)
            rows.append(
                {
                    "normalized_relative_path": relative,
                    "sha256": sha256_bytes(relative.encode("utf-8")),
                }
            )
        rows.sort(key=lambda row: (row["sha256"], row["normalized_relative_path"]))
        enumerated[dataset] = len(rows)
        selected[dataset] = rows[:3]
    return {
        "schema_version": "p6_e4_smoke_case_manifest_v1",
        "selection_rule": "ascending SHA-256(normalized POSIX relative path), path tie-breaker",
        "cases_per_dataset": 3,
        "enumerated_legal_case_counts": enumerated,
        "selected_cases": selected,
        "selection_inputs": "normalized relative paths only",
        "selection_completed_before_tier_a_invocation": True,
        "tier_a_invocation_count_at_freeze": 0,
        "performance_or_label_input_used": False,
    }


def _header(path: Path) -> Tuple[str, ...]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return tuple(next(csv.reader(handle)))


def _numeric_csv_summary(
    path: Path,
    columns: Sequence[str],
    derived_end: bool = False,
    chunk_size: int = 250000,
) -> Mapping[str, object]:
    parsed_rows = 0
    malformed_numeric_rows = 0
    minima: Dict[str, Optional[float]] = {column: None for column in columns}
    maxima: Dict[str, Optional[float]] = {column: None for column in columns}
    end_min: Optional[float] = None
    end_max: Optional[float] = None
    try:
        chunks = pd.read_csv(
            path,
            usecols=list(columns),
            chunksize=chunk_size,
            on_bad_lines="error",
            low_memory=False,
        )
        for chunk in chunks:
            parsed_rows += len(chunk)
            numeric = chunk.apply(pd.to_numeric, errors="coerce")
            bad = numeric.isna().any(axis=1)
            malformed_numeric_rows += int(bad.sum())
            valid = numeric.loc[~bad]
            for column in columns:
                if valid.empty:
                    continue
                current_min = float(valid[column].min())
                current_max = float(valid[column].max())
                minima[column] = current_min if minima[column] is None else min(minima[column], current_min)
                maxima[column] = current_max if maxima[column] is None else max(maxima[column], current_max)
            if derived_end and not valid.empty:
                ends = valid[columns[0]] + valid[columns[1]]
                current_end_min = float(ends.min())
                current_end_max = float(ends.max())
                end_min = current_end_min if end_min is None else min(end_min, current_end_min)
                end_max = current_end_max if end_max is None else max(end_max, current_end_max)
    except (ValueError, pd.errors.ParserError) as exc:
        return {
            "logical_rows": parsed_rows,
            "parsed_rows": parsed_rows,
            "malformed_rows": malformed_numeric_rows,
            "error": "{}: {}".format(type(exc).__name__, str(exc)),
            "min": minima,
            "max": maxima,
            "derived_end_min": end_min,
            "derived_end_max": end_max,
        }
    return {
        "logical_rows": parsed_rows,
        "parsed_rows": parsed_rows,
        "malformed_rows": malformed_numeric_rows,
        "min": minima,
        "max": maxima,
        "derived_end_min": end_min,
        "derived_end_max": end_max,
    }


def _row_count_only(path: Path) -> Mapping[str, object]:
    rows = 0
    try:
        for chunk in pd.read_csv(path, chunksize=250000, on_bad_lines="error", low_memory=False):
            rows += len(chunk)
    except (ValueError, pd.errors.ParserError) as exc:
        return {
            "logical_rows": rows,
            "parsed_rows": rows,
            "malformed_rows": 0,
            "error": "{}: {}".format(type(exc).__name__, str(exc)),
        }
    return {"logical_rows": rows, "parsed_rows": rows, "malformed_rows": 0}


def audit_case(dataset: str, dataset_root: Path, case_path: Path) -> Mapping[str, object]:
    relative = normalized_relative_path(case_path, dataset_root)
    available = sorted(name for name in FORMAL_FILES if (case_path / name).is_file())
    missing = sorted(name for name in FORMAL_FILES if not (case_path / name).is_file())
    inject_time = int((case_path / "inject_time.txt").read_text(encoding="utf-8").strip())
    file_summaries: Dict[str, Mapping[str, object]] = {}
    timestamp_columns: Dict[str, Optional[str]] = {}
    time_support: Dict[str, Mapping[str, object]] = {}

    for filename in FORMAL_FILES:
        if filename == "inject_time.txt":
            continue
        path = case_path / filename
        header = _header(path)
        if filename == "traces.csv":
            required = ("startTime", "duration")
            if not all(column in header for column in required):
                summary = _row_count_only(path)
                summary = dict(summary)
                summary["error"] = "missing trace timestamp columns"
            else:
                summary = _numeric_csv_summary(path, required, derived_end=True)
            timestamp_columns[filename] = "startTime,duration"
        else:
            preferred = ("timestamp", "time") if filename == "logs.csv" else ("time", "timestamp")
            timestamp = next((column for column in preferred if column in header), None)
            timestamp_columns[filename] = timestamp
            summary = _numeric_csv_summary(path, (timestamp,)) if timestamp else _row_count_only(path)
        file_summaries[filename] = summary
        if filename in ("logts.csv", "tracets_err.csv", "tracets_lat.csv"):
            time_support[filename] = {
                "time_column": timestamp_columns[filename],
                "min": summary.get("min", {}).get(timestamp_columns[filename]),
                "max": summary.get("max", {}).get(timestamp_columns[filename]),
                "rows": summary["logical_rows"],
                "malformed_rows": summary["malformed_rows"],
            }

    trace = file_summaries["traces.csv"]
    return {
        "dataset": dataset,
        "normalized_case_path": relative,
        "available_source_files": available,
        "missing_source_flags": missing,
        "inject_time": inject_time,
        "file_row_counts": {
            name: summary["logical_rows"] for name, summary in sorted(file_summaries.items())
        },
        "timestamp_column_names": timestamp_columns,
        "time_min_max": {
            name: {"min": summary.get("min"), "max": summary.get("max")}
            for name, summary in sorted(file_summaries.items())
            if summary.get("min") is not None
        },
        "trace_startTime_min": trace.get("min", {}).get("startTime"),
        "trace_startTime_max": trace.get("max", {}).get("startTime"),
        "trace_duration_min": trace.get("min", {}).get("duration"),
        "trace_duration_max": trace.get("max", {}).get("duration"),
        "trace_endTime_min": trace.get("derived_end_min"),
        "trace_endTime_max": trace.get("derived_end_max"),
        "logts_time_support": time_support["logts.csv"],
        "tracets_err_support": time_support["tracets_err.csv"],
        "tracets_lat_support": time_support["tracets_lat.csv"],
        "malformed_row_counts": {
            name: summary["malformed_rows"] for name, summary in sorted(file_summaries.items())
        },
        "parse_errors": {
            name: summary["error"]
            for name, summary in sorted(file_summaries.items())
            if "error" in summary
        },
    }


def build_all_case_schema_audit(dataset_roots: Mapping[str, Path]) -> Mapping[str, object]:
    cases = []
    for dataset, root in sorted(dataset_roots.items()):
        legal = legal_case_directories(root)
        if len(legal) != 90:
            raise RuntimeError("{} legal case count is {}, expected 90".format(dataset, len(legal)))
        for case_path in legal:
            cases.append(audit_case(dataset, root, case_path))
    return {
        "schema_version": "p6_e4_all_case_schema_audit_v1",
        "case_count": len(cases),
        "dataset_case_counts": {
            dataset: sum(1 for row in cases if row["dataset"] == dataset)
            for dataset in sorted(dataset_roots)
        },
        "performance_fields_recorded": False,
        "cases": cases,
    }


def package_versions() -> Mapping[str, str]:
    packages = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name") or distribution.metadata.get("Summary")
        if name:
            packages[str(name)] = distribution.version
    return dict(sorted(packages.items(), key=lambda item: item[0].lower()))


def build_upstream_provenance(rcaeval_root: Path) -> Mapping[str, object]:
    identity = assert_clean_upstream(rcaeval_root)
    checksums = {
        relative: sha256_file(rcaeval_root / relative) for relative in SOURCE_CHECKSUM_PATHS
    }
    freeze = subprocess.check_output(
        (sys.executable, "-m", "pip", "freeze"), text=True
    ).splitlines()
    return {
        "schema_version": "p6_e4_upstream_provenance_v1",
        "path": str(rcaeval_root.resolve()),
        "remote": identity["remote"],
        "head": identity["head"],
        "clean_status": identity["clean"],
        "working_tree_status": identity["status"],
        "environment": {
            "name": Path(sys.prefix).name,
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "dependency_source": [
                "pinned RCAEval repository requirements.txt",
                "pre-existing isolated conda environment rcaeval",
            ],
            "installation_commands_this_round": [],
            "package_versions": package_versions(),
            "pip_freeze": freeze,
        },
        "source_sha256": checksums,
    }


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
