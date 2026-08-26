import unittest

from src.rca.p4 import verify_complete_prediction


class P4PredictionCompletenessTest(unittest.TestCase):
    def test_complete_unique_ranking_and_root_required(self):
        candidates = ("a", "b", "c")
        verify_complete_prediction({"ranking": ["b", "a", "c"], "candidate_scores": {"a": 1., "b": 2., "c": 0.}}, candidates, "a")
        with self.assertRaises(ValueError):
            verify_complete_prediction({"ranking": ["a", "a", "c"], "candidate_scores": {"a": 1., "b": 2., "c": 0.}}, candidates, "a")
        with self.assertRaises(ValueError):
            verify_complete_prediction({"ranking": ["a", "b"], "candidate_scores": {"a": 1., "b": 2.}}, candidates, "c")


if __name__ == "__main__":
    unittest.main()
