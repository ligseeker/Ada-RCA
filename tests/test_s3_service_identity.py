import json
from pathlib import Path
import unittest


class S3ServiceIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.output = cls.root / "artifacts" / "final_audit" / "s3_service_identity"
        if not (cls.output / "summary.json").is_file():
            raise unittest.SkipTest("S3 probe artifacts not generated")

    def test_exact_s2_input_and_fixed_model(self):
        summary = json.loads((self.output / "summary.json").read_text())
        for dataset, result in summary.items():
            self.assertEqual(result["feature_dimension"], 16)
            self.assertEqual(result["input"], "exact frozen S2 16D representation")
            self.assertEqual(result["model"]["solver"], "lbfgs")
            self.assertEqual(result["model"]["C"], 1.0)
            self.assertEqual(result["model"]["max_iter"], 5000)
            self.assertTrue(result["model"]["train_only_scaler"])
            self.assertEqual(sum(result["empirical_class_distribution"].values()), 90 * (11 if dataset == "re2ob" else 68))

    def test_event_split_is_preserved_and_metrics_are_defined(self):
        summary = json.loads((self.output / "summary.json").read_text())
        for result in summary.values():
            self.assertEqual(set(result["folds"]), {"0", "1", "2"})
            for fold in result["folds"].values():
                self.assertEqual(fold["train_event_count"], 60)
                self.assertEqual(fold["test_event_count"], 30)
                self.assertGreaterEqual(fold["top1_accuracy"], 0.0)
                self.assertLessEqual(fold["top1_accuracy"], 1.0)
            self.assertGreaterEqual(result["top1_accuracy"], 0.0)
            self.assertLessEqual(result["top1_accuracy"], 1.0)
            self.assertGreaterEqual(result["macro_f1"], 0.0)
            self.assertLessEqual(result["macro_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()

