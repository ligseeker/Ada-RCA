import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/RCA_THESIS_CLAIM_MATRIX.md"


def _claim_rows(text):
    rows = []
    for line in text.splitlines():
        if not re.match(r"^\| \d+\.", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(
            {
                "claim": cells[0],
                "status": cells[1],
                "evidence_class": cells[2],
                "comparator": cells[3],
                "artifact": cells[4],
                "limitation": cells[5],
            }
        )
    return rows


class ThesisClaimMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MATRIX.read_text(encoding="utf-8")
        cls.rows = _claim_rows(cls.text)

    def _row(self, phrase):
        matches = [row for row in self.rows if phrase in row["claim"]]
        self.assertEqual(len(matches), 1, phrase)
        return matches[0]

    def test_all_required_claims_and_status_counts(self):
        self.assertEqual(len(self.rows), 24)
        self.assertEqual(
            Counter(row["status"] for row in self.rows),
            Counter(
                {
                    "SUPPORTED": 4,
                    "CONDITIONALLY SUPPORTED": 4,
                    "NOT SUPPORTED": 10,
                    "NOT TESTED": 6,
                }
            ),
        )

    def test_supported_claims_have_exact_comparator_and_artifact(self):
        for row in self.rows:
            if row["status"] != "SUPPORTED":
                continue
            self.assertNotIn("None", row["comparator"])
            self.assertIn("`", row["artifact"])
            self.assertTrue(row["limitation"])

    def test_no_sota_causal_or_unseen_system_support(self):
        self.assertEqual(self._row("SOTA")["status"], "NOT SUPPORTED")
        self.assertEqual(
            self._row("causal root-cause discovery")["status"], "NOT SUPPORTED"
        )
        self.assertEqual(
            self._row("generalizes to unseen systems")["status"], "NOT TESTED"
        )
        self.assertEqual(
            self._row("generalizes to unseen roots")["status"], "NOT SUPPORTED"
        )

    def test_absolute_leakage_claim_is_not_supported(self):
        self.assertEqual(
            self._row("There is no label leakage")["status"], "NOT SUPPORTED"
        )
        self.assertEqual(
            self._row("No explicit root/fault leakage")["status"], "SUPPORTED"
        )

    def test_tree_rankers_are_not_tested(self):
        for ranker in ("XGBoost", "LightGBM"):
            row = self._row(ranker)
            self.assertEqual(row["status"], "NOT TESTED")
            self.assertIn("not executed", row["comparator"].lower())


if __name__ == "__main__":
    unittest.main()
