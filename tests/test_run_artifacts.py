import json
from pathlib import Path
import unittest


class RunArtifactTest(unittest.TestCase):
    def test_all_zero_model_runs_have_complete_oof_predictions(self):
        root = Path(__file__).resolve().parents[1] / "artifacts" / "runs"
        if not (root / "z0" / "re2ob" / "predictions.jsonl").is_file():
            self.skipTest("formal zero-model runs not generated")
        for variant in ("z0", "z1", "z2", "z3", "z3_shuffle"):
            for dataset in ("re2ob", "re2tt"):
                run = root / variant / dataset
                rows = [json.loads(line) for line in (run / "predictions.jsonl").read_text().splitlines()]
                self.assertEqual(len(rows), 90)
                self.assertEqual(len({row["case_id"] for row in rows}), 90)
                self.assertTrue(all(len(row["ranking"]) == len(row["candidate_scores"]) for row in rows))
                self.assertEqual(json.loads((run / "manifest.json").read_text())["git_commit"], "f974c8c0bb6fe487ebcbe54b33d28276846a0708")


if __name__ == "__main__":
    unittest.main()
