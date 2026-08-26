"""Case-level P4-G0 statistics and diagnostics."""

from typing import Iterable, Mapping, Sequence

import numpy as np

from .evaluator import aggregate_case_metrics, evaluate_case

FAULT_ORDER = ("cpu", "mem", "disk", "socket", "delay", "loss")


def evaluate_predictions(predictions: Iterable[Mapping[str, object]], candidates_by_case: Mapping[str, Sequence[str]], roots: Mapping[str, str]) -> Mapping[str, object]:
    case_rows = []
    for prediction in predictions:
        case_id = str(prediction["case_id"])
        root = roots[case_id]
        metrics = evaluate_case(tuple(prediction["ranking"]), root, tuple(candidates_by_case[case_id]))
        case_rows.append({**metrics, "case_id": case_id, "fault_type": prediction["fault_type"], "fold": prediction["fold"], "root_service": root})
    by_fault = {fault: aggregate_case_metrics([row for row in case_rows if row["fault_type"] == fault]) for fault in FAULT_ORDER}
    by_root = {root: aggregate_case_metrics([row for row in case_rows if row["root_service"] == root]) for root in sorted({row["root_service"] for row in case_rows})}
    by_fold = {str(fold): aggregate_case_metrics([row for row in case_rows if row["fold"] == fold]) for fold in (0, 1, 2)}
    return {"overall_cases": aggregate_case_metrics(case_rows), "by_fault": by_fault, "by_root": by_root, "by_fold": by_fold, "case_metrics": case_rows}


def paired_fault_stratified_bootstrap(left: Mapping[str, Mapping[str, object]], right: Mapping[str, Mapping[str, object]], metric: str = "Avg@5", resamples: int = 10000, seed: int = 20260826) -> Mapping[str, object]:
    if set(left) != set(right):
        raise ValueError("paired prediction case IDs differ")
    by_fault = {}
    for case_id in sorted(left):
        fault = str(left[case_id]["fault_type"])
        by_fault.setdefault(fault, []).append(float(left[case_id][metric]) - float(right[case_id][metric]))
    if set(by_fault) != set(FAULT_ORDER) or any(len(values) != 15 for values in by_fault.values()):
        raise ValueError("expected six fault strata with 15 cases each")
    rng = np.random.RandomState(seed)
    arrays = {fault: np.asarray(by_fault[fault], dtype=np.float64) for fault in FAULT_ORDER}
    samples = np.empty(int(resamples), dtype=np.float64)
    for index in range(int(resamples)):
        samples[index] = float(np.mean(np.concatenate([values[rng.randint(0, 15, 15)] for values in arrays.values()])))
    return {"metric": metric, "point_delta": float(np.mean(np.concatenate(list(arrays.values())))), "ci95": [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))], "resamples": int(resamples), "seed": int(seed), "delta_by_fault": {fault: float(np.mean(values)) for fault, values in arrays.items()}}


def factorial_effects(metrics: Mapping[str, Mapping[str, float]]) -> Mapping[str, float]:
    a0, a1, a2, a3 = (float(metrics[name]["Avg@5"]) for name in ("A0", "A1", "A2", "A3"))
    return {"A1-A0": a1 - a0, "A3-A2": a3 - a2, "A2-A0": a2 - a0, "A3-A1": a3 - a1, "interaction": (a3 - a2) - (a1 - a0)}


def gate_decision(ob: Mapping[str, float], tt: Mapping[str, float], mean_ci_lower: float, integrity_pass: bool) -> Mapping[str, object]:
    checks = {"ob_delta_positive": float(ob["Avg@5"]) > 0, "tt_delta_positive": float(tt["Avg@5"]) > 0, "mean_delta_threshold": (float(ob["Avg@5"]) + float(tt["Avg@5"])) / 2.0 >= 0.01, "ac1_guardrail": float(ob["AC@1"]) >= -0.01 and float(tt["AC@1"]) >= -0.01, "bootstrap_mean_ci_lower_positive": float(mean_ci_lower) > 0, "integrity": bool(integrity_pass)}
    return {"checks": checks, "decision": "P4-G0 PASS" if all(checks.values()) else "P4-G0 NO-GO"}
