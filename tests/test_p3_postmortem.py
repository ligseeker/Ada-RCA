import unittest

from scripts.p3_postmortem import aggregate, case_metrics, difference_or_none, transition_label


class P3PostmortemTest(unittest.TestCase):
    def test_case_metric_and_transition_definitions(self):
        row = {"ranking": ["b", "a", "c"], "root_service": "a"}
        metrics = case_metrics(row)
        self.assertEqual(metrics["rank"], 2)
        self.assertAlmostEqual(metrics["Avg@5"], 0.8)
        self.assertEqual(transition_label(3, 2), "improved")
        self.assertEqual(transition_label(2, 3), "degraded")
        self.assertEqual(transition_label(2, 2), "unchanged")
        self.assertIsNone(difference_or_none(aggregate([]), aggregate([]), "Avg@5"))


if __name__ == "__main__":
    unittest.main()
