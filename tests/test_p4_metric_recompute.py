import unittest

from src.rca.evaluator import aggregate_case_metrics, evaluate_case


class P4MetricRecomputeTest(unittest.TestCase):
    def test_metrics_recompute_from_persisted_ranking(self):
        candidates = ("a", "b", "c", "d", "e")
        rows = [evaluate_case(("b", "a", "c", "d", "e"), "a", candidates) for _ in range(3)]
        metrics = aggregate_case_metrics(rows)
        self.assertEqual(metrics["AC@1"], 0.0)
        self.assertEqual(metrics["AC@3"], 1.0)
        self.assertAlmostEqual(metrics["Avg@5"], 0.8, places=15)


if __name__ == "__main__":
    unittest.main()
