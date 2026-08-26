import json
from pathlib import Path
import unittest


class P4SplitIntegrityTest(unittest.TestCase):
    def test_no_case_or_event_is_split_across_train_test(self):
        root = Path(__file__).resolve().parents[1]
        for dataset in ("re2ob", "re2tt"):
            assignments = json.loads((root / "artifacts" / "splits" / dataset / "assignments.json").read_text())
            self.assertEqual(len(assignments), 90)
            self.assertEqual(len({row["case_id"] for row in assignments}), 90)
            for fold in range(3):
                test = {row["case_id"] for row in assignments if row["fold"] == fold}
                train = {row["case_id"] for row in assignments if row["fold"] != fold}
                self.assertEqual(len(test), 30)
                self.assertEqual(len(train), 60)
                self.assertFalse(test & train)


if __name__ == "__main__":
    unittest.main()
