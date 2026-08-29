"""Preregistered paired statistics and gates for Ada-RCA V2."""

from typing import Mapping

import numpy as np

from .p4_stats import FAULT_ORDER


DATASET_ORDER = ("re2ob", "re2tt")
V2_METRICS = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")


def case_metric_map(metrics: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    return {str(row["case_id"]): row for row in metrics["case_metrics"]}


def paired_joint_fault_bootstrap(
    left_by_dataset: Mapping[str, Mapping[str, Mapping[str, object]]],
    right_by_dataset: Mapping[str, Mapping[str, Mapping[str, object]]],
    metric: str,
    resamples: int = 10000,
    seed: int = 20260829,
) -> Mapping[str, object]:
    if metric not in V2_METRICS:
        raise ValueError("unsupported V2 metric")
    deltas = {}
    for dataset in DATASET_ORDER:
        left = left_by_dataset[dataset]
        right = right_by_dataset[dataset]
        if set(left) != set(right):
            raise ValueError("paired case IDs differ for {}".format(dataset))
        by_fault = {}
        for case_id in sorted(left):
            if str(left[case_id]["fault_type"]) != str(right[case_id]["fault_type"]):
                raise ValueError("paired fault labels differ")
            fault = str(left[case_id]["fault_type"])
            by_fault.setdefault(fault, []).append(
                float(left[case_id][metric]) - float(right[case_id][metric])
            )
        if set(by_fault) != set(FAULT_ORDER) or any(len(by_fault[fault]) != 15 for fault in FAULT_ORDER):
            raise ValueError("expected six 15-case fault strata")
        deltas[dataset] = {
            fault: np.asarray(by_fault[fault], dtype=np.float64)
            for fault in FAULT_ORDER
        }

    rng = np.random.RandomState(seed)
    samples = {dataset: np.empty(int(resamples), dtype=np.float64) for dataset in DATASET_ORDER}
    equal_samples = np.empty(int(resamples), dtype=np.float64)
    for index in range(int(resamples)):
        for dataset in DATASET_ORDER:
            sampled = np.concatenate([
                values[rng.randint(0, 15, 15)]
                for values in (deltas[dataset][fault] for fault in FAULT_ORDER)
            ])
            samples[dataset][index] = float(np.mean(sampled))
        equal_samples[index] = float(np.mean([samples[dataset][index] for dataset in DATASET_ORDER]))

    result = {
        "metric": metric,
        "resamples": int(resamples),
        "seed": int(seed),
        "datasets": {},
    }
    points = []
    for dataset in DATASET_ORDER:
        all_deltas = np.concatenate([deltas[dataset][fault] for fault in FAULT_ORDER])
        point = float(np.mean(all_deltas))
        points.append(point)
        result["datasets"][dataset] = {
            "point_delta": point,
            "ci95": [
                float(np.percentile(samples[dataset], 2.5)),
                float(np.percentile(samples[dataset], 97.5)),
            ],
            "delta_by_fault": {
                fault: float(np.mean(deltas[dataset][fault]))
                for fault in FAULT_ORDER
            },
        }
    result["equal_dataset_mean"] = {
        "point_delta": float(np.mean(points)),
        "ci95": [
            float(np.percentile(equal_samples, 2.5)),
            float(np.percentile(equal_samples, 97.5)),
        ],
    }
    return result


def f1_gate_decision(performance_bootstrap, mechanism_bootstrap, metric_deltas, integrity_pass):
    def ac1_guard(delta):
        threshold = -1.0 / 90.0
        value = float(delta)
        return value >= threshold or bool(np.isclose(value, threshold, rtol=0.0, atol=1e-15))

    performance_checks = {
        "ob_avg5_nonnegative": float(metric_deltas["aligned_minus_z2"]["re2ob"]["Avg@5"]) >= 0.0,
        "tt_avg5_nonnegative": float(metric_deltas["aligned_minus_z2"]["re2tt"]["Avg@5"]) >= 0.0,
        "at_least_one_avg5_strict_positive": any(
            float(metric_deltas["aligned_minus_z2"][dataset]["Avg@5"]) > 0.0
            for dataset in DATASET_ORDER
        ),
        "equal_dataset_avg5_ci_lower_positive": float(performance_bootstrap["equal_dataset_mean"]["ci95"][0]) > 0.0,
        "ob_ac1_guard": ac1_guard(metric_deltas["aligned_minus_z2"]["re2ob"]["AC@1"]),
        "tt_ac1_guard": ac1_guard(metric_deltas["aligned_minus_z2"]["re2tt"]["AC@1"]),
        "integrity": bool(integrity_pass),
    }
    mechanism_checks = {
        "ob_avg5_strict_positive": float(metric_deltas["aligned_minus_misaligned"]["re2ob"]["Avg@5"]) > 0.0,
        "tt_avg5_strict_positive": float(metric_deltas["aligned_minus_misaligned"]["re2tt"]["Avg@5"]) > 0.0,
        "equal_dataset_avg5_ci_lower_positive": float(mechanism_bootstrap["equal_dataset_mean"]["ci95"][0]) > 0.0,
        "integrity": bool(integrity_pass),
    }
    performance_go = all(performance_checks.values())
    mechanism_go = all(mechanism_checks.values())
    return {
        "performance_checks": performance_checks,
        "mechanism_checks": mechanism_checks,
        "PERFORMANCE_GO": performance_go,
        "MECHANISM_GO": mechanism_go,
        "V2_F1": "GO" if performance_go and mechanism_go else "NO_GO",
    }
