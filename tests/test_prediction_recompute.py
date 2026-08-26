import unittest

from scripts.p3_a2_zero_models import evaluate_predictions


class PredictionRecomputeTest(unittest.TestCase):
    def test_metrics_recompute_from_prediction_rows(self):
        rows = []
        for fault in ("cpu", "mem", "disk", "socket", "delay", "loss"):
            rows.append({
                "case_id": fault,
                "fault_type": fault,
                "root_service": "a",
                "candidate_scores": {"a": 1.0, "b": 0.0, "c": -1.0, "d": -2.0, "e": -3.0},
                "ranking": ["a", "b", "c", "d", "e"],
            })
        metrics = evaluate_predictions(rows)
        self.assertEqual(metrics["average_across_faults"]["Avg@5"], 1.0)
        self.assertEqual(metrics["overall_cases"]["AC@1"], 1.0)


if __name__ == "__main__":
    unittest.main()
