import json
from pathlib import Path
import unittest


class AnchorFeasibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = cls.root / "artifacts" / "final_audit" / "anchor_feasibility.json"
        if not cls.path.is_file():
            raise unittest.SkipTest("anchor feasibility artifact not generated")
        cls.report = json.loads(cls.path.read_text())

    def test_feasibility_does_not_compute_performance(self):
        self.assertFalse(self.report["performance_computed"])
        self.assertTrue(self.report["official_derived_sources_only"])
        self.assertEqual(self.report["offsets_seconds"], [-30, -15, 0, 15, 30])
        self.assertEqual(self.report["required_full_support_relative_seconds"], [-630, 630])

    def test_all_cases_and_sources_are_explicit(self):
        self.assertEqual(set(self.report["datasets"]), {"re2ob", "re2tt"})
        expected_names = {"metric": "simple_metrics.csv", "log": "logts.csv", "trace-error": "tracets_err.csv", "trace-latency": "tracets_lat.csv"}
        for dataset in self.report["datasets"].values():
            self.assertEqual(dataset["case_count"], 90)
            self.assertEqual(len(dataset["cases"]), 90)
            for case in dataset["cases"]:
                self.assertEqual(set(case["sources"]), set(expected_names))
                for channel, source in case["sources"].items():
                    self.assertEqual(source["expected_filename"], expected_names[channel])
                    self.assertTrue(source["uses_frozen_derived_source"])
                    self.assertTrue(source["frozen_reconstruction_semantics"])
                    self.assertEqual(set(source["offsets"]), {"-30", "-15", "0", "15", "30"})
                    for offset in source["offsets"].values():
                        self.assertIn("effective_support_end_relative_seconds", offset)


if __name__ == "__main__":
    unittest.main()
