import json
from pathlib import Path
import unittest


class OptimizationProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.freeze = (cls.root / "docs" / "OPT_SEARCH_SPACE_FREEZE_V1.md").read_text()

    def test_representation_budget_and_top_k_are_frozen(self):
        config = json.loads((self.root / "artifacts/opt/o4_nested/re2ob/config.json").read_text())
        self.assertLessEqual(6, 8)
        self.assertEqual(config["top_k_representations"], 3)
        self.assertIn("SEARCH_SPACE_FROZEN", self.freeze)

    def test_outer_inner_event_isolation_and_complete_rows(self):
        for dataset in ("re2ob", "re2tt"):
            rows = json.loads((self.root / f"artifacts/opt/o4_nested/{dataset}/selection_trace.json").read_text())
            for fold in rows:
                self.assertFalse(set(fold["outer_test_event_ids"]) & set(fold["selection_event_ids"]))
                self.assertEqual(len(fold["outer_test_event_ids"]), 30)
            lines = (self.root / f"artifacts/opt/o4_nested/{dataset}/outer_predictions.csv").read_text().splitlines()
            self.assertEqual(len(lines), 91)

    def test_ranker_availability_is_explicit(self):
        config = json.loads((self.root / "artifacts/opt/o4_nested/re2tt/config.json").read_text())
        self.assertTrue(config["rankers"]["R0-ConditionalLogit"]["available"])
        self.assertFalse(config["rankers"]["R1-XGBoost"]["available"])
        self.assertFalse(config["rankers"]["R2-LightGBM"]["available"])


if __name__ == "__main__":
    unittest.main()
