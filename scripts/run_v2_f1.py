#!/usr/bin/env python3
"""Run the preregistered V2-F1 aligned and misaligned OOF comparisons."""

import argparse
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

from src.rca.final_method import load_dataset, read_jsonl, sha256_file
from src.rca.p4 import fit_predict_oof, verify_complete_prediction
from src.rca.p4_stats import evaluate_predictions
from src.rca.v2_fusion import (
    F1_DIMENSION,
    F1_FEATURE_NAMES,
    MODALITY_ORDER,
    PAIR_ORDER,
    XC_FEATURE_NAMES,
    build_f1_representation,
    load_fusion_case,
)
from src.rca.v2_stats import (
    V2_METRICS,
    case_metric_map,
    f1_gate_decision,
    paired_joint_fault_bootstrap,
)


VARIANTS = (("aligned", False), ("misaligned", True))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def array_sha256(values):
    return hashlib.sha256(np.ascontiguousarray(values).view(np.uint8)).hexdigest()


def metric_macro(groups):
    return {
        metric: float(np.mean([float(values[metric]) for values in groups.values()]))
        for metric in V2_METRICS
    }


def finalize_checksums(directory):
    checksums = {
        str(path.relative_to(directory)): sha256_file(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }
    write_json(directory / "checksums.json", checksums)


def save_fit_states(run_dir, fits, source_commit):
    feature_digest = hashlib.sha256("\n".join(F1_FEATURE_NAMES).encode("utf-8")).hexdigest()
    manifest = {}
    for fold in (0, 1, 2):
        fit = fits[fold]
        path = run_dir / "model_state" / ("fold_{}.npz".format(fold))
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            weights=np.asarray(fit.weights, dtype=np.float64),
            scaler_mean=np.asarray(fit.scaler_mean, dtype=np.float64),
            scaler_scale=np.asarray(fit.scaler_scale, dtype=np.float64),
        )
        metadata = {
            "schema_version": "ada_rca_v2_f1_fold_state_v1",
            "fold": fold,
            "feature_dimension": F1_DIMENSION,
            "feature_names": list(F1_FEATURE_NAMES),
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
            "array_file": path.name,
            "array_sha256": sha256_file(path),
        }
        write_json(path.with_suffix(".json"), metadata)
        manifest[str(fold)] = metadata
    write_json(run_dir / "model_state_manifest.json", manifest)
    return feature_digest


def load_representations(dataset, misaligned, frozen_events):
    represented = {}
    feature_rows = []
    for case_id in sorted(frozen_events):
        case = load_fusion_case(PROJECT_ROOT / "artifacts" / "features" / dataset / (case_id + ".npz"))
        representation = build_f1_representation(case, misaligned=misaligned)
        if tuple(representation.event.candidates) != tuple(frozen_events[case_id].candidates):
            raise RuntimeError("candidate order changed for {}".format(case_id))
        if not np.array_equal(representation.z2, frozen_events[case_id].features):
            raise RuntimeError("F1 changed frozen Z2 for {}".format(case_id))
        represented[case_id] = representation.event
        feature_rows.append({
            "case_id": case_id,
            "candidate_count": len(case.candidates),
            "candidate_order_sha256": hashlib.sha256("\n".join(case.candidates).encode("utf-8")).hexdigest(),
            "z2_sha256": array_sha256(representation.z2),
            "xc30_sha256": array_sha256(representation.xc30),
            "f1_sha256": array_sha256(representation.event.features),
            "shifts": {key: int(value) for key, value in representation.shifts.items()},
            "all_finite": bool(np.all(np.isfinite(representation.event.features))),
        })
    return represented, feature_rows


def run_dataset(dataset, variant, misaligned, output_root, source_commit):
    frozen_events, labels, roots, assignments = load_dataset(PROJECT_ROOT, dataset)
    represented, feature_rows = load_representations(dataset, misaligned, frozen_events)
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
        row["root_rank"] = int(tuple(row["ranking"]).index(roots[case_id]) + 1)
        verify_complete_prediction(row, represented[case_id].candidates, roots[case_id])
        enriched.append(row)
    metrics = evaluate_predictions(
        enriched,
        {case_id: event.candidates for case_id, event in represented.items()},
        roots,
    )
    metrics["fault_macro"] = metric_macro(metrics["by_fault"])
    metrics["root_macro"] = metric_macro(metrics["by_root"])
    integrity = {
        "case_count": len(enriched),
        "feature_dimension": sorted({event.features.shape[1] for event in represented.values()}),
        "all_features_finite": all(np.all(np.isfinite(event.features)) for event in represented.values()),
        "complete_rankings": True,
        "root_present_all_cases": True,
        "all_folds_converged": all(fit.converged for fit in fits.values()),
        "max_gradient_norm": max(float(fit.gradient_norm) for fit in fits.values()),
        "z2_unchanged": True,
        "misalignment_integrity": all(
            row["shifts"]["M"] == 0
            and len(set(row["shifts"][modality] for modality in MODALITY_ORDER[1:])) == 3
            and all(row["shifts"][modality] != 0 for modality in MODALITY_ORDER[1:])
            for row in feature_rows
        ) if misaligned else all(all(value == 0 for value in row["shifts"].values()) for row in feature_rows),
    }
    integrity["integrity_pass"] = bool(
        integrity["case_count"] == 90
        and integrity["feature_dimension"] == [F1_DIMENSION]
        and integrity["all_features_finite"]
        and integrity["all_folds_converged"]
        and integrity["max_gradient_norm"] <= 1e-8
        and integrity["misalignment_integrity"]
    )
    if not integrity["integrity_pass"]:
        raise RuntimeError("F1 integrity failed for {} {}".format(dataset, variant))

    run_dir = output_root / dataset
    run_dir.mkdir(parents=True)
    feature_digest = save_fit_states(run_dir, fits, source_commit)
    write_jsonl(run_dir / "predictions.jsonl", enriched)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "feature_manifest.json", {
        "schema_version": "ada_rca_v2_f1_feature_manifest_v1",
        "variant": variant,
        "dataset": dataset,
        "feature_dimension": F1_DIMENSION,
        "feature_names": list(F1_FEATURE_NAMES),
        "feature_order_sha256": feature_digest,
        "case_features": feature_rows,
    })
    write_json(run_dir / "fold_assignments.json", [
        {"case_id": case_id, "fold": int(assignments[case_id])}
        for case_id in sorted(assignments)
    ])
    write_json(run_dir / "integrity.json", integrity)
    write_json(run_dir / "config.json", {
        "stage": "V2-F1",
        "variant": variant,
        "misaligned": bool(misaligned),
        "feature_dimension": F1_DIMENSION,
        "feature_names": list(F1_FEATURE_NAMES),
        "modality_order": list(MODALITY_ORDER),
        "pair_order": ["{}-{}".format(*pair) for pair in PAIR_ORDER],
        "xc_feature_names": list(XC_FEATURE_NAMES),
        "lambda": 1.0,
        "relative": False,
        "scaler": "StandardScaler fitted on training-fold candidate rows only",
        "optimizer": "src.rca.p4.fit_conditional_logit",
        "max_iter": 1000,
        "gradient_tolerance": 1e-8,
        "split": "frozen repetition 3-fold OOF",
        "misalignment_seed": 20260829 if misaligned else None,
        "misalignment_rule": "nonzero distinct SHA-256 cyclic shifts used only for XC30" if misaligned else None,
        "hyperparameter_search": False,
    })
    final_provenance = json.loads(
        (PROJECT_ROOT / "artifacts" / "final_method" / dataset / "provenance.json").read_text(encoding="utf-8")
    )
    write_json(run_dir / "provenance.json", {
        "schema_version": "ada_rca_v2_f1_run_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "protocol": "docs/V2_MULTIMODAL_FUSION_PROTOCOL_V0.1.md",
        "dataset": dataset,
        "variant": variant,
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
    return enriched, metrics, integrity


def metric_deltas(left_metrics, right_metrics):
    return {
        dataset: {
            metric: float(left_metrics[dataset]["overall_cases"][metric])
            - float(right_metrics[dataset]["overall_cases"][metric])
            for metric in V2_METRICS
        }
        for dataset in ("re2ob", "re2tt")
    }


def run(aligned_output, misaligned_output, bootstrap_output):
    source_commit = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=PROJECT_ROOT, text=True).strip()
    if subprocess.check_output(("git", "status", "--porcelain"), cwd=PROJECT_ROOT, text=True).strip():
        raise RuntimeError("V2-F1 formal run requires a clean source commit")
    targets = {
        "aligned": PROJECT_ROOT / aligned_output,
        "misaligned": PROJECT_ROOT / misaligned_output,
        "bootstrap": PROJECT_ROOT / bootstrap_output,
    }
    if any(path.exists() for path in targets.values()):
        raise FileExistsError("one or more formal F1 output directories already exist")
    parent = PROJECT_ROOT / "artifacts" / "v2"
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".f1-run-", dir=str(parent)))
    temporary_targets = {name: temporary / name for name in targets}
    try:
        predictions = {"aligned": {}, "misaligned": {}}
        metrics = {"aligned": {}, "misaligned": {}, "z2": {}}
        integrities = {"aligned": {}, "misaligned": {}}
        for variant, misaligned in VARIANTS:
            for dataset in ("re2ob", "re2tt"):
                rows, result_metrics, integrity = run_dataset(
                    dataset,
                    variant,
                    misaligned,
                    temporary_targets[variant],
                    source_commit,
                )
                predictions[variant][dataset] = rows
                metrics[variant][dataset] = result_metrics
                integrities[variant][dataset] = integrity
                print(json.dumps({
                    "dataset": dataset,
                    "variant": variant,
                    "metrics": result_metrics["overall_cases"],
                    "max_gradient_norm": integrity["max_gradient_norm"],
                }, sort_keys=True), flush=True)
        for dataset in ("re2ob", "re2tt"):
            metrics["z2"][dataset] = json.loads(
                (PROJECT_ROOT / "artifacts" / "final_method" / dataset / "metrics.json").read_text(encoding="utf-8")
            )

        case_metrics = {
            "aligned": {dataset: case_metric_map(metrics["aligned"][dataset]) for dataset in ("re2ob", "re2tt")},
            "misaligned": {dataset: case_metric_map(metrics["misaligned"][dataset]) for dataset in ("re2ob", "re2tt")},
            "z2": {dataset: case_metric_map(metrics["z2"][dataset]) for dataset in ("re2ob", "re2tt")},
        }
        comparisons = {}
        for name, left, right in (
            ("aligned_minus_z2", "aligned", "z2"),
            ("aligned_minus_misaligned", "aligned", "misaligned"),
        ):
            comparisons[name] = {
                metric: paired_joint_fault_bootstrap(
                    case_metrics[left], case_metrics[right], metric,
                    resamples=10000, seed=20260829,
                )
                for metric in V2_METRICS
            }
        deltas = {
            "aligned_minus_z2": metric_deltas(metrics["aligned"], metrics["z2"]),
            "aligned_minus_misaligned": metric_deltas(metrics["aligned"], metrics["misaligned"]),
        }
        integrity_pass = all(
            integrities[variant][dataset]["integrity_pass"]
            for variant in ("aligned", "misaligned")
            for dataset in ("re2ob", "re2tt")
        ) and all(
            json.loads((PROJECT_ROOT / "artifacts" / "final_method" / dataset / "replay_audit.json").read_text(encoding="utf-8"))["integrity_status"] == "INTEGRITY_VALID"
            for dataset in ("re2ob", "re2tt")
        )
        decision = f1_gate_decision(
            comparisons["aligned_minus_z2"]["Avg@5"],
            comparisons["aligned_minus_misaligned"]["Avg@5"],
            deltas,
            integrity_pass,
        )
        bootstrap_dir = temporary_targets["bootstrap"]
        bootstrap_dir.mkdir(parents=True)
        write_json(bootstrap_dir / "comparisons.json", comparisons)
        write_json(bootstrap_dir / "metric_deltas.json", deltas)
        write_json(bootstrap_dir / "gate_decision.json", decision)
        write_json(bootstrap_dir / "config.json", {
            "stage": "V2-F1",
            "resamples": 10000,
            "seed": 20260829,
            "sampling_unit": "paired failure case",
            "stratification": "six fault types, 15 cases each",
            "dataset_order": ["re2ob", "re2tt"],
            "equal_dataset_mean": True,
            "percentile_ci": [2.5, 97.5],
            "metrics": list(V2_METRICS),
        })
        write_json(bootstrap_dir / "provenance.json", {
            "schema_version": "ada_rca_v2_f1_bootstrap_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_commit": source_commit,
            "protocol": "docs/V2_MULTIMODAL_FUSION_PROTOCOL_V0.1.md",
            "aligned_prediction_sha256": {
                dataset: sha256_file(temporary_targets["aligned"] / dataset / "predictions.jsonl")
                for dataset in ("re2ob", "re2tt")
            },
            "misaligned_prediction_sha256": {
                dataset: sha256_file(temporary_targets["misaligned"] / dataset / "predictions.jsonl")
                for dataset in ("re2ob", "re2tt")
            },
            "z2_prediction_sha256": {
                dataset: sha256_file(PROJECT_ROOT / "artifacts" / "final_method" / dataset / "predictions.jsonl")
                for dataset in ("re2ob", "re2tt")
            },
        })
        finalize_checksums(bootstrap_dir)
        for variant in ("aligned", "misaligned"):
            write_json(temporary_targets[variant] / "run_manifest.json", {
                "schema_version": "ada_rca_v2_f1_variant_v1",
                "variant": variant,
                "source_commit": source_commit,
                "datasets": ["re2ob", "re2tt"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            finalize_checksums(temporary_targets[variant])
        for name, target in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary_targets[name].replace(target)
        temporary.rmdir()
    except Exception:
        print("partial F1 output retained at {}".format(temporary), file=sys.stderr)
        raise
    print(json.dumps({"stage": "V2-F1", "decision": decision["V2_F1"], "integrity_pass": integrity_pass}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aligned-output", default="artifacts/v2/f1_concordance")
    parser.add_argument("--misaligned-output", default="artifacts/v2/f1_misaligned")
    parser.add_argument("--bootstrap-output", default="artifacts/v2/bootstrap/f1")
    args = parser.parse_args()
    run(args.aligned_output, args.misaligned_output, args.bootstrap_output)


if __name__ == "__main__":
    main()
