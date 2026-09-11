import unittest

from src.rca.evaluator import aggregate_case_metrics, evaluate_case


class SupervisedEvaluatorTest(unittest.TestCase):
    def test_toy_ranks_match_retained_evaluator(self):
        candidates = ("a", "b", "c", "d", "e", "f")
        rank_one = evaluate_case(candidates, "a", candidates)
        rank_four = evaluate_case(candidates, "d", candidates)
        self.assertEqual(rank_one, {
            "AC@1": 1.0, "AC@3": 1.0, "AC@5": 1.0, "Avg@5": 1.0, "MRR": 1.0,
        })
        self.assertEqual(rank_four, {
            "AC@1": 0.0, "AC@3": 0.0, "AC@5": 1.0, "Avg@5": 0.4, "MRR": 0.25,
        })
        aggregate = aggregate_case_metrics((rank_one, rank_four))
        self.assertEqual(aggregate["AC@1"], 0.5)
        self.assertEqual(aggregate["Avg@5"], 0.7)


if __name__ == "__main__":
    unittest.main()
