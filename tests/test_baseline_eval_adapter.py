from pathlib import Path
import unittest

from src.baseline_eval import (
    AdapterError,
    adapt_native_ranking,
    inspect_trace_timestamp_sample,
    is_complete_legal_ranking,
    metric_legality,
    mmbaro_dataset_key,
    span_end_in_canonical_window,
    trace_anchor_microseconds,
    validate_mmbaro_payload,
)


ROOT = Path(__file__).resolve().parents[1]


class BaselineEvalAdapterTest(unittest.TestCase):
    def test_indicator_and_operation_mapping_uses_registry_only(self):
        candidates = ("checkoutservice", "emailservice", "frontend")
        result = adapt_native_ranking(
            (
                "checkoutservice_cpu",
                "checkoutservice_latency",
                "frontendservice_GET",
                "notregistered_cpu",
                "emailservice_mem",
            ),
            candidates,
        )
        self.assertEqual(result.services, ("checkoutservice", "frontend", "emailservice"))
        self.assertEqual(result.duplicates, ("checkoutservice_latency",))
        self.assertEqual(result.unmapped, ("notregistered_cpu",))

    def test_longest_registry_prefix_wins(self):
        result = adapt_native_ranking(("a_b_cpu",), ("a", "a_b"))
        self.assertEqual(result.services, ("a_b",))

    def test_all_illegal_native_items_are_adapter_failure(self):
        with self.assertRaises(AdapterError):
            adapt_native_ranking(("unknown_cpu",), ("legal",))

    def test_native_duplicates_do_not_consume_service_rank(self):
        result = adapt_native_ranking(("a_cpu", "a_mem", "b_cpu"), ("a", "b"))
        self.assertEqual(result.services, ("a", "b"))

    def test_timestamp_units_and_half_open_trace_window(self):
        t0 = 1_705_354_566
        t0_us = trace_anchor_microseconds(t0)
        self.assertEqual(t0_us, 1_705_354_566_000_000)
        self.assertTrue(span_end_in_canonical_window(t0_us - 600_000_000, 0, t0))
        self.assertTrue(span_end_in_canonical_window(t0_us + 599_999_999, 0, t0))
        self.assertFalse(span_end_in_canonical_window(t0_us - 600_000_001, 0, t0))
        self.assertFalse(span_end_in_canonical_window(t0_us + 600_000_000, 0, t0))

    def test_committed_trace_sample_proves_seconds_microseconds_mismatch(self):
        for dataset in ("re2ob", "re2tt"):
            audit = inspect_trace_timestamp_sample(ROOT, dataset)
            self.assertEqual(audit["inject_time_unit"], "s")
            self.assertEqual(audit["start_time_unit"], "us")
            self.assertEqual(audit["duration_unit"], "us")
            self.assertEqual(audit["derived_time_unit"], "s")
            self.assertTrue(audit["start_time_millis_consistent"])
            self.assertTrue(audit["commented_conversion_is_required"])

    def test_native_top_k_and_full_ranking_legality_are_distinct(self):
        legality = metric_legality("OPERATION_OR_INDICATOR_PARTIAL")
        for metric in ("AC@1", "AC@3", "AC@5", "Avg@5"):
            self.assertEqual(legality[metric], "ADAPTED-BUT-VALID")
        self.assertEqual(legality["MRR"], "NOT-IDENTIFIABLE")
        self.assertTrue(is_complete_legal_ranking(("a", "b"), ("a", "b")))
        self.assertFalse(is_complete_legal_ranking(("a",), ("a", "b")))
        self.assertFalse(is_complete_legal_ranking(("a", "a"), ("a", "b")))

    def test_mmbaro_uses_official_multimodal_keys(self):
        self.assertEqual(mmbaro_dataset_key("re2ob"), "mm-ob")
        self.assertEqual(mmbaro_dataset_key("re2tt"), "mm-tt")
        payload = {
            "metric": object(),
            "logs": object(),
            "logts": object(),
            "traces": object(),
            "tracets_err": object(),
            "tracets_lat": object(),
            "cluster_info": None,
        }
        validate_mmbaro_payload(payload)
        with self.assertRaises(AdapterError):
            validate_mmbaro_payload({"metric": object(), "logts": object()})


if __name__ == "__main__":
    unittest.main()
