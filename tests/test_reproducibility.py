import hashlib
import json
import unittest
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReproducibilityTest(unittest.TestCase):
    def test_split_manifests_have_internal_digests(self):
        root = Path(__file__).resolve().parents[1] / "artifacts" / "splits"
        if not (root / "re2ob" / "split_manifest.json").is_file():
            self.skipTest("formal split artifacts not generated")
        for key in ("re2ob", "re2tt"):
            bundle = root / key
            manifest = json.loads((bundle / "split_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["assignments_sha256"], digest(bundle / "assignments.json"))
            self.assertEqual(manifest["folds_sha256"], digest(bundle / "folds.json"))
            self.assertEqual(manifest["fold_sizes"], {"0": 30, "1": 30, "2": 30})


if __name__ == "__main__":
    unittest.main()
