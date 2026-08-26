from pathlib import Path
import tempfile
import unittest

from src.rca.features import CHANNELS, deterministic_shuffle, extract_case_features, flatten_features
from src.rca.rcaeval import CaseSource


class FeatureTest(unittest.TestCase):
    def make_source(self, directory):
        root = Path(directory)
        files = {}
        for name in ("metrics", "simple_metrics", "logs", "logts", "traces", "trace_error", "trace_latency"):
            filename = root / (name + ".csv")
            if name == "simple_metrics":
                filename.write_text("time,a_cpu,a_mem,b_cpu\n" + "\n".join("{},1,1,{}".format(i, 1 if i < 600 else 10) for i in range(0, 1200, 15)) + "\n", encoding="utf-8")
            else:
                filename.write_text("time,a_value,b_value\n" + "\n".join("{},1,{}".format(i, 1 if i < 600 else 10) for i in range(0, 1200, 15)) + "\n", encoding="utf-8")
            files[name + "_path"] = str(filename)
        inject = root / "inject_time.txt"
        inject.write_text("600", encoding="utf-8")
        return CaseSource("case", "condition/1", 1, "condition", str(root / "metrics.csv"), files["simple_metrics_path"], str(root / "logs.csv"), files["logts_path"], str(root / "traces.csv"), files["trace_error_path"], files["trace_latency_path"], str(inject))

    def test_shape_and_shuffle(self):
        with tempfile.TemporaryDirectory() as directory:
            features = extract_case_features("case", ("a", "b"), 600, self.make_source(directory))
            self.assertEqual(features.base.shape, (2, 4, 8))
            self.assertEqual(features.z.shape, (2, 4, 80))
            self.assertEqual(flatten_features(features, "z0").shape, (2, 1))
            self.assertEqual(flatten_features(features, "z1").shape, (2, 32))
            self.assertEqual(flatten_features(features, "z2").shape, (2, 68))
            self.assertEqual(flatten_features(features, "z3").shape, (2, 676))
            shuffled = deterministic_shuffle(features)
            self.assertEqual(shuffled.base.tolist(), features.base.tolist())
            self.assertEqual(shuffled.q_mask.shape, features.q_mask.shape)

    def test_missing_and_onset_are_masked_without_fake_zero_deviation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(directory)
            features = extract_case_features("case", ("a", "b"), 600, source)
            # The synthetic series has a sustained post-event jump for service b.
            self.assertGreaterEqual(features.base[1, 0, 3], 0.0)
            self.assertEqual(features.q_mask.shape, (2, 4, 80))
            self.assertTrue(((features.z == 0.0) | (features.q_mask == 1.0)).all())


if __name__ == "__main__":
    unittest.main()
