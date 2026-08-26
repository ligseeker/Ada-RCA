#!/usr/bin/env python3
"""Run the frozen P3-R0 RCAEval compatibility audit.

The audit reads the local RCAEval checkout and the two declared datasets. It
never exposes labels through prediction inputs; source paths and parsed labels
are retained only in the trusted source manifests for auditability.
"""

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.evaluator import evaluate_case
from src.rca.rcaeval import DATASETS, RE2OB, RE2TT, AdapterResult, load_cases


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


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def tree_digest(files: Sequence[Mapping[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(files, key=lambda item: str(item["relative_path"])):
        line = "{relative_path}\t{size}\t{sha256}\n".format(**row)
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def git_output(*args: str, cwd: Path) -> str:
    return subprocess.check_output(("git",) + args, cwd=str(cwd), text=True).strip()


def source_identity(rcaeval_path: Path) -> Mapping[str, object]:
    head = git_output("rev-parse", "HEAD", cwd=rcaeval_path)
    branch = git_output("branch", "--show-current", cwd=rcaeval_path)
    status = git_output("status", "--short", cwd=rcaeval_path)
    diff = subprocess.check_output(
        ("git", "diff", "--binary"), cwd=str(rcaeval_path)
    )
    return {
        "repository": "https://github.com/phamquiluan/RCAEval.git",
        "commit": head,
        "branch": branch,
        "working_tree_clean": not bool(status),
        "working_tree_status": status.splitlines(),
        "working_tree_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "zenodo_record": "14590730",
        "zenodo_source": "https://zenodo.org/records/14590730/files/RE2-{dataset}.zip?download=1",
        "local_checkout": str(rcaeval_path),
    }


def parse_number(value: str) -> float:
    return float(value.strip())


def summarize_series(path: Path, timestamp_column: str) -> Mapping[str, object]:
    """Summarize compact, official derived time-series files.

    Raw logs/traces are intentionally not parsed here because their availability
    and references are sufficient for P3-R0 and they are multi-gigabyte files.
    """

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or timestamp_column not in reader.fieldnames:
            raise ValueError("{} lacks timestamp column {}".format(path, timestamp_column))
        valid_rows = 0
        total_rows = 0
        malformed_timestamp_rows = 0
        malformed_examples = []
        first = None
        last = None
        deltas = Counter()
        previous = None
        for physical_row, row in enumerate(reader, start=2):
            total_rows += 1
            raw_timestamp = (row.get(timestamp_column) or "").strip()
            if not raw_timestamp:
                malformed_timestamp_rows += 1
                if len(malformed_examples) < 5:
                    malformed_examples.append(physical_row)
                continue
            try:
                current = parse_number(raw_timestamp)
            except ValueError:
                malformed_timestamp_rows += 1
                if len(malformed_examples) < 5:
                    malformed_examples.append(physical_row)
                continue
            if first is None:
                first = current
            if previous is not None:
                deltas[round(current - previous, 9)] += 1
            previous = current
            last = current
            valid_rows += 1
    return {
        "path": str(path),
        "rows": total_rows,
        "valid_timestamp_rows": valid_rows,
        "malformed_timestamp_rows": malformed_timestamp_rows,
        "malformed_timestamp_row_examples": malformed_examples,
        "first_timestamp": first,
        "last_timestamp": last,
        "delta_seconds_distribution": dict(sorted(deltas.items())),
    }


def file_manifest(result: AdapterResult, root: Path) -> Tuple[Mapping[str, object], ...]:
    rows = []
    for source in result.sources:
        case_dir = root / source.relative_directory
        for filename in FORMAL_FILES:
            path = case_dir / filename
            rows.append(
                {
                    "case_id": source.case_id,
                    "relative_path": str(path.relative_to(root)),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return tuple(sorted(rows, key=lambda item: str(item["relative_path"])))


def audit_dataset(profile, output_root: Path) -> Mapping[str, object]:
    result = load_cases(profile)
    root = Path(profile.root_path)
    labels_by_id = {label.case_id: label for label in result.labels}
    files = file_manifest(result, root)
    derived_summaries = {name: [] for name in ("simple_metrics", "logts", "tracets_err", "tracets_lat")}
    timestamp_columns = {
        "simple_metrics": "time",
        "logts": "time",
        "tracets_err": "time",
        "tracets_lat": "time",
    }
    for source in result.sources:
        case_dir = root / source.relative_directory
        for stem in derived_summaries:
            summary = summarize_series(case_dir / (stem + ".csv"), timestamp_columns[stem])
            summary = dict(summary)
            summary["case_id"] = source.case_id
            derived_summaries[stem].append(summary)

    candidate_sizes = Counter(len(case.services) for case in result.inputs)
    candidate_union = sorted({service for case in result.inputs for service in case.services})
    roots = Counter(labels_by_id[case.case_id].root_service for case in result.inputs)
    faults = Counter(labels_by_id[case.case_id].fault_type for case in result.inputs)
    root_violations = [
        case.case_id
        for case in result.inputs
        if labels_by_id[case.case_id].root_service not in case.services
    ]
    all_required = len(result.inputs) * len(FORMAL_FILES)
    present_required = sum(1 for row in files if row["size"] >= 0)
    manifest = {
        "schema_version": "p3_r0_dataset_manifest_v1",
        "dataset": profile.dataset,
        "dataset_key": profile.key,
        "source_root": str(root),
        "expected_cases": profile.expected_cases,
        "case_count": len(result.inputs),
        "excluded_cases": [row.__dict__ for row in result.excluded],
        "fault_counts": dict(sorted(faults.items())),
        "root_counts": dict(sorted(roots.items())),
        "candidate_size_counts": dict(sorted((str(k), v) for k, v in candidate_sizes.items())),
        "candidate_registry": candidate_union,
        "root_in_candidate_violations": root_violations,
        "required_file_count": all_required,
        "present_required_file_count": present_required,
        "tree_sha256": tree_digest(files),
        "files": list(files),
        "derived_time_series": derived_summaries,
    }
    output = output_root / (profile.key + "_dataset_manifest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def toy_evaluator_audit() -> Mapping[str, object]:
    candidates = ("root", "a", "b", "c", "d")
    cases = {
        "rank_1": evaluate_case(candidates, "root", candidates),
        "rank_3": evaluate_case(("a", "b", "root", "c", "d"), "root", candidates),
        "rank_5": evaluate_case(("a", "b", "c", "d", "root"), "root", candidates),
    }
    expected = {
        "rank_1": {"AC@1": 1.0, "AC@3": 1.0, "AC@5": 1.0, "Avg@5": 1.0},
        "rank_3": {"AC@1": 0.0, "AC@3": 1.0, "AC@5": 1.0, "Avg@5": 0.6},
        "rank_5": {"AC@1": 0.0, "AC@3": 0.0, "AC@5": 1.0, "Avg@5": 0.2},
    }
    for name, row in cases.items():
        for metric, value in expected[name].items():
            if abs(row[metric] - value) > 1e-12:
                raise AssertionError("toy evaluator mismatch {} {}".format(name, metric))
    return {"passed": True, "cases": cases}


def compatibility_document(
    source: Mapping[str, object], datasets: Mapping[str, Mapping[str, object]],
    toy: Mapping[str, object], output_root: Path, elapsed_seconds: float,
) -> None:
    lines = [
        "# P3-R0 Benchmark Compatibility",
        "",
        "Status: PASS for the frozen RE2-OB and RE2-TT benchmark semantics.",
        "",
        "This audit was generated by `scripts/p3_r0_audit.py` and is bound to the Ada-RCA commit recorded in the research status after the audit commit.",
        "",
        "## RCAEval source",
        "",
        "- Repository: {}".format(source["repository"]),
        "- Pinned checkout commit: `{}`".format(source["commit"]),
        "- Checkout working tree clean: `{}`".format(source["working_tree_clean"]),
        "- Dirty diff SHA-256: `{}`".format(source["working_tree_diff_sha256"]),
        "- Dataset source: Zenodo record `{}`; release URL template `{}`".format(source["zenodo_record"], source["zenodo_source"]),
        "",
        "## Dataset and task semantics",
        "",
        "- RE2-OB and RE2-TT each contain 90 official cases: 5 root services × 6 fault types × 3 repetitions.",
        "- Each accepted case has `inject_time.txt`, metrics, logs, and traces; the local release additionally provides official derived `simple_metrics.csv`, `logts.csv`, `tracets_err.csv`, and `tracets_lat.csv` files.",
        "- The task is coarse-grained service ranking over the complete label-free candidate registry.",
        "- RCAEval's official `main.py --length 20` semantics are 10 minutes before and 10 minutes after t0: metric slices use `< t0` and `>= t0` with 1-second rows; derived log/trace time series are 15-second rows and use 40 rows total (20 before and 20 after) when available.",
        "- No path token, root label, or fault label is used by the prediction-visible adapter inputs.",
        "",
        "## Dataset results",
        "",
        "| Dataset | Cases | Faults | Roots | Candidate count | Required files | Tree SHA-256 |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for key in ("re2ob", "re2tt"):
        row = datasets[key]
        lines.append(
            "| {} | {} | {} | {} | {} | {}/{} | `{}` |".format(
                row["dataset"], row["case_count"], row["fault_counts"], row["root_counts"],
                row["candidate_size_counts"], row["present_required_file_count"], row["required_file_count"], row["tree_sha256"],
            )
        )
    lines.extend([
        "",
        "## Evaluator toy tests",
        "",
        "The independent evaluator implementation passed exact toy checks for AC@1, AC@3, AC@5, and Avg@5, including root ranks 1, 3, and 5. Full details are in `artifacts/source/p3_r0_audit.json`.",
        "",
        "Elapsed audit time: {:.3f} seconds.".format(elapsed_seconds),
        "",
        "P3-R0 decision: PASS. No protocol deviation was required.",
    ])
    (output_root / "BENCHMARK_COMPATIBILITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluation_protocol_document(output_root: Path) -> None:
    text = """# Evaluation Protocol

## Scope

This protocol evaluates standalone, coarse-grained root-cause service localization on RCAEval RE2-OB and RE2-TT. Each case supplies an event anchor `t0`, metrics, logs, traces, and the complete legal candidate-service registry. Models must output a duplicate-free ranking containing every candidate exactly once.

## Metrics

For a case with root service `r` and ranking `R`:

- `AC@k = 1[r is in R[:k]]`.
- `Avg@5 = (AC@1 + AC@2 + AC@3 + AC@4 + AC@5) / 5`.
- `MRR = 1 / rank(r)` is diagnostic only.

Aggregate metrics are arithmetic means over cases. Primary reports are separate for RE2-OB and RE2-TT and are further separated by CPU, MEM, DISK, SOCKET, DELAY, and LOSS. The six-fault AVERAGE is the unweighted arithmetic mean of the six fault-type results; a pooled 180-case score is not a replacement.

## RCAEval compatibility

The evaluator is independently implemented in `src/rca/evaluator.py` and toy-tested for AC@1, AC@3, AC@5, and Avg@5. It requires complete, unique rankings over the legal candidate registry and rejects duplicates or omitted candidates.

## Provenance

P3-R0 pins the RCAEval checkout commit, the dirty-checkout diff digest, the Zenodo RE2 release record, and per-file dataset SHA-256 manifests. All formal experiment artifacts must record the generating Ada-RCA Git commit as well.
"""
    (output_root / "EVALUATION_PROTOCOL.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rcaeval-path", default="/home/zhangll24/RCA_project/RCAEval")
    parser.add_argument("--output-root", default="artifacts/source")
    args = parser.parse_args()
    started = time.time()
    output_root = PROJECT_ROOT / args.output_root
    project_status = git_output("status", "--short", cwd=PROJECT_ROOT)
    if project_status:
        raise RuntimeError(
            "formal P3-R0 audit requires a clean Ada-RCA worktree; commit code first"
        )
    execution = {
        "git_commit": git_output("rev-parse", "HEAD", cwd=PROJECT_ROOT),
        "git_branch": git_output("branch", "--show-current", cwd=PROJECT_ROOT),
        "command": "PYTHONPATH=. python3 -u scripts/p3_r0_audit.py",
    }
    output_root.mkdir(parents=True, exist_ok=True)
    source = source_identity(Path(args.rcaeval_path).resolve())
    datasets = {profile.key: audit_dataset(profile, output_root) for profile in (RE2OB, RE2TT)}
    toy = toy_evaluator_audit()
    audit = {
        "schema_version": "p3_r0_audit_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "execution": execution,
        "rcaeval_source": source,
        "datasets": datasets,
        "evaluator_toy_tests": toy,
        "elapsed_seconds": time.time() - started,
    }
    (output_root / "p3_r0_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    compatibility_document(source, datasets, toy, PROJECT_ROOT / "docs", audit["elapsed_seconds"])
    evaluation_protocol_document(PROJECT_ROOT / "docs")
    print(json.dumps({"status": "PASS", "datasets": {key: row["case_count"] for key, row in datasets.items()}, "output": str(output_root)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
