import unittest

from scripts.p4_g0_diagnostics import aggregate_delta


class P4DiagnosticsTest(unittest.TestCase):
    def test_case_is_statistical_unit(self):
        left = {"a": {"Avg@5": 1.0, "AC@1": 1.0, "root_rank": 1}, "b": {"Avg@5": 0.0, "AC@1": 0.0, "root_rank": 6}}
        right = {"a": {"Avg@5": 0.8, "AC@1": 0.0, "root_rank": 2}, "b": {"Avg@5": 0.2, "AC@1": 0.0, "root_rank": 5}}
        result = aggregate_delta(("a", "b"), left, right)
        self.assertEqual(result["cases"], 2)
        self.assertAlmostEqual(result["Avg@5"], 0.0)
        self.assertAlmostEqual(result["AC@1"], 0.5)
        self.assertAlmostEqual(result["root_rank"], 0.0)


if __name__ == "__main__":
    unittest.main()
