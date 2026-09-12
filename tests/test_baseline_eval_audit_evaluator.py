import unittest

from src.baseline_eval import TerminalStatus
from src.baseline_eval.audit_evaluator import (
    DualEvaluationError,
    aggregate_hits,
    evaluate_case,
    evaluate_records,
    validate_case_identity,
)


class BaselineAuditEvaluatorTest(unittest.TestCase):
    def test_synthetic_duplicate_slots_distinguish_protocols(self):
        result = evaluate_case(
            status=TerminalStatus.SUCCESS.value,
            native_ranking=("A_cpu", "A_mem", "B_cpu", "C_cpu"),
            target="C",
            candidates=("A", "B", "C"),
        )
        self.assertEqual(result.unique_service_ranking, ("A", "B", "C"))
        self.assertEqual(result.rcaeval_service_slots, ("A", "A", "B", "C"))
        self.assertEqual(result.root_rank_unique, 3)
        self.assertEqual(result.root_rank_slot, 4)
        self.assertEqual(result.unique_hits, (0, 0, 1, 1, 1))
        self.assertEqual(result.rcaeval_slot_hits, (0, 0, 0, 1, 1))
        self.assertEqual(result.affected_k, (3,))
        self.assertTrue(result.dedup_changed)

    def test_frozen_alias_and_unmapped_slot_are_not_candidate_completed(self):
        result = evaluate_case(
            status=TerminalStatus.SUCCESS.value,
            native_ranking=("frontendservice_cpu", "unknown_cpu", "checkoutservice_latency"),
            target="checkoutservice",
            candidates=("frontend", "checkoutservice"),
        )
        self.assertEqual(result.unique_service_ranking, ("frontend", "checkoutservice"))
        self.assertEqual(result.root_rank_unique, 2)
        # RCAEval's pinned entity projection keeps the native service token;
        # the local frontendservice alias is a U-only adapter rule.
        self.assertEqual(result.rcaeval_service_slots, ("frontendservice", "unknown", "checkoutservice"))
        self.assertEqual(result.root_rank_slot, 3)

    def test_rcaeval_slot_projection_keeps_unregistered_entities(self):
        result = evaluate_case(
            status=TerminalStatus.SUCCESS.value,
            native_ranking=("unknown_cpu", "checkoutservice_latency"),
            target="checkoutservice",
            candidates=("checkoutservice",),
        )
        self.assertEqual(result.unique_service_ranking, ("checkoutservice",))
        self.assertEqual(result.rcaeval_service_slots, ("unknown", "checkoutservice"))
        self.assertEqual(result.root_rank_unique, 1)
        self.assertEqual(result.root_rank_slot, 2)

    def test_method_failure_contributes_zero_utility(self):
        result = evaluate_case(
            status=TerminalStatus.METHOD_FAILURE.value,
            native_ranking=(),
            target="C",
            candidates=("A", "B", "C"),
        )
        self.assertEqual(result.unique_hits, (0, 0, 0, 0, 0))
        self.assertEqual(result.rcaeval_slot_hits, (0, 0, 0, 0, 0))

    def test_avg_at_5_uses_raw_hit_counts_without_intermediate_rounding(self):
        rows = []
        for index in range(90):
            rows.append(
                evaluate_case(
                    status=TerminalStatus.SUCCESS.value,
                    native_ranking=("root_cpu",) if index < 30 else ("other_cpu",),
                    target="root",
                    candidates=("root", "other"),
                )
            )
        aggregate = aggregate_hits(rows, protocol="unique_service")
        self.assertEqual(aggregate["hit_counts"], {
            "hit@1": 30,
            "hit@2": 30,
            "hit@3": 30,
            "hit@4": 30,
            "hit@5": 30,
        })
        self.assertEqual(aggregate["avg_at_5_numerator"], 150)
        self.assertEqual(aggregate["metrics"]["Avg@5"], 1 / 3)

    def test_case_identity_rejects_missing_duplicate_and_foreign_records(self):
        expected = tuple(f"case-{index:02d}" for index in range(90))
        validate_case_identity(expected, expected)
        with self.assertRaises(DualEvaluationError):
            validate_case_identity(expected[:-1], expected)
        with self.assertRaises(DualEvaluationError):
            validate_case_identity((*expected[:-1], expected[0]), expected)
        with self.assertRaises(DualEvaluationError):
            validate_case_identity((*expected[:-1], "foreign"), expected)

    def test_record_evaluation_requires_exact_denominator_and_returns_both(self):
        expected = tuple(f"case-{index:02d}" for index in range(90))
        records = [
            {
                "case_id": case_id,
                "terminal_status": "SUCCESS",
                "native_ranking": ["root_cpu"] if index == 0 else ["other_cpu"],
            }
            for index, case_id in enumerate(expected)
        ]
        labels = {case_id: "root" for case_id in expected}
        cases, aggregates = evaluate_records(records, labels, ("root", "other"), expected)
        self.assertEqual(len(cases), 90)
        self.assertEqual(set(aggregates), {"unique_service", "rcaeval_service_slot"})
        self.assertEqual(aggregates["unique_service"]["hit_counts"]["hit@1"], 1)
        with self.assertRaises(DualEvaluationError):
            aggregate_hits(tuple(), protocol="unique_service")


if __name__ == "__main__":
    unittest.main()
