#!/usr/bin/env python3
"""Frozen, small-budget nested OOF optimization over canonical V1 features."""
import json
import platform
import sys
from pathlib import Path
from itertools import product

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.rca.final_method import load_dataset
from src.rca.p4 import CandidateEvent, fit_conditional_logit, rank_candidates
from src.rca.p4_stats import evaluate_predictions

CHANNELS = ("metric", "log", "trace-error", "trace-latency")
CHANNEL_INDEX = {name: i for i, name in enumerate(CHANNELS)}
REPRESENTATIONS = {
    "Z1-M": ("metric",),
    "M+L": ("metric", "log"),
    "M+TE": ("metric", "trace-error"),
    "M+TL": ("metric", "trace-latency"),
    "M+L+TL": ("metric", "log", "trace-latency"),
    "FULL-Z2": CHANNELS,
}
LAMBDA_GRID = (0.1, 1.0, 10.0)
TOP_K = 3
SEED = 20260829


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def slice_event(event, channels):
    indices = []
    for ch in channels:
        start = CHANNEL_INDEX[ch] * 17
        indices.extend(range(start, start + 17))
    return CandidateEvent(event.case_id, event.candidates, event.features[:, indices])


def predict(fit, events, fold):
    rows = []
    for event in events:
        scores = fit.scores(event.features)
        rows.append({"case_id": event.case_id, "fold": fold,
                     "candidate_scores": {c: float(scores[i]) for i, c in enumerate(event.candidates)},
                     "ranking": list(rank_candidates(event.candidates, scores))})
    return rows


def score_rows(rows, roots, events):
    return evaluate_predictions(rows, {e.case_id: e.candidates for e in events}, roots)["overall_cases"]


def inner_splits(ids, folds=3):
    return [{"train": [x for i, x in enumerate(ids) if i % folds != f],
             "valid": [x for i, x in enumerate(ids) if i % folds == f]} for f in range(folds)]


def fit_score(rep_events, ids_train, roots, lam, outer_fold):
    events = [rep_events[x] for x in ids_train]
    fit = fit_conditional_logit(events, roots, l2_lambda=lam, max_iter=1000, gradient_tolerance=1e-8)
    return fit, fit.gradient_norm


def select_config(raw_events, roots, labels, outer_train_ids):
    ordered = sorted(outer_train_ids)
    splits = inner_splits(ordered, 3)
    rep_scores = []
    for rep_name, channels in REPRESENTATIONS.items():
        rep_events = {cid: slice_event(raw_events[cid], channels) for cid in ordered}
        vals = []
        for split in splits:
            fit, _ = fit_score(rep_events, split["train"], roots, 1.0, -1)
            rows = predict(fit, [rep_events[x] for x in split["valid"]], -1)
            for row in rows:
                row["fault_type"] = labels[row["case_id"]]["fault_type"]
            vals.append(score_rows(rows, roots, [rep_events[x] for x in split["valid"]])["Avg@5"])
        rep_scores.append((float(np.mean(vals)), rep_name, vals))
    rep_scores.sort(key=lambda x: (-x[0], x[1]))
    top = [x[1] for x in rep_scores[:TOP_K]]
    candidates = []
    trace = {"representation_screen": [{"representation": n, "mean_Avg@5": s, "fold_scores": v} for s, n, v in rep_scores], "top_k": top}
    for rep_name in top:
        channels = REPRESENTATIONS[rep_name]
        rep_events = {cid: slice_event(raw_events[cid], channels) for cid in ordered}
        for lam in LAMBDA_GRID:
            vals = []
            ac1_vals = []
            for split in splits:
                fit, _ = fit_score(rep_events, split["train"], roots, lam, -1)
                rows = predict(fit, [rep_events[x] for x in split["valid"]], -1)
                for row in rows:
                    row["fault_type"] = labels[row["case_id"]]["fault_type"]
                metrics = score_rows(rows, roots, [rep_events[x] for x in split["valid"]])
                vals.append(metrics["Avg@5"])
                ac1_vals.append(metrics["AC@1"])
            candidates.append({"representation": rep_name, "ranker": "R0-ConditionalLogit",
                               "lambda": lam, "mean_Avg@5": float(np.mean(vals)), "fold_scores": vals,
                               "AC@1_mean": float(np.mean(ac1_vals))})
    candidates.sort(key=lambda x: (-x["mean_Avg@5"], -x["AC@1_mean"], x["lambda"], x["representation"]))
    chosen = candidates[0]
    trace["ranker_grid"] = candidates
    trace["chosen"] = chosen
    return chosen, trace


def run_dataset(dataset, output_root):
    events, labels, roots, assignments = load_dataset(ROOT, dataset)
    outer_rows, selections = [], []
    for fold in (0, 1, 2):
        train_ids = sorted(cid for cid, f in assignments.items() if f != fold)
        test_ids = sorted(cid for cid, f in assignments.items() if f == fold)
        chosen, trace = select_config(events, roots, labels, train_ids)
        channels = REPRESENTATIONS[chosen["representation"]]
        rep_events = {cid: slice_event(events[cid], channels) for cid in events}
        fit, grad = fit_score(rep_events, train_ids, roots, chosen["lambda"], fold)
        preds = predict(fit, [rep_events[x] for x in test_ids], fold)
        for row in preds:
            row["fault_type"] = labels[row["case_id"]]["fault_type"]
            row["root_service"] = roots[row["case_id"]]
        outer_rows.extend(preds)
        selections.append({"outer_fold": fold, "outer_train_event_ids": train_ids,
                           "outer_test_event_ids": test_ids, "selected": chosen,
                           "ranker": "R0-ConditionalLogit", "ensemble": None,
                           "inner_selection_trace": trace, "gradient_norm": float(grad),
                           "selection_event_ids": sorted(set(train_ids))})
    out = ROOT / output_root / dataset
    out.mkdir(parents=True, exist_ok=True)
    metrics = evaluate_predictions(outer_rows, {cid: e.candidates for cid, e in events.items()}, roots)
    write(out / "config.json", {"dataset": dataset, "protocol": "OPT-DEVELOPMENT-NESTED-OOF",
        "outer_folds": 3, "inner_folds": 3, "top_k_representations": TOP_K,
        "rankers": {"R0-ConditionalLogit": {"available": True, "lambda": list(LAMBDA_GRID)},
                     "R1-XGBoost": {"available": False, "reason": "dependency unavailable"},
                     "R2-LightGBM": {"available": False, "reason": "dependency unavailable"}},
        "ensemble": {"allowed": True, "selected": False, "alphas": [0, .25, .5, .75, 1]},
        "seed": SEED})
    write(out / "feature_names.json", {"representations": {n: [f"{c}.{i}" for c in ch for i in range(17)] for n, ch in REPRESENTATIONS.items()}})
    write(out / "selection_trace.json", selections)
    write(out / "metrics.json", metrics)
    (out / "outer_predictions.csv").write_text("case_id,fold,root_service,fault_type,root_rank\n" + "".join(
        f"{r['case_id']},{r['fold']},{r['root_service']},{r['fault_type']},{r['ranking'].index(r['root_service'])+1}\n" for r in outer_rows), encoding="utf-8")
    write(out / "versions.json", {"python": platform.python_version(), "numpy": np.__version__, "seed": SEED})
    return metrics, selections


def main():
    for ds in ("re2ob", "re2tt"):
        metrics, selections = run_dataset(ds, "artifacts/opt/o4_nested")
        print(ds, json.dumps(metrics["overall_cases"], sort_keys=True))


if __name__ == "__main__":
    main()
