import unittest
from pathlib import Path


class P3A05ExtractionTest(unittest.TestCase):
    def test_formal_feature_audit_if_present(self):
        path = Path(__file__).resolve().parents[1] / "artifacts" / "features" / "p3_a05_audit.json"
        if not path.is_file():
            self.skipTest("formal feature extraction not generated")
        import json
        report = json.loads(path.read_text(encoding="utf-8"))
        for key in ("re2ob", "re2tt"):
            self.assertEqual(report["datasets"][key]["case_count"], 90)
            self.assertTrue(report["datasets"][key]["finite_all_cases"])


if __name__ == "__main__":
    unittest.main()
