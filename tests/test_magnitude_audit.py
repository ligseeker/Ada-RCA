import unittest
from pathlib import Path

from scripts.p3_a1_magnitude_audit import audit_dataset


class MagnitudeAuditTest(unittest.TestCase):
    def test_formal_audit_has_all_cases(self):
        root = Path(__file__).resolve().parents[1] / "artifacts"
        if not (root / "features" / "re2ob").is_dir():
            self.skipTest("formal feature artifacts not generated")
        for key in ("re2ob", "re2tt"):
            report = audit_dataset(key, root)
            self.assertEqual(report["case_count"], 90)
            self.assertEqual(sum(report["by_fault"][fault]["cases"] for fault in report["by_fault"]), 90)


if __name__ == "__main__":
    unittest.main()
