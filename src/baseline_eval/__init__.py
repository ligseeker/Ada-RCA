"""Performance-blind RCAEval baseline protocol and adapter primitives.

This package deliberately contains no label join and no aggregate performance
evaluator.  It is isolated from ``src.rca`` so the frozen Ada-RCA V1 code is not
modified by the baseline audit.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from enum import Enum
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STARTING_HEAD = "9342e06db91945be2e44703437229ba45b18bda8"
PROTOCOL_VERSION = "baseline_protocol_freeze_v1"
CANONICAL_SEED = 20260830
EXPECTED_CASES_PER_DATASET = 90
TRACE_TIMESTAMP_MULTIPLIER = 1_000_000
WINDOW_SECONDS = 600


class AdapterError(ValueError):
    """Native output cannot be converted without inventing evidence."""


class DenominatorError(ValueError):
    """The persisted records do not cover the frozen case denominator."""


class FirewallBreach(ValueError):
    """A case record contains a forbidden label or performance field."""


class MethodOutputError(ValueError):
    """A method returned no valid native ranking or violated its output contract."""


class TerminalStatus(str, Enum):
    SUCCESS = "SUCCESS"
    METHOD_FAILURE = "METHOD_FAILURE"
    ADAPTER_FAILURE = "ADAPTER_FAILURE"
    DATA_FAILURE = "DATA_FAILURE"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class AdaptedRanking:
    services: tuple[str, ...]
    duplicates: tuple[str, ...]
    unmapped: tuple[str, ...]
    native_count: int


@dataclass(frozen=True)
class CaseRecord:
    """Label-free terminal record for exactly one method/case invocation."""

    protocol_version: str
    method: str
    dataset: str
    case_id: str
    status: TerminalStatus
    native_output_kind: str
    native_ranking: tuple[str, ...] = ()
    adapted_ranking: tuple[str, ...] = ()
    duplicate_native_items: tuple[str, ...] = ()
    unmapped_native_items: tuple[str, ...] = ()
    missing_candidate_reasons: tuple[str, ...] = ()
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, TerminalStatus):
            object.__setattr__(self, "status", TerminalStatus(self.status))
        if self.status is TerminalStatus.SUCCESS:
            if not self.native_ranking or not self.adapted_ranking:
                raise ValueError("SUCCESS requires non-empty native and adapted rankings")
        elif self.native_ranking or self.adapted_ranking:
            raise ValueError("failure records cannot contain a fallback ranking")
        if len(set(self.adapted_ranking)) != len(self.adapted_ranking):
            raise ValueError("adapted ranking must contain unique services")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def audit_frozen_inputs(root: Path) -> dict[str, dict[str, Any]]:
    """Validate committed event, label, source, and registry identities.

    This function checks identities and membership only.  It never constructs a
    baseline output and never joins a label to a ranking.
    """

    result: dict[str, dict[str, Any]] = {}
    for dataset in ("re2ob", "re2tt"):
        bundle = root / "artifacts" / "source" / dataset
        input_path = bundle / "inputs.jsonl"
        label_path = bundle / "labels.jsonl"
        source_path = bundle / "sources.jsonl"
        registry_path = bundle / "service_registry.json"
        inputs = _jsonl(input_path)
        labels = _jsonl(label_path)
        sources = _jsonl(source_path)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))["services"]
        input_ids = [row["case_id"] for row in inputs]
        label_ids = [row["case_id"] for row in labels]
        source_ids = [row["case_id"] for row in sources]
        def source_anchor(source: Mapping[str, Any]) -> int:
            return int(Path(source["inject_time_path"]).read_text(encoding="utf-8").strip())

        with ThreadPoolExecutor(max_workers=16) as executor:
            source_anchors = tuple(executor.map(source_anchor, sources))
        anchors_match = tuple(int(case["anchor_time"]) for case in inputs) == source_anchors
        result[dataset] = {
            "case_count": len(inputs),
            "unique_case_count": len(set(input_ids)),
            "case_ids_aligned": input_ids == label_ids == source_ids,
            "anchors_match_sources": anchors_match,
            "candidate_count": len(registry),
            "registry_identical_across_cases": all(row["candidates"] == registry for row in inputs),
            "roots_in_registry": all(row["root_service"] in registry for row in labels),
            "inputs_sha256": _sha256(input_path),
            "labels_sha256": _sha256(label_path),
            "sources_sha256": _sha256(source_path),
            "registry_sha256": _sha256(registry_path),
        }
    return result


def assert_ada_rca_frozen_unchanged(root: Path) -> None:
    """Fail if any pre-existing frozen Ada-RCA path differs from the start."""

    pathspecs = (
        "src/rca",
        "configs",
        "artifacts",
        ":(exclude)artifacts/baseline_eval",
        "docs/BASELINE_COMPATIBILITY_MATRIX.md",
        "docs/BENCHMARK_COMPATIBILITY.md",
        "docs/RCA_FINAL_EVALUATION_PROTOCOL_V1.0.md",
        "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md",
        "docs/RCA_EVIDENCE_INDEX.md",
    )
    completed = subprocess.run(
        ("git", "diff", "--quiet", STARTING_HEAD, "--", *pathspecs),
        cwd=root,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError("Ada-RCA frozen paths differ from the baseline-evaluation starting HEAD")


def _normalize_frozen_alias(native_item: str) -> str:
    if native_item == "frontendservice":
        return "frontend"
    if native_item.startswith("frontendservice_"):
        return "frontend_" + native_item[len("frontendservice_") :]
    return native_item


def _map_native_item(native_item: str, candidates: Sequence[str]) -> str | None:
    normalized = _normalize_frozen_alias(native_item)
    matches = [
        candidate
        for candidate in candidates
        if normalized == candidate or normalized.startswith(candidate + "_")
    ]
    return max(matches, key=lambda candidate: (len(candidate), candidate)) if matches else None


def adapt_native_ranking(
    native_ranking: Sequence[str], candidates: Sequence[str]
) -> AdaptedRanking:
    """Project ordered indicator/operation names to a partial service ranking."""

    candidate_tuple = tuple(candidates)
    if not candidate_tuple or len(set(candidate_tuple)) != len(candidate_tuple):
        raise AdapterError("legal candidate registry must be non-empty and unique")
    services: list[str] = []
    duplicates: list[str] = []
    unmapped: list[str] = []
    for item in native_ranking:
        if not isinstance(item, str) or not item:
            unmapped.append(str(item))
            continue
        service = _map_native_item(item, candidate_tuple)
        if service is None:
            unmapped.append(item)
        elif service in services:
            duplicates.append(item)
        else:
            services.append(service)
    if not services:
        raise AdapterError("native ranking contains no item in the frozen legal registry")
    return AdaptedRanking(tuple(services), tuple(duplicates), tuple(unmapped), len(native_ranking))


def is_complete_legal_ranking(ranking: Sequence[str], candidates: Sequence[str]) -> bool:
    return (
        len(ranking) == len(candidates)
        and len(set(ranking)) == len(ranking)
        and set(ranking) == set(candidates)
    )


def metric_legality(output_semantics: str) -> dict[str, str]:
    if output_semantics == "COMPLETE_SERVICE_RANKING":
        return {metric: "NATIVE" for metric in ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")}
    if output_semantics == "OPERATION_OR_INDICATOR_PARTIAL":
        return {
            "AC@1": "ADAPTED-BUT-VALID",
            "AC@3": "ADAPTED-BUT-VALID",
            "AC@5": "ADAPTED-BUT-VALID",
            "Avg@5": "ADAPTED-BUT-VALID",
            "MRR": "NOT-IDENTIFIABLE",
        }
    return {metric: "NOT-IDENTIFIABLE" for metric in ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")}


def trace_anchor_microseconds(anchor_seconds: int) -> int:
    if isinstance(anchor_seconds, bool) or not isinstance(anchor_seconds, int):
        raise AdapterError("trace anchor must be an integer Unix timestamp in seconds")
    return anchor_seconds * TRACE_TIMESTAMP_MULTIPLIER


def span_end_in_canonical_window(start_time_us: int, duration_us: int, anchor_seconds: int) -> bool:
    end_time_us = int(start_time_us) + int(duration_us)
    anchor_us = trace_anchor_microseconds(anchor_seconds)
    return anchor_us - WINDOW_SECONDS * TRACE_TIMESTAMP_MULTIPLIER <= end_time_us < (
        anchor_us + WINDOW_SECONDS * TRACE_TIMESTAMP_MULTIPLIER
    )


def inspect_trace_timestamp_sample(root: Path, dataset: str) -> dict[str, Any]:
    """Inspect one deterministic committed raw/derived row for unit semantics."""

    if dataset not in {"re2ob", "re2tt"}:
        raise AdapterError("unsupported dataset")
    bundle = root / "artifacts" / "source" / dataset
    input_row = _jsonl(bundle / "inputs.jsonl")[0]
    source_row = _jsonl(bundle / "sources.jsonl")[0]
    anchor = int(input_row["anchor_time"])
    with Path(source_row["traces_path"]).open(encoding="utf-8", newline="") as handle:
        raw_row = next(csv.DictReader(handle))
    with Path(source_row["trace_error_path"]).open(encoding="utf-8", newline="") as handle:
        derived_row = next(csv.DictReader(handle))
    start_time = int(raw_row["startTime"])
    start_time_millis = int(raw_row["startTimeMillis"])
    duration = int(raw_row["duration"])
    derived_time = int(float(derived_row["time"]))
    metadata_unit = input_row["traces"]["metadata"]["timestamp_unit"]
    return {
        "case_id": input_row["case_id"],
        "inject_time_unit": "s" if 1_000_000_000 <= anchor < 10_000_000_000 else "UNKNOWN",
        "start_time_unit": metadata_unit if 1_000_000_000_000_000 <= start_time else "UNKNOWN",
        "duration_unit": "us",
        "derived_time_unit": "s" if 1_000_000_000 <= derived_time < 10_000_000_000 else "UNKNOWN",
        "start_time_millis_consistent": start_time // 1_000 == start_time_millis,
        "commented_conversion_is_required": start_time > anchor * 100_000 and duration < start_time,
    }


_MMBARO_KEYS = frozenset(
    {"metric", "logs", "logts", "traces", "tracets_err", "tracets_lat", "cluster_info"}
)


def mmbaro_dataset_key(dataset: str) -> str:
    try:
        return {"re2ob": "mm-ob", "re2tt": "mm-tt"}[dataset]
    except KeyError as exc:
        raise AdapterError("mmBARO supports only frozen RE2-OB and RE2-TT") from exc


def frozen_microcause_sli(dataset: str, available_columns: Sequence[str]) -> str:
    """Return the label-independent dataset SLI frozen by the adapter spec."""

    if dataset == "re2tt":
        return "ts-ui-dashboard_latency"
    if dataset == "re2ob":
        if "frontend_latency" not in available_columns and "frontend_1" in available_columns:
            return "frontend_1"
        return "frontend_latency"
    raise AdapterError("MicroCause supports only frozen RE2-OB and RE2-TT")


def validate_mmbaro_payload(payload: Mapping[str, Any]) -> None:
    missing = sorted(_MMBARO_KEYS.difference(payload))
    if missing:
        raise AdapterError("mmBARO payload missing native keys: " + ", ".join(missing))
    unexpected = sorted(set(payload).difference(_MMBARO_KEYS))
    if unexpected:
        raise AdapterError("mmBARO payload has unauthorized keys: " + ", ".join(unexpected))


def _empty_graph(value: Any) -> bool:
    if value is None:
        return False
    try:
        array = np.asarray(value)
        return array.size == 0 or bool(np.all(array == 0))
    except Exception:
        return value == []


def detect_silent_fallback(
    method: str, output: Mapping[str, Any], input_columns: Sequence[str]
) -> bool:
    """Detect audited RCAEval column-order fallbacks without judging scores."""

    if method.lower() not in {"circa", "causalrca"}:
        return False
    ranks = tuple(output.get("ranks") or ())
    node_names = tuple(output.get("node_names") or input_columns)
    return ranks == tuple(input_columns) == node_names and _empty_graph(output.get("adj"))


def validate_native_output(
    method: str, output: Mapping[str, Any], input_columns: Sequence[str] = ()
) -> tuple[str, ...]:
    """Validate only native output shape; do not complete or evaluate it."""

    if not isinstance(output, Mapping):
        raise MethodOutputError("native output must be a mapping")
    if detect_silent_fallback(method, output, input_columns):
        raise MethodOutputError("audited input-column fallback is a method failure")
    if method.lower() == "microcause" and (
        output.get("adj") is None or _empty_graph(output.get("adj"))
    ):
        raise MethodOutputError("MicroCause returned a missing or empty graph")
    ranks = output.get("ranks")
    if not isinstance(ranks, (list, tuple)) or not ranks:
        raise MethodOutputError("native ranks must be a non-empty ordered sequence")
    if any(not isinstance(item, str) or not item for item in ranks):
        raise MethodOutputError("native ranks must contain non-empty names")
    if method.lower() == "microrank" and len(ranks) > 11:
        raise MethodOutputError("pinned MicroRank output cannot exceed top_max + 6 = 11")
    return tuple(ranks)


def canonical_seed_environment(seed: int = CANONICAL_SEED) -> dict[str, str]:
    return {
        "PYTHONHASHSEED": str(seed),
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    }


def seed_in_process(seed: int = CANONICAL_SEED, include_torch: bool = True) -> None:
    """Seed in-process RNGs; workers must still start with PYTHONHASHSEED."""

    random.seed(seed)
    np.random.seed(seed)
    if include_torch:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True)


_FORBIDDEN_RECORD_KEYS = frozenset(
    {
        "rootservice",
        "faulttype",
        "rootrank",
        "ac1",
        "ac3",
        "ac5",
        "avg5",
        "mrr",
        "winner",
        "delta",
        "comparison",
        "label",
        "condition",
        "relativedirectory",
        "sourcepath",
        "injectiontarget",
    }
)


def _normalized_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def assert_firewall_safe_record(record: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                normalized = _normalized_key(key)
                if normalized in _FORBIDDEN_RECORD_KEYS:
                    raise FirewallBreach("forbidden label/performance field: " + str(key))
                walk(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                walk(nested)

    walk(record)


def assert_performance_firewall_tree(root: Path) -> None:
    """Fail closed on unauthorized B0/B1 or label-free B2 artifacts."""

    artifact_root = root / "artifacts" / "baseline_eval"
    allowed = {
        "execution_matrix_v1.json",
        "protocol_freeze_v1.json",
        "provenance_v1.json",
        "timestamp_audit_v1.json",
    }
    observed = {
        str(path.relative_to(artifact_root))
        for path in artifact_root.rglob("*")
        if path.is_file()
    }
    missing = sorted(allowed.difference(observed))
    execution_files = sorted(path for path in observed if path.startswith("execution_v1/"))
    unexpected = sorted(observed.difference(allowed).difference(execution_files))
    allowed_execution_patterns = (
        re.compile(r"execution_v1/input_manifest_v1\.json"),
        re.compile(r"execution_v1/environments/(?:baro|circa|microcause|microrank|tracerca|mmbaro|causalrca)\.json"),
        re.compile(r"execution_v1/locks/(?:baro|circa|microcause|microrank|tracerca|mmbaro|causalrca)_prediction_lock\.json"),
        re.compile(r"execution_v1/records/(?:baro|circa|microcause|microrank|tracerca|mmbaro|causalrca)/[A-Za-z0-9_.-]+/re2(?:ob|tt)/re2(?:ob|tt)-[0-9a-f]{16}\.json"),
        re.compile(r"execution_v1/prediction_lock_v1\.json"),
        re.compile(r"execution_v1/evaluation_v1\.json"),
    )
    unexpected_execution = [
        path for path in execution_files if not any(pattern.fullmatch(path) for pattern in allowed_execution_patterns)
    ]
    if unexpected or unexpected_execution or missing:
        raise FirewallBreach(
            "baseline artifact allowlist mismatch; missing={!r}, unexpected={!r}".format(
                missing, unexpected + unexpected_execution
            )
        )
    protocol = json.loads((artifact_root / "protocol_freeze_v1.json").read_text(encoding="utf-8"))
    provenance = json.loads((artifact_root / "provenance_v1.json").read_text(encoding="utf-8"))
    if protocol["performance_firewall"]["baseline_performance_exposed"]:
        raise FirewallBreach("protocol records baseline performance exposure")
    if provenance["performance_firewall"]["baseline_performance_exposed"]:
        raise FirewallBreach("provenance records baseline performance exposure")
    if protocol["performance_firewall"]["breach_status"] != "NONE":
        raise FirewallBreach("protocol contains a performance firewall breach")
    global_lock = artifact_root / "execution_v1" / "prediction_lock_v1.json"
    evaluation = artifact_root / "execution_v1" / "evaluation_v1.json"
    if evaluation.exists() and not global_lock.exists():
        raise FirewallBreach("post-lock evaluation exists without a global prediction lock")
    for relative in execution_files:
        if relative == "execution_v1/evaluation_v1.json":
            continue
        payload = json.loads((artifact_root / relative).read_text(encoding="utf-8"))
        assert_firewall_safe_record(payload)


def persist_case_record(output_directory: Path, record: CaseRecord) -> Path:
    payload = record.to_dict()
    assert_firewall_safe_record(payload)
    output_directory.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{record.method}__{record.dataset}__{record.case_id}")
    path = output_directory / f"{safe_name}.json"
    temporary = output_directory / f".{safe_name}.tmp"
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def validate_case_denominator(records: Sequence[CaseRecord], expected_case_ids: Sequence[str]) -> None:
    expected = tuple(expected_case_ids)
    observed = tuple(record.case_id for record in records)
    if len(expected) != EXPECTED_CASES_PER_DATASET or len(set(expected)) != len(expected):
        raise DenominatorError("expected case identity must contain exactly 90 unique IDs")
    if len(observed) != len(expected) or len(set(observed)) != len(observed) or set(observed) != set(expected):
        raise DenominatorError("case records must cover all 90 frozen IDs exactly once")


__all__ = [
    "AdapterError",
    "AdaptedRanking",
    "CANONICAL_SEED",
    "CaseRecord",
    "DenominatorError",
    "FirewallBreach",
    "MethodOutputError",
    "PROTOCOL_VERSION",
    "STARTING_HEAD",
    "TerminalStatus",
    "adapt_native_ranking",
    "assert_ada_rca_frozen_unchanged",
    "assert_firewall_safe_record",
    "assert_performance_firewall_tree",
    "audit_frozen_inputs",
    "canonical_seed_environment",
    "detect_silent_fallback",
    "inspect_trace_timestamp_sample",
    "is_complete_legal_ranking",
    "metric_legality",
    "mmbaro_dataset_key",
    "persist_case_record",
    "seed_in_process",
    "span_end_in_canonical_window",
    "trace_anchor_microseconds",
    "validate_case_denominator",
    "validate_mmbaro_payload",
    "validate_native_output",
]
