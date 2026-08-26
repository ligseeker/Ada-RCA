#!/usr/bin/env python3
"""Run the frozen label-free magnitude-inversion diagnostic."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
import subprocess

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def git_output(*args):
    return subprocess.check_output(("git",) + args, cwd=str(PROJECT_ROOT), text=True).strip()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rank_magnitude(path: Path, candidates):
    with np.load(path) as data:
        scores = np.asarray(data["a"], dtype=float)
    order = np.argsort(-scores, kind="stable")
    ranking = [candidates[index] for index in order]
    return ranking, scores


def audit_dataset(key: str, root: Path):
    bundle = root / "source" / key
    feature_bundle = root / "features" / key
    inputs = {row["case_id"]: row for row in read_jsonl(bundle / "inputs.jsonl")}
    labels = {row["case_id"]: row for row in read_jsonl(bundle / "labels.jsonl")}
    rows = []
    for case_id in sorted(inputs):
        candidates = tuple(inputs[case_id]["candidates"])
        ranking, scores = rank_magnitude(feature_bundle / (case_id + ".npz"), candidates)
        root_service = labels[case_id]["root_service"]
        rank = ranking.index(root_service) + 1
        rows.append({
            "case_id": case_id,
            "fault_type": labels[case_id]["fault_type"],
            "root_service": root_service,
            "root_magnitude_rank": rank,
            "mi_1": rank > 1,
            "mi_3": rank > 3,
            "ranking": ranking,
            "magnitude_scores": {service: float(scores[index]) for index, service in enumerate(candidates)},
        })
    faults = sorted({row["fault_type"] for row in rows})
    by_fault = {}
    for fault in faults:
        selected = [row for row in rows if row["fault_type"] == fault]
        by_fault[fault] = {
            "cases": len(selected),
            "mi_1_count": sum(row["mi_1"] for row in selected),
            "mi_1_ratio": sum(row["mi_1"] for row in selected) / len(selected),
            "mi_3_count": sum(row["mi_3"] for row in selected),
            "mi_3_ratio": sum(row["mi_3"] for row in selected) / len(selected),
            "root_rank_distribution": dict(sorted(Counter(str(row["root_magnitude_rank"]) for row in selected).items(), key=lambda item: int(item[0]))),
        }
    summary = {
        "dataset": key,
        "case_count": len(rows),
        "candidate_count": len(inputs[next(iter(inputs))]["candidates"]),
        "mi_1_count": sum(row["mi_1"] for row in rows),
        "mi_1_ratio": sum(row["mi_1"] for row in rows) / len(rows),
        "mi_3_count": sum(row["mi_3"] for row in rows),
        "mi_3_ratio": sum(row["mi_3"] for row in rows) / len(rows),
        "root_rank_distribution": dict(sorted(Counter(str(row["root_magnitude_rank"]) for row in rows).items(), key=lambda item: int(item[0]))),
        "by_fault": by_fault,
        "cases": rows,
    }
    return summary


def write_doc(report, output: Path):
    lines = [
        "# Magnitude-Inversion Audit",
        "",
        "The frozen service magnitude is `A_i = mean over available channels of min(20, post-event magnitude)`. Rankings sort decreasing magnitude with canonical registry order for exact ties. This audit is label-free during score computation; labels are joined only for evaluation.",
        "",
        "MI-1 means the true root is not rank 1. MI-3 means the true root rank is greater than 3. The terms are neutral diagnostics and do not imply propagated symptoms.",
        "",
    ]
    for key in ("re2ob", "re2tt"):
        row = report[key]
        lines.extend([
            "## {}".format(key.upper()), "",
            "Overall: MI-1 `{}/{:.4f}`; MI-3 `{}/{:.4f}`.".format(row["mi_1_count"], row["mi_1_ratio"], row["mi_3_count"], row["mi_3_ratio"]),
            "",
            "| Fault | Cases | MI-1 count/ratio | MI-3 count/ratio | Root rank distribution |",
            "|---|---:|---:|---:|---|",
        ])
        for fault in ("cpu", "mem", "disk", "socket", "delay", "loss"):
            sub = row["by_fault"][fault]
            lines.append("| {} | {} | {}/{:.4f} | {}/{:.4f} | {} |".format(fault.upper(), sub["cases"], sub["mi_1_count"], sub["mi_1_ratio"], sub["mi_3_count"], sub["mi_3_ratio"], sub["root_rank_distribution"]))
        lines.extend(["", "Root rank distribution: `{}`.".format(row["root_rank_distribution"]), ""])
    lines.append("MI audit is diagnostic and does not replace the full benchmark or the P3-G1 gate.")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", default="artifacts")
    args = parser.parse_args()
    status = git_output("status", "--short")
    allowed_outputs = ("artifacts/audits/", "docs/MAGNITUDE_INVERSION_AUDIT.md")
    unrelated = [line for line in status.splitlines() if not any(token in line for token in allowed_outputs)]
    if unrelated:
        raise RuntimeError("formal P3-A1 audit requires committed code: {}".format(unrelated))
    root = PROJECT_ROOT / args.artifact_root
    report = {key: audit_dataset(key, root) for key in ("re2ob", "re2tt")}
    report["execution"] = {
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_branch": git_output("branch", "--show-current"),
        "command": "PYTHONPATH=. python3 scripts/p3_a1_magnitude_audit.py --artifact-root artifacts",
        "representation_commit": "7cd6d418a114978b33838e788346febbeae71818",
        "feature_artifact_commit": "4fdea9da691ca738ffb706d3cc2141c7cca6f796",
    }
    output = root / "audits" / "magnitude_inversion.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_doc(report, PROJECT_ROOT / "docs" / "MAGNITUDE_INVERSION_AUDIT.md")
    print(json.dumps({key: {"mi1": report[key]["mi_1_count"], "mi3": report[key]["mi_3_count"], "cases": report[key]["case_count"]} for key in ("re2ob", "re2tt")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
