import unittest

import numpy as np

from src.rca.final_audit import (
    S1_FEATURE_NAMES,
    S2_FEATURE_NAMES,
    aggregate_expected,
    observability_event,
    s0_rankings,
)
from src.rca.p4 import CandidateEvent


class FinalAuditControlsTest(unittest.TestCase):
    def test_s1_uses_only_coverage_and_channel_availability(self):
        base = np.arange(2 * 4 * 8, dtype=float).reshape(2, 4, 8)
        event = observability_event("case", ("a", "b"), base)
        expected = base[:, :, (6, 7)].reshape(2, 8)
        np.testing.assert_array_equal(event.features, expected)
        self.assertEqual(len(S1_FEATURE_NAMES), 8)
        self.assertFalse(any("onset" in name or "magnitude" in name for name in S1_FEATURE_NAMES))

    def test_s2_schema_is_exactly_four_pre_fields_per_channel(self):
        self.assertEqual(len(S2_FEATURE_NAMES), 16)
        self.assertEqual(S2_FEATURE_NAMES[:4], (
            "metric.pre_mean_q", "metric.pre_max_q", "metric.pre_coverage", "metric.pre_available",
        ))
        self.assertTrue(all("post" not in name for name in S2_FEATURE_NAMES))

    def test_s0_tie_neutral_expectation_is_analytical(self):
        candidates = ("a", "b", "c", "d")
        events = {
            "train_a": CandidateEvent("train_a", candidates, np.zeros((4, 1))),
            "train_b": CandidateEvent("train_b", candidates, np.zeros((4, 1))),
            "test": CandidateEvent("test", candidates, np.zeros((4, 1))),
        }
        roots = {"train_a": "a", "train_b": "b", "test": "a"}
        assignments = {"train_a": 1, "train_b": 2, "test": 0}
        deterministic, expected, seen = s0_rankings(events, roots, assignments)
        test_row = next(row for row in expected if row["case_id"] == "test")
        self.assertEqual(test_row["tie_group_size"], 2)
        self.assertEqual(test_row["higher_score_count"], 0)
        self.assertEqual(test_row["AC@1"], 0.5)
        self.assertEqual(test_row["AC@3"], 1.0)
        self.assertAlmostEqual(test_row["MRR"], 0.75)


if __name__ == "__main__":
    unittest.main()

