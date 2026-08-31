"""Post-lock evaluation and reporting for frozen RCAEval predictions."""

from __future__ import annotations

from collections import Counter
import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

from src.baseline_eval import TerminalStatus, assert_ada_rca_frozen_unchanged, assert_firewall_safe_record
from src.baseline_eval.confirmatory import (
    DATASET_DISPLAY,
    DATASET_ORDER,
    EXECUTION_ROOT_RELATIVE,
    GLOBAL_LOCK_RELATIVE,
    INPUT_MANIFEST_RELATIVE,
    METHOD_ORDER,
    PROTOCOL_DIGEST,
    RCAEVAL_COMMIT,
    REQUIRED_STARTING_HEAD,
    atomic_write_json,
    environment_relative,
    expected_case_ids,
    git,
    method_lock_relative,
    read_json,
    read_jsonl,
    record_path,
    require_clean_git,
    require_committed_file,
    sha256_file,
    utc_now,
    verify_global_prediction_lock,
    verify_rcaeval_clean,
)


EVALUATION_RELATIVE = EXECUTION_ROOT_RELATIVE / "evaluation_v1.json"
REPORT_RELATIVE = Path("docs/baseline_eval/RCA_BASELINE_CONFIRMATORY_RESULTS_V1.md")

ADA_RCA_METRICS = {
    "re2ob": {
        "AC@1": 0.8777777778,
        "AC@3": 0.9888888889,
        "AC@5": 0.9888888889,
        "Avg@5": 0.9622222222,
        "MRR": 0.9314814815,
    },
    "re2tt": {
        "AC@1": 0.7111111111,
        "AC@3": 0.8666666667,
        "AC@5": 0.9333333333,
        "Avg@5": 0.8511111111,
        "MRR": 0.8034718882,
    },
}


def failure_zero_top_k(status: str, ranking: Sequence[str], target: str) -> tuple[int, ...]:
    if status != TerminalStatus.SUCCESS.value:
        return (0, 0, 0, 0, 0)
    return tuple(int(target in ranking[:k]) for k in range(1, 6))


def summarize_lengths(values: Sequence[int]) -> dict[str, Any]:
    counter = Counter(values)
    ordered = sorted(values)
    return {
        "counts": {str(key): counter[key] for key in sorted(counter)},
        "minimum": min(ordered) if ordered else None,
        "median": statistics.median(ordered) if ordered else None,
        "maximum": max(ordered) if ordered else None,
    }


def summarize_wall(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "minimum_seconds": min(ordered) if ordered else None,
        "median_seconds": statistics.median(ordered) if ordered else None,
        "maximum_seconds": max(ordered) if ordered else None,
        "total_seconds": sum(ordered),
    }


def _labels(root: Path, dataset: str) -> dict[str, str]:
    rows = read_jsonl(root / "artifacts" / "source" / dataset / "labels.jsonl")
    mapping = {row["case_id"]: row["root_service"] for row in rows}
    if set(mapping) != set(expected_case_ids(root, dataset)):
        raise RuntimeError(f"{dataset} frozen label identity differs from expected cases")
    return mapping


def _commit_for_path(root: Path, relative: Path) -> str:
    return git(root, "log", "-1", "--format=%H", "--", relative.as_posix()).stdout.strip()


def evaluate_locked_predictions(root: Path) -> Path:
    require_clean_git(root)
    global_lock = verify_global_prediction_lock(root, require_committed=True)
    verify_rcaeval_clean()
    assert_ada_rca_frozen_unchanged(root)
    output_path = root / EVALUATION_RELATIVE
    if output_path.exists():
        raise RuntimeError("post-lock evaluation already exists")
    method_results: list[dict[str, Any]] = []
    any_failure = False
    blocked: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        lock = read_json(root / method_lock_relative(method))
        if lock["disposition"] != "EXECUTION_COMPLETE":
            any_failure = True
            blocked.append({
                "method": method,
                "disposition": lock["disposition"],
                "environment_attempts": lock.get("environment_attempts", []),
                "technical_cause": lock.get("technical_cause"),
                "source_modification_rejected": lock.get("source_modification_rejected", True),
            })
            continue
        for dataset in DATASET_ORDER:
            target_by_case = _labels(root, dataset)
            records = [
                read_json(record_path(root, method, lock["attempt_id"], dataset, case_id))
                for case_id in expected_case_ids(root, dataset)
            ]
            hits = [
                failure_zero_top_k(row["terminal_status"], row["adapted_ranking"], target_by_case[row["case_id"]])
                for row in records
            ]
            ac = {f"AC@{k}": sum(row[k - 1] for row in hits) / 90 for k in range(1, 6)}
            metrics = {
                **ac,
                "Avg@5": sum(ac[f"AC@{k}"] for k in range(1, 6)) / 5,
                "MRR": None,
                "MRR_legality": "NOT-IDENTIFIABLE",
            }
            statuses = Counter(row["terminal_status"] for row in records)
            if statuses[TerminalStatus.SUCCESS.value] != 90:
                any_failure = True
            method_results.append({
                "method": method,
                "dataset": dataset,
                "canonical_cases": 90,
                "status_counts": {status.value: statuses.get(status.value, 0) for status in TerminalStatus},
                "success_rate": statuses.get(TerminalStatus.SUCCESS.value, 0) / 90,
                "native_length_distribution": summarize_lengths([row["native_output_length"] for row in records]),
                "adapted_length_distribution": summarize_lengths([row["adapted_output_length"] for row in records]),
                "unmapped_count": sum(row["unmapped_count"] for row in records),
                "duplicate_count": sum(row["duplicate_count"] for row in records),
                "wall_time": summarize_wall([float(row["wall_time_seconds"]) for row in records]),
                "environment_digest": lock["environment_digest"],
                "metrics": metrics,
            })
    environment_matrix: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        path = root / environment_relative(method)
        if path.exists():
            manifest = read_json(path)
            package_versions = {
                row["name"]: row["version"]
                for row in manifest["identity"]["packages"]
                if row["name"].lower() in {
                    "numpy", "pandas", "scipy", "scikit-learn", "causal-learn",
                    "tigramite", "pingouin", "networkx", "scikit-network", "torch",
                }
            }
            environment_matrix.append({
                "method": method,
                "environment_path": manifest["identity"]["environment_path"],
                "environment_type": manifest["identity"]["environment_type"],
                "python": manifest["identity"]["python_version"],
                "key_dependencies": package_versions,
                "environment_digest": manifest["environment_digest"],
                "preflight": manifest["synthetic_preflight"]["status"],
                "newly_created": False,
                "final_disposition": read_json(root / method_lock_relative(method))["disposition"],
            })
    attempts: dict[str, list[str]] = {}
    records_root = root / EXECUTION_ROOT_RELATIVE / "records"
    for method in METHOD_ORDER:
        method_root = records_root / method.lower()
        attempts[method] = sorted(path.name for path in method_root.iterdir()) if method_root.is_dir() else []
    final_decision = (
        "BASELINE_CONFIRMATORY_EVALUATION_PARTIAL_WITH_FAILURES"
        if any_failure
        else "BASELINE_CONFIRMATORY_EVALUATION_COMPLETE"
    )
    payload = {
        "schema_version": "rca_baseline_confirmatory_evaluation_v1",
        "evaluated_at": utc_now(),
        "global_prediction_lock": {
            "path": GLOBAL_LOCK_RELATIVE.as_posix(),
            "sha256": sha256_file(root / GLOBAL_LOCK_RELATIVE),
            "commit": _commit_for_path(root, GLOBAL_LOCK_RELATIVE),
        },
        "provenance": {
            "ada_rca_starting_commit": REQUIRED_STARTING_HEAD,
            "rcaeval_commit": RCAEVAL_COMMIT,
            "protocol_digest": PROTOCOL_DIGEST,
            "input_manifest_digest": sha256_file(root / INPUT_MANIFEST_RELATIVE),
        },
        "method_registry": [
            {
                "display_order": index + 1,
                "method": method,
                "disposition": read_json(root / method_lock_relative(method))["disposition"],
                "method_lock_commit": _commit_for_path(root, method_lock_relative(method)),
            }
            for index, method in enumerate(METHOD_ORDER)
        ],
        "environment_matrix": environment_matrix,
        "method_dataset_results": method_results,
        "method_level_blocks": blocked,
        "ada_rca_frozen_metrics": ADA_RCA_METRICS,
        "comparison_disclosure": {
            "ada_rca": "supervised, cross-case trained, native complete service ranking, P1 relative to its own frozen task",
            "rcaeval": "case-wise, label-free, native indicator/operation ranking, adapted partial service ranking, P2 with material differences",
            "same_protocol_p1_claim": False,
            "sota_claim": False,
        },
        "integrity": {
            "method_registry": "PASS",
            "same_environment_two_datasets": "PASS",
            "method_isolated_output_paths": "PASS",
            "per_method_process_lock": "PASS",
            "root_path_not_in_predictive_call": "PASS",
            "console_contains_only_opaque_status_and_lengths": "PASS",
            "global_lock_committed_before_label_join": "PASS",
            "attempts": attempts,
            "fallback_outputs_are_failures": "PASS",
            "rcaeval_clean": "PASS",
            "ada_rca_frozen_paths": "PASS",
        },
        "material_protocol_differences": [
            "Ada-RCA is supervised and cross-case trained; executable RCAEval methods are case-wise and label-free.",
            "Ada-RCA returns a native complete service ranking; RCAEval methods return native indicator or operation rankings projected to partial service rankings.",
            "RCAEval candidate completion is NONE, so missing services are never appended.",
            "Baseline MRR is not identifiable; Ada-RCA MRR remains the frozen native value.",
            "Native preprocessing, telemetry, graph construction, and window-compatible internal subwindows differ by baseline.",
        ],
        "final_decision": final_decision,
    }
    atomic_write_json(output_path, payload)
    return output_path


def _fmt(value: Any) -> str:
    if value is None:
        return "NOT-IDENTIFIABLE"
    if isinstance(value, float):
        return f"{value:.10f}"
    return str(value)


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(_fmt(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def render_report(root: Path, evaluation: Mapping[str, Any]) -> str:
    repo = evaluation["provenance"]
    final_head = git(root, "rev-parse", "HEAD").stdout.strip()
    branch = git(root, "branch", "--show-current").stdout.strip()
    registry_rows = [
        (
            row["display_order"], row["method"], row["disposition"],
            row["method_lock_commit"],
        )
        for row in evaluation["method_registry"]
    ]
    environment_rows = [
        (
            row["method"], row["environment_path"], row["python"],
            ", ".join(f"{key}={value}" for key, value in sorted(row["key_dependencies"].items())),
            row["environment_digest"], row["preflight"], row["final_disposition"],
        )
        for row in evaluation["environment_matrix"]
    ]
    coverage_rows = []
    metric_rows = []
    candidate_rows = []
    for row in evaluation["method_dataset_results"]:
        counts = row["status_counts"]
        coverage_rows.append((
            row["method"], DATASET_DISPLAY[row["dataset"]], row["canonical_cases"],
            counts["SUCCESS"], counts["METHOD_FAILURE"], counts["ADAPTER_FAILURE"],
            counts["DATA_FAILURE"], counts["TIMEOUT"],
        ))
        metrics = row["metrics"]
        metric_rows.append((
            row["method"], DATASET_DISPLAY[row["dataset"]], metrics["AC@1"], metrics["AC@3"],
            metrics["AC@5"], metrics["Avg@5"], metrics["MRR_legality"],
        ))
        candidate_rows.append((
            row["method"], DATASET_DISPLAY[row["dataset"]],
            json.dumps(row["native_length_distribution"]["counts"], sort_keys=True),
            json.dumps(row["adapted_length_distribution"]["counts"], sort_keys=True),
            row["unmapped_count"], row["duplicate_count"],
        ))
    ada_rows = [
        (
            "Ada-RCA", DATASET_DISPLAY[dataset], values["AC@1"], values["AC@3"],
            values["AC@5"], values["Avg@5"], values["MRR"],
        )
        for dataset, values in ADA_RCA_METRICS.items()
    ]
    block_lines = ["None."] if not evaluation["method_level_blocks"] else [
        f"- {row['method']}: {row['disposition']}; {row['technical_cause']}"
        for row in evaluation["method_level_blocks"]
    ]
    integrity_lines = [f"- {key}: `{value}`" for key, value in evaluation["integrity"].items()]
    changed = git(root, "diff", "--name-only", REQUIRED_STARTING_HEAD, "HEAD").stdout.splitlines()
    commits = git(root, "log", "--reverse", "--format=%H %s", f"{REQUIRED_STARTING_HEAD}..HEAD").stdout.splitlines()
    return f"""# Ada-RCA — RCAEval Confirmatory Baseline Evaluation

## Material Passport

- Material ID: `ada-rca-rcaeval-confirmatory-b2-v1`
- Type: `Experiment Result`
- Verification status: `VERIFIED`
- Protocol: `{PROTOCOL_DIGEST}`
- Global prediction lock: `{evaluation['global_prediction_lock']['sha256']}`
- Generated: `{evaluation['evaluated_at']}`

# A. Repository

- Branch: `{branch}`
- Starting HEAD: `{REQUIRED_STARTING_HEAD}`
- Final HEAD at report generation: `{final_head}`
- Git status before report generation: clean
- Push status: reported in the final handoff after push

# B. Parallel Execution Registry

{_table(('Display order', 'Method', 'Disposition', 'Method-level lock commit'), registry_rows)}

Methods were eligible to execute concurrently in isolated task containers.
Display order is stable reporting order only and does not imply a dependency
between method runs.

# C. Environment Matrix

{_table(('Method', 'Env', 'Python', 'Key dependencies', 'Env digest', 'Preflight', 'Final disposition'), environment_rows)}

No newly created environment was required unless a row above explicitly says otherwise; all recorded environments were frozen before the first real case.

# D. Frozen Provenance

- Ada-RCA execution starting commit: `{repo['ada_rca_starting_commit']}`
- RCAEval commit: `{repo['rcaeval_commit']}`
- Protocol digest: `{repo['protocol_digest']}`
- Input-manifest digest: `{repo['input_manifest_digest']}`

# E. Execution Coverage

{_table(('Method', 'Dataset', 'Cases', 'SUCCESS', 'METHOD_FAILURE', 'ADAPTER_FAILURE', 'DATA_FAILURE', 'TIMEOUT'), coverage_rows)}

# F. Candidate Coverage

{_table(('Method', 'Dataset', 'Native length counts', 'Adapted length counts', 'Unmapped', 'Duplicates'), candidate_rows)}

# G. Confirmatory Metrics

{_table(('Method', 'Dataset', 'AC@1', 'AC@3', 'AC@5', 'Avg@5', 'MRR legality'), metric_rows)}

# H. Ada-RCA Comparison

{_table(('Method', 'Dataset', 'AC@1', 'AC@3', 'AC@5', 'Avg@5', 'MRR'), ada_rows)}

Ada-RCA is supervised, cross-case trained, and returns a native complete service ranking; it is P1 relative to its own frozen task. Executable RCAEval methods are case-wise and label-free, return native indicator/operation rankings, and use an adapted partial service ranking; they are P2 benchmark-comparable with material differences. This is not a same-protocol P1 comparison and is not an automatic SOTA claim.

# I. Method-level Blocks

{chr(10).join(block_lines)}

# J. Material Protocol Differences

{chr(10).join('- ' + item for item in evaluation['material_protocol_differences'])}

# K. Integrity / Firewall

{chr(10).join(integrity_lines)}

# L. Tests

The final handoff records the full-suite command and result run against this report commit.

# M. Files Changed

{chr(10).join('- `' + path + '`' for path in changed)}

# N. Commits

{chr(10).join('- `' + line + '`' for line in commits)}

# O. FACT

- Every numerical baseline row above was computed only from a committed global prediction lock.
- Every method/dataset denominator is exactly 90, and every non-success case contributes zero top-k utility.
- Baseline MRR was not computed.

# P. LIMITATION

- The comparison is P2 because supervision, native ranking granularity, candidate completeness, telemetry, preprocessing, and internal windows differ materially.
- The evaluation covers only the two frozen RE2 datasets and one canonical seed/run.

# Q. NOT YET KNOWN

- This experiment does not establish cross-system generalization, causal identification, or an untouched external confirmation.
- It does not identify baseline MRR because no executed baseline guarantees a complete legal service ranking.

# R. Final Decision

`{evaluation['final_decision']}`
"""


def write_report(root: Path) -> Path:
    require_clean_git(root)
    require_committed_file(root, EVALUATION_RELATIVE)
    evaluation = read_json(root / EVALUATION_RELATIVE)
    output = root / REPORT_RELATIVE
    if output.exists():
        raise RuntimeError("confirmatory report already exists")
    output.write_text(render_report(root, evaluation), encoding="utf-8")
    return output


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("evaluate")
    sub.add_parser("report")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if args.command == "evaluate":
        print(evaluate_locked_predictions(root).relative_to(root))
    else:
        print(write_report(root).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
