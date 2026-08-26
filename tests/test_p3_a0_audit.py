import unittest
from pathlib import Path

from scripts.p3_a0_audit import audit_bundle


class P3A0AuditTest(unittest.TestCase):
    def test_formal_bundles_pass(self):
        root = Path(__file__).resolve().parents[1] / "artifacts" / "source"
        if not (root / "re2ob" / "inputs.jsonl").is_file():
            self.skipTest("formal P3-A0 manifests not generated yet")
        for key in ("re2ob", "re2tt"):
            self.assertTrue(audit_bundle(root / key)["passed"])


if __name__ == "__main__":
    unittest.main()
