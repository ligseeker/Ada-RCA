from pathlib import Path
import unittest

from src.baseline_eval import assert_performance_firewall_tree


ROOT = Path(__file__).resolve().parents[1]


class BaselineEvalPerformanceFirewallTest(unittest.TestCase):
    def test_b0_b1_artifact_tree_contains_only_audit_and_freeze_files(self):
        assert_performance_firewall_tree(ROOT)

    def test_baseline_eval_package_exposes_no_aggregate_evaluator(self):
        import src.baseline_eval as baseline_eval

        for forbidden in ("evaluate", "calculate_ac", "calculate_avg_at_5", "calculate_mrr"):
            self.assertFalse(hasattr(baseline_eval, forbidden))
        source = (ROOT / "src/baseline_eval/__init__.py").read_text(encoding="utf-8")
        self.assertNotIn("from src.rca.evaluator", source)
        self.assertNotIn("import src.rca.evaluator", source)


if __name__ == "__main__":
    unittest.main()
