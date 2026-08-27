import unittest

import numpy as np
from pathlib import Path

from src.rca.final_audit import (
    S1_FEATURE_NAMES,
    S2_FEATURE_NAMES,
    aggregate_expected,
    observability_event,
    fit_control_oof,
    s0_rankings,
)
from src.rca.final_method import load_dataset
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

    def test_formal_observability_control_satisfies_gradient_tolerance(self):
        root = Path(__file__).resolve().parents[1]
        events, labels, roots, assignments = load_dataset(root, "re2ob")
        s1_events = {}
        for case_id, event in events.items():
            with np.load(root / "artifacts" / "features" / "re2ob" / (case_id + ".npz")) as data:
                s1_events[case_id] = observability_event(case_id, event.candidates, data["base"])
        predictions, fits = fit_control_oof(s1_events, roots, assignments)
        self.assertEqual(len(predictions), 90)
        self.assertTrue(all(fit.converged for fit in fits.values()))
        self.assertLessEqual(max(fit.gradient_norm for fit in fits.values()), 1e-8)


if __name__ == "__main__":
    unittest.main()
