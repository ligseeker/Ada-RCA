"""Adapters for the frozen RCAEval RE2-OB and RE2-TT case layouts."""

import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import FrozenSet, List, Sequence, Tuple

from .schema import RCACaseInput, RCACaseLabel, TelemetryRef, validate_case_collection


FAULT_TYPES = ("cpu", "mem", "disk", "socket", "delay", "loss")
_AUXILIARY_ENTITIES = frozenset(
    {"frontend-check", "frontend-external", "istio-init", "loadgenerator"}
)


@dataclass(frozen=True)
class DatasetProfile:
    key: str
    dataset: str
    id_namespace: str
    id_prefix: str
    uri_namespace: str
    root_path: str
    expected_cases: int = 90
    replicates: Tuple[str, ...] = ("1", "2", "3")
    auxiliary_entities: FrozenSet[str] = _AUXILIARY_ENTITIES


RE2OB = DatasetProfile(
    "re2ob", "RCAEval-RE2-OB", "RCAEval:RE2-OB", "re2ob", "re2-ob",
    "/home/zhangll24/RCA_project/datasets/RCAEval/RE2-OB",
)
RE2TT = DatasetProfile(
    "re2tt", "RCAEval-RE2-TT", "RCAEval:RE2-TT", "re2tt", "re2-tt",
    "/home/zhangll24/RCA_project/datasets/RCAEval/RE2/RE2-TT",
)
DATASETS = {profile.key: profile for profile in (RE2OB, RE2TT)}


@dataclass(frozen=True)
class CaseSource:
    case_id: str
    relative_directory: str
    replicate: int
    condition: str
    metrics_path: str
    simple_metrics_path: str
    logs_path: str
    logts_path: str
    traces_path: str
    trace_error_path: str
    trace_latency_path: str
    inject_time_path: str


@dataclass(frozen=True)
class ExcludedCase:
    relative_directory: str
    reason: str


@dataclass(frozen=True)
class AdapterResult:
    inputs: Tuple[RCACaseInput, ...]
    labels: Tuple[RCACaseLabel, ...]
    sources: Tuple[CaseSource, ...]
    excluded: Tuple[ExcludedCase, ...]


def opaque_case_id(profile: DatasetProfile, relative_directory: str) -> str:
    payload = "{}:{}".format(profile.id_namespace, relative_directory).encode("utf-8")
    return "{}-{}".format(profile.id_prefix, hashlib.sha256(payload).hexdigest()[:16])


def parse_condition(condition: str) -> Tuple[str, str]:
    if "_" not in condition:
        raise ValueError("condition must be <root_service>_<fault_type>")
    root, fault = condition.rsplit("_", 1)
    if fault not in FAULT_TYPES:
        raise ValueError("unsupported fault type {!r}".format(fault))
    return root, fault


def read_header(path: Path) -> Sequence[str]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return next(csv.reader(handle))


def candidate_services(case_directory: Path, profile: DatasetProfile) -> Tuple[str, ...]:
    header = read_header(case_directory / "simple_metrics.csv")
    candidates = {
        column.rsplit("_", 1)[0]
        for column in header
        if column.endswith("_cpu") or column.endswith("_mem")
    }
    candidates.difference_update(profile.auxiliary_entities)
    if not candidates:
        raise ValueError("no candidate services derived from label-free metric schema")
    return tuple(sorted(candidates))


def discover_case_directories(root: Path, profile: DatasetProfile) -> Sequence[Path]:
    directories: List[Path] = []
    for condition in sorted(path for path in root.iterdir() if path.is_dir()):
        try:
            parse_condition(condition.name)
        except ValueError:
            continue
        for replicate in profile.replicates:
            case = condition / replicate
            if case.is_dir():
                directories.append(case)
    return directories


def load_cases(profile: DatasetProfile, raw_path: str = None) -> AdapterResult:
    root = Path(raw_path or profile.root_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(str(root))
    inputs, labels, sources, excluded = [], [], [], []
    for case_directory in discover_case_directories(root, profile):
        relative = str(case_directory.relative_to(root))
        required = {
            "metrics": case_directory / "metrics.csv",
            "simple_metrics": case_directory / "simple_metrics.csv",
            "logs": case_directory / "logs.csv",
            "logts": case_directory / "logts.csv",
            "traces": case_directory / "traces.csv",
            "trace_error": case_directory / "tracets_err.csv",
            "trace_latency": case_directory / "tracets_lat.csv",
            "inject_time": case_directory / "inject_time.txt",
        }
        missing = tuple(sorted(key for key, path in required.items() if not path.is_file()))
        if missing:
            excluded.append(ExcludedCase(relative, "missing:" + ",".join(missing)))
            continue
        try:
            root_service, fault_type = parse_condition(case_directory.parent.name)
            anchor_time = int(required["inject_time"].read_text(encoding="utf-8").strip())
            services = candidate_services(case_directory, profile)
        except (OSError, StopIteration, TypeError, ValueError) as exc:
            excluded.append(ExcludedCase(relative, "parse_error:" + type(exc).__name__))
            continue
        if root_service not in services:
            excluded.append(ExcludedCase(relative, "root_not_in_candidates"))
            continue

        case_id = opaque_case_id(profile, relative)
        base_uri = "rcaeval://{}/{}".format(profile.uri_namespace, case_id)
        inputs.append(
            RCACaseInput(
                case_id=case_id,
                dataset=profile.dataset,
                anchor_time=anchor_time,
                services=services,
                metrics=TelemetryRef(base_uri + "/metrics", "csv-wide", "time", metadata={"timestamp_unit": "s"}),
                logs=TelemetryRef(base_uri + "/logs", "csv", "timestamp", "container_name", {"timestamp_unit": "ns"}),
                traces=TelemetryRef(base_uri + "/traces", "csv", "startTime", "serviceName", {"timestamp_unit": "us"}),
                metadata={
                    "candidate_rule": "simple_metrics CPU/memory entity union excluding auxiliary entities",
                    "channels": ("metric", "log", "trace-error", "trace-latency"),
                },
            )
        )
        labels.append(RCACaseLabel(case_id, root_service, fault_type))
        sources.append(
            CaseSource(
                case_id, relative, int(case_directory.name), case_directory.parent.name,
                *(str(required[key]) for key in (
                    "metrics", "simple_metrics", "logs", "logts", "traces",
                    "trace_error", "trace_latency", "inject_time",
                ))
            )
        )
    validate_case_collection(inputs, labels)
    return AdapterResult(tuple(inputs), tuple(labels), tuple(sources), tuple(excluded))


def load_re2ob_cases(raw_path: str = None) -> AdapterResult:
    return load_cases(RE2OB, raw_path)


def load_re2tt_cases(raw_path: str = None) -> AdapterResult:
    return load_cases(RE2TT, raw_path)
