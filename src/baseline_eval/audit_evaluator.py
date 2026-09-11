"""Frozen dual service-level evaluators for the baseline audit.

This module is deliberately separate from the immutable V1/V2 evaluators.  It
does not run a method and does not change a prediction record.  It only
projects an already persisted native ranking under two explicitly named
protocols:

``unique_service``
    Reuse the frozen repository adapter.  The first mapped occurrence of each
    legal service is retained and unmapped items are omitted.

``rcaeval_service_slot``
    Map every native slot with the same frozen alias/prefix rule, retain slot
    positions (including ``None`` for an unmapped item), and do not deduplicate
    services before Top-K membership is checked.  This is the slot-level
    semantic exposed by the pinned RCAEval ``Evaluator`` class.

Both protocols use the fixed 90-case denominator supplied by the caller.  A
failure contributes five zero hits, but a missing, duplicate, or foreign case
ID is an audit error rather than a silently shortened denominator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.baseline_eval import AdapterError, TerminalStatus, adapt_native_ranking


PROTOCOL_VERSION = "RCA_BASELINE_AUDIT_FIX_DUAL_EVALUATION_V1"
PROTOCOLS = ("unique_service", "rcaeval_service_slot")
METRICS = ("AC@1", "AC@2", "AC@3", "AC@4", "AC@5")
EXPECTED_DENOMINATOR = 90


class DualEvaluationError(ValueError):
    """Persisted evidence cannot be evaluated under the frozen contract."""


@dataclass(frozen=True)
class CaseEvaluation:
    """Two protocol projections and raw per-case utility for one case."""

    status: str
    native_ranking: tuple[str, ...]
    unique_service_ranking: tuple[str, ...]
    rcaeval_service_slots: tuple[str | None, ...]
    unique_hits: tuple[int, ...]
    rcaeval_slot_hits: tuple[int, ...]
    root_rank_unique: int | None
    root_rank_slot: int | None
    affected_k: tuple[int, ...]
    dedup_changed: bool

    def protocol_hits(self, protocol: str) -> tuple[int, ...]:
        if protocol == "unique_service":
            return self.unique_hits
        if protocol == "rcaeval_service_slot":
            return self.rcaeval_slot_hits
        raise DualEvaluationError(f"unknown dual-evaluation protocol: {protocol}")


def _slot_projection(
    native_ranking: Sequence[str], candidates: Sequence[str]
) -> tuple[str | None, ...]:
    """Apply the frozen adapter mapping one native slot at a time.

    ``adapt_native_ranking`` is the single source of truth for alias and
    longest-prefix behavior.  Calling it on one item preserves the item's
    native position while converting an unmapped item to a non-matching slot.
    """

    slots: list[str | None] = []
    for item in native_ranking:
        try:
            projected = adapt_native_ranking((item,), candidates)
        except AdapterError:
            slots.append(None)
        else:
            slots.append(projected.services[0])
    return tuple(slots)


def _first_rank(values: Sequence[str | None], target: str) -> int | None:
    for index, value in enumerate(values, start=1):
        if value == target:
            return index
    return None


def _hits(values: Sequence[str | None], target: str) -> tuple[int, ...]:
    return tuple(int(target in values[:k]) for k in range(1, 6))


def evaluate_case(
    *,
    status: str,
    native_ranking: Sequence[str],
    target: str,
    candidates: Sequence[str],
) -> CaseEvaluation:
    """Evaluate one persisted case without changing its native ranking."""

    normalized_status = str(status)
    native = tuple(native_ranking)
    if normalized_status != TerminalStatus.SUCCESS.value:
        zero = (0, 0, 0, 0, 0)
        return CaseEvaluation(
            status=normalized_status,
            native_ranking=native,
            unique_service_ranking=(),
            rcaeval_service_slots=(),
            unique_hits=zero,
            rcaeval_slot_hits=zero,
            root_rank_unique=None,
            root_rank_slot=None,
            affected_k=(),
            dedup_changed=False,
        )

    if not native:
        raise DualEvaluationError("SUCCESS case has an empty native ranking")
    unique = adapt_native_ranking(native, candidates).services
    slots = _slot_projection(native, candidates)
    unique_hits = _hits(unique, target)
    slot_hits = _hits(slots, target)
    affected = tuple(
        k for k, (unique_hit, slot_hit) in enumerate(zip(unique_hits, slot_hits), start=1)
        if unique_hit != slot_hit
    )
    mapped_slots = tuple(value for value in slots if value is not None)
    return CaseEvaluation(
        status=normalized_status,
        native_ranking=native,
        unique_service_ranking=unique,
        rcaeval_service_slots=slots,
        unique_hits=unique_hits,
        rcaeval_slot_hits=slot_hits,
        root_rank_unique=_first_rank(unique, target),
        root_rank_slot=_first_rank(slots, target),
        affected_k=affected,
        dedup_changed=unique != mapped_slots,
    )


def aggregate_hits(
    case_evaluations: Sequence[CaseEvaluation],
    *,
    protocol: str,
    expected_denominator: int = EXPECTED_DENOMINATOR,
) -> dict[str, Any]:
    """Aggregate raw hits with no intermediate rounding."""

    if protocol not in PROTOCOLS:
        raise DualEvaluationError(f"unknown dual-evaluation protocol: {protocol}")
    if len(case_evaluations) != expected_denominator:
        raise DualEvaluationError(
            f"{protocol} requires denominator {expected_denominator}, "
            f"observed {len(case_evaluations)}"
        )
    hits = [row.protocol_hits(protocol) for row in case_evaluations]
    hit_counts = {
        f"hit@{k}": sum(row[k - 1] for row in hits) for k in range(1, 6)
    }
    metrics = {
        f"AC@{k}": hit_counts[f"hit@{k}"] / expected_denominator
        for k in range(1, 6)
    }
    avg_numerator = sum(hit_counts.values())
    metrics["Avg@5"] = avg_numerator / (5 * expected_denominator)
    return {
        "protocol": protocol,
        "denominator": expected_denominator,
        "hit_counts": hit_counts,
        "avg_at_5_numerator": avg_numerator,
        "metrics": metrics,
        "status_counts": _status_counts(case_evaluations),
    }


def _status_counts(case_evaluations: Sequence[CaseEvaluation]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in case_evaluations:
        counts[row.status] = counts.get(row.status, 0) + 1
    return dict(sorted(counts.items()))


def validate_case_identity(
    case_ids: Sequence[str], expected_case_ids: Sequence[str], *, denominator: int = EXPECTED_DENOMINATOR
) -> None:
    """Require the exact frozen case universe before metric aggregation."""

    observed = tuple(case_ids)
    expected = tuple(expected_case_ids)
    if len(expected) != denominator or len(set(expected)) != denominator:
        raise DualEvaluationError("expected case universe is not exactly the frozen denominator")
    if len(observed) != denominator or len(set(observed)) != denominator:
        raise DualEvaluationError("records contain missing or duplicate case IDs")
    if set(observed) != set(expected):
        raise DualEvaluationError("records contain a foreign or missing case ID")


def evaluate_records(
    records: Sequence[Mapping[str, Any]],
    labels: Mapping[str, str],
    candidates: Sequence[str],
    expected_case_ids: Sequence[str],
    *,
    denominator: int = EXPECTED_DENOMINATOR,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Evaluate records under both protocols after exact case-ID validation."""

    case_ids = [str(row.get("case_id")) for row in records]
    validate_case_identity(case_ids, expected_case_ids, denominator=denominator)
    by_id = {str(row["case_id"]): row for row in records}
    ordered_rows: list[dict[str, Any]] = []
    evaluations: list[CaseEvaluation] = []
    for case_id in expected_case_ids:
        row = by_id[case_id]
        if case_id not in labels:
            raise DualEvaluationError(f"label is missing for {case_id}")
        evaluation = evaluate_case(
            status=str(row.get("terminal_status")),
            native_ranking=row.get("native_ranking", ()),
            target=labels[case_id],
            candidates=candidates,
        )
        evaluations.append(evaluation)
        ordered_rows.append({
            "case_id": case_id,
            "status": evaluation.status,
            "ground_truth": labels[case_id],
            "native_ranking": list(evaluation.native_ranking),
            "projected_service_slots": list(evaluation.rcaeval_service_slots),
            "unique_service_ranking": list(evaluation.unique_service_ranking),
            "root_rank_slot": evaluation.root_rank_slot,
            "root_rank_unique": evaluation.root_rank_unique,
            "affected_k": list(evaluation.affected_k),
            "dedup_changed": evaluation.dedup_changed,
            "hits_unique": list(evaluation.unique_hits),
            "hits_rcaeval_slot": list(evaluation.rcaeval_slot_hits),
        })
    aggregates = {
        protocol: aggregate_hits(evaluations, protocol=protocol, expected_denominator=denominator)
        for protocol in PROTOCOLS
    }
    return ordered_rows, aggregates


__all__ = [
    "CaseEvaluation",
    "DualEvaluationError",
    "EXPECTED_DENOMINATOR",
    "METRICS",
    "PROTOCOLS",
    "PROTOCOL_VERSION",
    "aggregate_hits",
    "evaluate_case",
    "evaluate_records",
    "validate_case_identity",
]
