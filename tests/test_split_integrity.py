import unittest
from pathlib import Path

from scripts.p3_a0_splits import build_split


class SplitIntegrityTest(unittest.TestCase):
    def test_formal_splits_are_three_balanced_folds(self):
        root = Path(__file__).resolve().parents[1]
        source = root / "artifacts" / "source"
        if not (source / "re2ob" / "inputs.jsonl").is_file():
            self.skipTest("formal source manifests not generated")
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            for key in ("re2ob", "re2tt"):
                summary = build_split(source / key, Path(directory), 20260826)
                self.assertEqual(summary["fold_sizes"], {"0": 30, "1": 30, "2": 30})
                self.assertEqual(summary["train_sizes"], {"0": 60, "1": 60, "2": 60})


if __name__ == "__main__":
    unittest.main()
