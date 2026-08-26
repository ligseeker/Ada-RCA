"""RCAEval-aligned coarse service-level ranking metrics."""

from typing import Iterable, Mapping, Sequence


def _validate_ranking(ranking: Sequence[str], candidates: Sequence[str]) -> None:
    if tuple(ranking) and len(ranking) != len(candidates):
        raise ValueError("ranking must contain every candidate exactly once")
    if len(set(ranking)) != len(ranking) or set(ranking) != set(candidates):
        raise ValueError("ranking must be a duplicate-free candidate permutation")


def hit_at_k(ranking: Sequence[str], root_service: str, k: int) -> float:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be positive")
    if root_service not in ranking:
        raise ValueError("root service absent from ranking")
    return float(root_service in ranking[:k])


def average_at_5(ranking: Sequence[str], root_service: str) -> float:
    return sum(hit_at_k(ranking, root_service, k) for k in range(1, 6)) / 5.0


def reciprocal_rank(ranking: Sequence[str], root_service: str) -> float:
    if root_service not in ranking:
        raise ValueError("root service absent from ranking")
    return 1.0 / float(tuple(ranking).index(root_service) + 1)


def evaluate_case(ranking: Sequence[str], root_service: str, candidates: Sequence[str]) -> Mapping[str, float]:
    _validate_ranking(ranking, candidates)
    return {
        "AC@1": hit_at_k(ranking, root_service, 1),
        "AC@3": hit_at_k(ranking, root_service, 3),
        "AC@5": hit_at_k(ranking, root_service, 5),
        "Avg@5": average_at_5(ranking, root_service),
        "MRR": reciprocal_rank(ranking, root_service),
    }


def aggregate_case_metrics(rows: Iterable[Mapping[str, float]]) -> Mapping[str, float]:
    rows = tuple(rows)
    if not rows:
        raise ValueError("cannot aggregate zero cases")
    keys = ("AC@1", "AC@3", "AC@5", "Avg@5", "MRR")
    return {key: sum(float(row[key]) for row in rows) / len(rows) for key in keys}
