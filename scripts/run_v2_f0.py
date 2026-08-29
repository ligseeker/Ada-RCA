#!/usr/bin/env python3
"""Run the preregistered V2-F0 descriptive modality audit."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np
import scipy
import sklearn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.features import CHANNELS
from src.rca.final_method import (
    FINAL_Z2_FEATURE_NAMES,
    compare_predictions,
    load_dataset,
    read_jsonl,
    sha256_file,
)
from src.rca.p4 import CandidateEvent, fit_predict_oof, verify_complete_prediction
from src.rca.p4_stats import FAULT_ORDER, evaluate_predictions


MODALITIES = ("M", "L", "TE", "TL")
MODALITY_CHANNELS = dict(zip(MODALITIES, CHANNELS))
VARIANT_MODALITIES = (
    ("M", ("M",)),
    ("L", ("L",)),
    ("TE", ("TE",)),
    ("TL", ("TL",)),
    ("M+L", ("M", "L")),
    ("M+TE", ("M", "TE")),
    ("M+TL", ("M", "TL")),
    ("L+TE", ("L", "TE")),
    ("L+TL", ("L", "TL")),
    ("TE+TL", ("TE", "TL")),
    ("FULL-M", ("L", "TE", "TL")),
    ("FULL-L", ("M", "TE", "TL")),
    ("FULL-TE", ("M", "L", "TL")),
    ("FULL-TL", ("M", "L", "TE")),
    ("FULL-Z2", MODALITIES),
)
VARIANT_NAMES = tuple(name for name, _ in VARIANT_MODALITIES)
SINGLE_VARIANTS = MODALITIES
PAIR_VARIANTS = ("M+L", "M+TE", "M+TL", "L+TE", "L+TL", "TE+TL")
LEAVE_ONE_OUT_VARIANTS = ("FULL-M", "FULL-L", "FULL-TE", "FULL-TL")
METRICS = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def feature_indices(modalities):
    indices = []
    for modality in modalities:
        channel_index = MODALITIES.index(modality)
        indices.extend(range(channel_index * 17, (channel_index + 1) * 17))
    return tuple(indices)


def feature_names(modalities):
    return tuple(FINAL_Z2_FEATURE_NAMES[index] for index in feature_indices(modalities))


def select_event(event, modalities):
    return CandidateEvent(
        event.case_id,
        event.candidates,
        event.features[:, feature_indices(modalities)],
    )


def metric_macro(groups):
    return {
        metric: float(np.mean([float(values[metric]) for values in groups.values()]))
        for metric in METRICS
    }


def root_rank(prediction, root):
    return int(tuple(prediction["ranking"]).index(root) + 1)


def save_fit_states(run_dir, fits, names, source_commit):
    feature_digest = hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
    manifest = {}
    for fold in (0, 1, 2):
        fit = fits[fold]
        array_path = run_dir / "model_state" / ("fold_{}.npz".format(fold))
        array_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            array_path,
            weights=np.asarray(fit.weights, dtype=np.float64),
            scaler_mean=np.asarray(fit.scaler_mean, dtype=np.float64),
            scaler_scale=np.asarray(fit.scaler_scale, dtype=np.float64),
        )
        metadata = {
            "schema_version": "ada_rca_v2_f0_fold_state_v1",
            "fold": fold,
            "feature_dimension": len(names),
            "feature_names": list(names),
            "feature_order_sha256": feature_digest,
            "lambda": 1.0,
            "optimizer": "src.rca.p4.fit_conditional_logit",
            "gradient_tolerance": 1e-8,
            "initial_loss": float(fit.initial_loss),
            "final_loss": float(fit.final_loss),
            "gradient_norm": float(fit.gradient_norm),
            "iterations": int(fit.iterations),
            "converged": bool(fit.converged),
            "message": str(fit.message),
            "source_commit": source_commit,
            "array_file": array_path.name,
            "array_sha256": sha256_file(array_path),
        }
        write_json(array_path.with_suffix(".json"), metadata)
        manifest[str(fold)] = metadata
    write_json(run_dir / "model_state_manifest.json", manifest)
    return feature_digest


def finalize_checksums(directory):
    checksums = {
        str(path.relative_to(directory)): sha256_file(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }
    write_json(directory / "checksums.json", checksums)


def load_availability_coverage(dataset, labels):
    by_case = {}
    for case_id in sorted(labels):
        with np.load(PROJECT_ROOT / "artifacts" / "features" / dataset / (case_id + ".npz")) as data:
            base = np.asarray(data["base"], dtype=np.float64)
        by_case[case_id] = {
            modality: {
                "availability_candidate_mean": float(np.mean(base[:, index, 7])),
                "coverage_candidate_mean": float(np.mean(base[:, index, 6])),
            }
            for index, modality in enumerate(MODALITIES)
        }
    summary = {}
    for modality in MODALITIES:
        availability = [by_case[case_id][modality]["availability_candidate_mean"] for case_id in sorted(by_case)]
        coverage = [by_case[case_id][modality]["coverage_candidate_mean"] for case_id in sorted(by_case)]
        summary[modality] = {
            "candidate_row_availability_mean": float(np.mean(availability)),
            "event_modality_availability_mean": float(np.mean(availability)),
            "candidate_row_coverage_mean": float(np.mean(coverage)),
            "event_modality_coverage_mean": float(np.mean(coverage)),
            "event_availability_min": float(np.min(availability)),
            "event_availability_max": float(np.max(availability)),
            "event_coverage_min": float(np.min(coverage)),
            "event_coverage_max": float(np.max(coverage)),
        }
    return by_case, summary


def run_variant(dataset, variant, modalities, events, labels, roots, assignments, output_root, source_commit):
    represented = {case_id: select_event(event, modalities) for case_id, event in events.items()}
    started = time.time()
    predictions, fits = fit_predict_oof(
        represented,
        roots,
        assignments,
        relative=False,
        l2_lambda=1.0,
        max_iter=1000,
        gradient_tolerance=1e-8,
    )
    elapsed = time.time() - started
    enriched = []
    for raw in predictions:
        row = dict(raw)
        case_id = str(row["case_id"])
        row["fault_type"] = str(labels[case_id]["fault_type"])
        row["root_service"] = roots[case_id]
        row["root_rank"] = root_rank(row, roots[case_id])
        verify_complete_prediction(row, represented[case_id].candidates, roots[case_id])
        enriched.append(row)
    metrics = evaluate_predictions(
        enriched,
        {case_id: event.candidates for case_id, event in represented.items()},
        roots,
    )
    metrics["fault_macro"] = metric_macro(metrics["by_fault"])
    metrics["root_macro"] = metric_macro(metrics["by_root"])
    if not all(fit.converged and fit.gradient_norm <= 1e-8 for fit in fits.values()):
        raise RuntimeError("F0 optimizer integrity failed for {} {}".format(dataset, variant))

    run_dir = output_root / variant / dataset
    run_dir.mkdir(parents=True)
    names = feature_names(modalities)
    feature_digest = save_fit_states(run_dir, fits, names, source_commit)
    write_jsonl(run_dir / "predictions.jsonl", enriched)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "fold_assignments.json", [
        {"case_id": case_id, "fold": int(assignments[case_id])}
        for case_id in sorted(assignments)
    ])
    write_json(run_dir / "config.json", {
        "stage": "V2-F0",
        "dataset": dataset,
        "variant": variant,
        "modalities": list(modalities),
        "modality_order": list(MODALITIES),
        "feature_dimension": len(names),
        "feature_names": list(names),
        "feature_order_sha256": feature_digest,
        "lambda": 1.0,
        "relative": False,
        "scaler": "StandardScaler fitted on training-fold candidate rows only",
        "optimizer": "src.rca.p4.fit_conditional_logit",
        "max_iter": 1000,
        "gradient_tolerance": 1e-8,
        "split": "frozen repetition 3-fold OOF",
        "model_selection": False,
    })
    final_provenance = json.loads(
        (PROJECT_ROOT / "artifacts" / "final_method" / dataset / "provenance.json").read_text(encoding="utf-8")
    )
    write_json(run_dir / "provenance.json", {
        "schema_version": "ada_rca_v2_f0_run_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "protocol": "docs/V2_MULTIMODAL_FUSION_PROTOCOL_V0.1.md",
        "dataset": dataset,
        "dataset_tree_sha256": final_provenance["dataset_tree_sha256"],
        "source_manifest_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "source" / dataset / "manifest.json"),
        "feature_manifest_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "features" / dataset / "manifest.json"),
        "split_manifest_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "splits" / dataset / "split_manifest.json"),
        "assignment_sha256": sha256_file(PROJECT_ROOT / "artifacts" / "splits" / dataset / "assignments.json"),
    })
    write_json(run_dir / "environment.json", {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "platform": platform.platform(),
    })
    write_json(run_dir / "runtime.json", {
        "elapsed_seconds": elapsed,
        "case_count": len(enriched),
        "candidate_row_count": sum(len(row["ranking"]) for row in enriched),
    })
    finalize_checksums(run_dir)
    return enriched, metrics


def build_descriptive_audit(output_root, predictions_by_dataset, metrics_by_dataset, availability):
    table_rows = []
    rank_rows = []
    disagreements = {}
    corrections = {}
    leave_one_out = {}
    for dataset in ("re2ob", "re2tt"):
        predictions = predictions_by_dataset[dataset]
        for variant in VARIANT_NAMES:
            metrics = metrics_by_dataset[dataset][variant]
            table_rows.append({
                "dataset": dataset,
                "variant": variant,
                **{metric: float(metrics["overall_cases"][metric]) for metric in METRICS},
                "fault_macro_Avg@5": float(metrics["fault_macro"]["Avg@5"]),
                "root_macro_Avg@5": float(metrics["root_macro"]["Avg@5"]),
            })
        case_ids = sorted(predictions["FULL-Z2"])
        for case_id in case_ids:
            reference = predictions["FULL-Z2"][case_id]
            rank_rows.append({
                "dataset": dataset,
                "case_id": case_id,
                "fault_type": reference["fault_type"],
                "root_service": reference["root_service"],
                "fold": int(reference["fold"]),
                **{variant: int(predictions[variant][case_id]["root_rank"]) for variant in VARIANT_NAMES},
            })

        disagreements[dataset] = {}
        for left, right in (("M", "L"), ("M", "TE"), ("M", "TL"), ("L", "TE"), ("L", "TL"), ("TE", "TL")):
            signed = np.asarray([
                predictions[left][case_id]["root_rank"] - predictions[right][case_id]["root_rank"]
                for case_id in case_ids
            ], dtype=np.float64)
            disagreements[dataset]["{}-{}".format(left, right)] = {
                "mean_signed_rank_difference": float(np.mean(signed)),
                "mean_absolute_rank_difference": float(np.mean(np.abs(signed))),
                "nonzero_disagreement_count": int(np.count_nonzero(signed)),
                "case_count": len(case_ids),
            }

        corrections[dataset] = {"relative_to_full_z2": {}, "family_unique_rank1": {}}
        for variant in VARIANT_NAMES[:-1]:
            cases = [
                case_id for case_id in case_ids
                if predictions[variant][case_id]["root_rank"] == 1
                and predictions["FULL-Z2"][case_id]["root_rank"] > 1
            ]
            corrections[dataset]["relative_to_full_z2"][variant] = {"count": len(cases), "case_ids": cases}
        for family_name, family in (("single", SINGLE_VARIANTS), ("pair", PAIR_VARIANTS), ("leave_one_out", LEAVE_ONE_OUT_VARIANTS)):
            unique = {}
            for case_id in case_ids:
                winners = [variant for variant in family if predictions[variant][case_id]["root_rank"] == 1]
                if len(winners) == 1:
                    unique.setdefault(winners[0], []).append(case_id)
            corrections[dataset]["family_unique_rank1"][family_name] = {
                variant: {"count": len(unique.get(variant, [])), "case_ids": unique.get(variant, [])}
                for variant in family
            }

        leave_one_out[dataset] = {}
        for variant in LEAVE_ONE_OUT_VARIANTS:
            changes = np.asarray([
                predictions[variant][case_id]["root_rank"] - predictions["FULL-Z2"][case_id]["root_rank"]
                for case_id in case_ids
            ], dtype=np.int64)
            leave_one_out[dataset][variant] = {
                "improved_count": int(np.sum(changes < 0)),
                "unchanged_count": int(np.sum(changes == 0)),
                "degraded_count": int(np.sum(changes > 0)),
                "mean_signed_rank_change": float(np.mean(changes)),
                "mean_absolute_rank_change": float(np.mean(np.abs(changes))),
            }

    with (output_root / "metrics_table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(table_rows[0]))
        writer.writeheader()
        writer.writerows(table_rows)
    with (output_root / "case_root_rank_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rank_rows[0]))
        writer.writeheader()
        writer.writerows(rank_rows)
    write_json(output_root / "modality_pair_root_rank_disagreement.json", disagreements)
    write_json(output_root / "rank1_corrections.json", corrections)
    write_json(output_root / "leave_one_out_transitions.json", leave_one_out)
    write_json(output_root / "modality_availability_coverage.json", availability)
    write_json(output_root / "audit_summary.json", {
        "stage": "V2-F0",
        "status": "DESCRIPTIVE_ONLY",
        "variant_order": list(VARIANT_NAMES),
        "modality_order": list(MODALITIES),
        "metrics": table_rows,
        "model_selection_authorized": False,
    })
    finalize_checksums(output_root)


def run(output_root):
    source_commit = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip()
    if subprocess.check_output(("git", "status", "--porcelain"), cwd=PROJECT_ROOT, text=True).strip():
        raise RuntimeError("V2-F0 formal run requires a clean source commit")
    final_root = PROJECT_ROOT / output_root
    if final_root.exists():
        raise FileExistsError("formal F0 artifact directory already exists: {}".format(final_root))
    final_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".f0_modality_audit-", dir=str(final_root.parent)))
    try:
        predictions_by_dataset = {}
        metrics_by_dataset = {}
        availability = {}
        for dataset in ("re2ob", "re2tt"):
            events, labels, roots, assignments = load_dataset(PROJECT_ROOT, dataset)
            availability_by_case, availability_summary = load_availability_coverage(dataset, labels)
            availability[dataset] = {
                "by_case": availability_by_case,
                "summary": availability_summary,
            }
            predictions_by_dataset[dataset] = {}
            metrics_by_dataset[dataset] = {}
            for variant, modalities in VARIANT_MODALITIES:
                rows, metrics = run_variant(
                    dataset, variant, modalities, events, labels, roots,
                    assignments, temporary, source_commit,
                )
                predictions_by_dataset[dataset][variant] = {row["case_id"]: row for row in rows}
                metrics_by_dataset[dataset][variant] = metrics
                print(json.dumps({
                    "dataset": dataset,
                    "variant": variant,
                    "metrics": metrics["overall_cases"],
                    "max_gradient_norm": max(
                        json.loads((temporary / variant / dataset / "model_state" / ("fold_{}.json".format(fold))).read_text())["gradient_norm"]
                        for fold in (0, 1, 2)
                    ),
                }, sort_keys=True), flush=True)
            full_rows = list(predictions_by_dataset[dataset]["FULL-Z2"].values())
            committed = read_jsonl(PROJECT_ROOT / "artifacts" / "final_method" / dataset / "predictions.jsonl")
            identity = compare_predictions(full_rows, committed)
            if not identity["ranking_identical"] or identity["max_abs_score_difference"] > 1e-12:
                raise RuntimeError("F0 FULL-Z2 does not replay V1 for {}".format(dataset))
            write_json(temporary / ("{}_v1_identity.json".format(dataset)), identity)
        build_descriptive_audit(
            temporary,
            predictions_by_dataset,
            metrics_by_dataset,
            availability,
        )
        temporary.replace(final_root)
    except Exception:
        print("partial F0 output retained at {}".format(temporary), file=sys.stderr)
        raise
    print(json.dumps({"stage": "V2-F0", "status": "COMPLETED", "output": str(final_root)}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="artifacts/v2/f0_modality_audit")
    args = parser.parse_args()
    run(args.output_root)


if __name__ == "__main__":
    main()
