import unittest

from src.rca.evaluator import evaluate_case


class CandidateCompletenessTest(unittest.TestCase):
    def test_full_unique_registry_required(self):
        candidates = ("a", "b", "c", "d", "e", "f")
        with self.assertRaises(ValueError):
            evaluate_case(("a", "b", "c", "d", "e"), "a", candidates)
        with self.assertRaises(ValueError):
            evaluate_case(("a", "b", "c", "d", "e", "e"), "a", candidates)


if __name__ == "__main__":
    unittest.main()
