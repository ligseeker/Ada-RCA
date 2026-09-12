"""Pure case-level diagnostics for the Ada-RCA Z2-XGB closure."""

from typing import Mapping, Sequence

from ..p4_stats import FAULT_ORDER, paired_fault_stratified_bootstrap


TRANSITIONS = ("improved", "unchanged", "degraded")


def classify_rank_transition(new_rank: int, old_rank: int) -> str:
    """Classify a root-rank change using the preregistered direction."""

    if int(new_rank) < int(old_rank):
        return "improved"
    if int(new_rank) == int(old_rank):
        return "unchanged"
    return "degraded"


def _empty_counts():
    return {name: 0 for name in TRANSITIONS}


def summarize_rank_transitions(
    new_records: Mapping[str, Mapping[str, object]],
    old_records: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object]:
    """Return overall, fault, root, fold, and case-level rank transitions."""

    if set(new_records) != set(old_records):
        raise ValueError("rank-transition case IDs differ")
    overall = _empty_counts()
    by_fault = {fault: _empty_counts() for fault in FAULT_ORDER}
    by_root = {}
    by_fold = {str(fold): _empty_counts() for fold in (0, 1, 2)}
    case_rows = []
    for case_id in sorted(new_records):
        new = new_records[case_id]
        old = old_records[case_id]
        for key in ("fault_type", "root_service", "fold"):
            if str(new[key]) != str(old[key]):
                raise ValueError("{} metadata differs for {}".format(key, case_id))
        new_rank = int(new["root_rank"])
        old_rank = int(old["root_rank"])
        transition = classify_rank_transition(new_rank, old_rank)
        fault = str(new["fault_type"])
        root = str(new["root_service"])
        fold = str(new["fold"])
        if fault not in by_fault:
            raise ValueError("unexpected fault type: {}".format(fault))
        if fold not in by_fold:
            raise ValueError("unexpected fold: {}".format(fold))
        by_root.setdefault(root, _empty_counts())
        overall[transition] += 1
        by_fault[fault][transition] += 1
        by_root[root][transition] += 1
        by_fold[fold][transition] += 1
        case_rows.append({
            "case_id": case_id,
            "new_root_rank": new_rank,
            "old_root_rank": old_rank,
            "transition": transition,
            "fault_type": fault,
            "root_service": root,
            "fold": int(fold),
        })
    return {
        "case_count": len(case_rows),
        "overall": overall,
        "by_fault": by_fault,
        "by_root": by_root,
        "by_fold": by_fold,
        "case_rows": case_rows,
    }


def paired_metric_statistics(
    left_records: Mapping[str, Mapping[str, object]],
    right_records: Mapping[str, Mapping[str, object]],
    left_name: str,
    right_name: str,
    metrics: Sequence[str] = ("Avg@5", "AC@1", "MRR"),
    resamples: int = 10000,
    seed: int = 20260826,
) -> Mapping[str, object]:
    """Run the frozen paired fault-stratified bootstrap for each metric."""

    if set(left_records) != set(right_records):
        raise ValueError("paired metric case IDs differ")
    result = {}
    for metric in metrics:
        statistic = paired_fault_stratified_bootstrap(
            left_records,
            right_records,
            metric=metric,
            resamples=resamples,
            seed=seed,
        )
        result[metric] = {
            "left": left_name,
            "right": right_name,
            "direction": "{} - {}".format(left_name, right_name),
            **statistic,
        }
    return result
