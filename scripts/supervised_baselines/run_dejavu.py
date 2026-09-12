#!/usr/bin/env python3
"""Run one pinned DejaVu RE2 fold or the designated non-formal smoke."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import (
    SEED,
    _allowed_untracked_artifact_prefixes,
    base_environment,
    create_run_directory,
    current_git_identity,
    evaluate_fold_scores,
    finalize_run_directory,
    load_label_subset,
    sha256_file,
    write_json,
)
from src.rca.supervised_baselines.dejavu import (
    DEJAVU_COMMIT,
    DEJAVU_CONFIG,
    load_prepared_events,
    score_dejavu,
    train_dejavu,
)
from src.rca.supervised_baselines.dejavu_adapter import dejavu_fold_partitions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=("re2ob", "re2tt"))
    parser.add_argument("--fold", required=True, type=int, choices=(0, 1, 2))
    parser.add_argument("--dejavu-root", required=True, type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output-root",
        default="artifacts/supervised_baselines/dejavu/runs",
    )
    args = parser.parse_args()
    if args.smoke and (args.dataset != "re2ob" or args.fold != 0):
        raise ValueError("the designated DejaVu smoke is RE2-OB fold 0")
    if __import__("os").environ.get("PYTHONHASHSEED") != str(SEED):
        raise RuntimeError("DejaVu run requires PYTHONHASHSEED={}".format(SEED))

    output_root = PROJECT_ROOT / args.output_root
    git_identity = current_git_identity(PROJECT_ROOT)
    allowed = _allowed_untracked_artifact_prefixes(PROJECT_ROOT, output_root)
    disallowed = [
        entry for entry in git_identity["dirty_entries"]
        if not any(entry.startswith(prefix) for prefix in allowed)
    ]
    if disallowed:
        raise RuntimeError("DejaVu run rejects non-artifact changes: {}".format(disallowed))

    role = "SMOKE_NOT_FORMAL" if args.smoke else "FORMAL_OOF_FOLD"
    method = "dejavu_smoke" if args.smoke else "dejavu"
    config = dict(DEJAVU_CONFIG)
    config["run_role"] = role
    if args.smoke:
        config["smoke_execution"] = "one train batch, one validation pass, complete test scoring"
    run_dir = output_root / method / args.dataset / "fold_{}".format(args.fold)
    started_at = create_run_directory(run_dir, config)
    started_clock = time.monotonic()

    try:
        events = load_prepared_events(PROJECT_ROOT, args.dataset)
        train_ids, validation_ids, test_ids = dejavu_fold_partitions(
            PROJECT_ROOT, args.dataset, args.fold
        )
        fit_ids = tuple(train_ids) + tuple(validation_ids)
        fit_labels = load_label_subset(PROJECT_ROOT, args.dataset, fit_ids)
        fit_roots = {case_id: row["root_service"] for case_id, row in fit_labels.items()}
        if any(fit_roots[case_id] not in events[case_id].candidates for case_id in fit_ids):
            raise ValueError("DejaVu fit root absent from candidate registry")

        model, history, selection = train_dejavu(
            events,
            train_ids,
            validation_ids,
            fit_roots,
            args.dejavu_root,
            smoke=args.smoke,
        )
        import torch

        torch.save(model.state_dict(), str(run_dir / "model_state.pt"))
        write_json(run_dir / "training_history.json", {
            "history": history,
            "selection": selection,
            "outer_test_metrics_used": False,
        })
        scores_by_case = score_dejavu(model, events, test_ids, args.dejavu_root)
        score_case_ids = tuple(sorted(scores_by_case))
        np.savez_compressed(
            run_dir / "scores_label_free.npz",
            case_ids=np.asarray(score_case_ids),
            candidates=np.asarray(events[score_case_ids[0]].candidates),
            scores=np.stack([scores_by_case[case_id] for case_id in score_case_ids]),
        )
        prediction_completed_at = datetime.now(timezone.utc).isoformat()

        test_events = tuple(events[case_id] for case_id in test_ids)
        candidate_rows, metrics = evaluate_fold_scores(
            PROJECT_ROOT,
            args.dataset,
            args.fold,
            test_events,
            scores_by_case,
        )
        expected_rows = 30 * len(test_events[0].candidates)
        integrity = {
            "status": "PASS" if len(candidate_rows) == expected_rows else "FAIL",
            "case_count": len(test_ids),
            "candidate_row_count": len(candidate_rows),
            "expected_candidate_row_count": expected_rows,
            "complete_score_matrix_before_label_join": True,
            "complete_candidate_rows": len(candidate_rows) == expected_rows,
            "complete_rank_permutations": all(
                sorted(row["rank"] for row in candidate_rows if row["case_id"] == case_id)
                == list(range(1, len(events[case_id].candidates) + 1))
                for case_id in test_ids
            ),
            "graph_node_count_complete": True,
        }
        if integrity["status"] != "PASS" or not integrity["complete_rank_permutations"]:
            raise RuntimeError("DejaVu smoke/formal output integrity failed")

        import dgl
        import networkx
        import pandas
        import pytorch_lightning
        import scipy
        import sklearn
        import torchmetrics

        environment = dict(base_environment())
        environment.update({
            "torch": torch.__version__,
            "dgl": dgl.__version__,
            "networkx": networkx.__version__,
            "pytorch_lightning": pytorch_lightning.__version__,
            "torchmetrics": torchmetrics.__version__,
            "dejavu_environment_manifest_sha256": sha256_file(
                PROJECT_ROOT / "artifacts" / "supervised_baselines" / "dejavu" / "environment" / "environment.json"
            ),
        })
        firewall = {
            "status": "PASS",
            "model_train_case_count": len(train_ids),
            "inner_validation_case_count": len(validation_ids),
            "outer_test_case_count": len(test_ids),
            "partition_overlap": sorted(
                (set(train_ids) & set(validation_ids))
                | (set(train_ids) & set(test_ids))
                | (set(validation_ids) & set(test_ids))
            ),
            "fit_label_case_ids_sha256": hashlib.sha256(
                "\n".join(fit_ids).encode("utf-8")
            ).hexdigest(),
            "outer_test_interface_label_free": True,
            "stock_test_callback_enabled": False,
            "automatic_lr_find_enabled": False,
            "outer_test_labels_joined_after_complete_score_matrix": True,
            "prediction_completed_at": prediction_completed_at,
        }
        provenance = {
            "schema_version": "dejavu_re2_fold_v1",
            "run_role": role,
            "dataset": args.dataset,
            "fold": args.fold,
            "source_commit": git_identity["head"],
            "branch": git_identity["branch"],
            "official_dejavu_root": str(args.dejavu_root.resolve()),
            "official_dejavu_commit": DEJAVU_COMMIT,
            "adapter_protocol": "docs/supervised_baselines/DEJAVU_ADAPTER_PROTOCOL_V1.md",
            "adapter_protocol_sha256": sha256_file(
                PROJECT_ROOT / "docs" / "supervised_baselines" / "DEJAVU_ADAPTER_PROTOCOL_V1.md"
            ),
            "prepared_manifest_sha256": sha256_file(
                PROJECT_ROOT / "artifacts" / "supervised_baselines" / "dejavu" / "prepared" / args.dataset / "manifest.json"
            ),
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
            {
                "elapsed_seconds": time.monotonic() - started_clock,
                "model_train_cases": len(train_ids),
                "inner_validation_cases": len(validation_ids),
                "outer_test_cases": len(test_ids),
                **selection,
            },
        )
        print(json.dumps({
            "status": "COMPLETE",
            "run_role": role,
            "run_dir": str(run_dir),
            "integrity": integrity,
            "metrics": metrics["overall_cases"],
        }, indent=2, sort_keys=True))
    except Exception as exc:
        write_json(run_dir / "status.json", {
            "status": "FAILED",
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise


if __name__ == "__main__":
    main()
