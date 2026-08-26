import unittest

from src.rca.evaluator import aggregate_case_metrics, evaluate_case


class EvaluatorTest(unittest.TestCase):
    def test_perfect_ranking(self):
        result = evaluate_case(("root", "b", "c", "d", "e"), "root", ("root", "b", "c", "d", "e"))
        self.assertEqual(result["AC@1"], 1.0)
        self.assertEqual(result["AC@3"], 1.0)
        self.assertEqual(result["AC@5"], 1.0)
        self.assertEqual(result["Avg@5"], 1.0)
        self.assertEqual(result["MRR"], 1.0)

    def test_rank_three(self):
        result = evaluate_case(("a", "b", "root", "d", "e"), "root", ("a", "b", "root", "d", "e"))
        self.assertEqual(result["AC@1"], 0.0)
        self.assertEqual(result["AC@3"], 1.0)
        self.assertEqual(result["AC@5"], 1.0)
        self.assertAlmostEqual(result["Avg@5"], 0.6)
        self.assertAlmostEqual(result["MRR"], 1.0 / 3.0)

    def test_duplicate_and_incomplete_rankings_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_case(("root", "a", "a"), "root", ("root", "a", "b"))
        with self.assertRaises(ValueError):
            evaluate_case(("root", "a"), "root", ("root", "a", "b"))

    def test_aggregate(self):
        a = evaluate_case(("root", "a", "b", "c", "d"), "root", ("root", "a", "b", "c", "d"))
        b = evaluate_case(("a", "root", "b", "c", "d"), "root", ("root", "a", "b", "c", "d"))
        self.assertAlmostEqual(aggregate_case_metrics((a, b))["AC@1"], 0.5)


if __name__ == "__main__":
    unittest.main()
