from pathlib import Path
import tempfile
import unittest

from src.rca.supervised_baselines.aggregate import evaluate_dejavu_gate


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SupervisedGateTest(unittest.TestCase):
    def test_missing_aggregates_leave_gate_pending(self):
        with tempfile.TemporaryDirectory() as artifact_root:
            gate = evaluate_dejavu_gate(PROJECT_ROOT, Path(artifact_root))
        self.assertEqual(gate["decision"], "PENDING")
        self.assertEqual(len(gate["missing"]), 6)


if __name__ == "__main__":
    unittest.main()
