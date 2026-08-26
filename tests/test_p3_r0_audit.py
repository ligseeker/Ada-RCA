from pathlib import Path
import tempfile
import unittest

from scripts.p3_r0_audit import summarize_series


class P3R0AuditTest(unittest.TestCase):
    def test_malformed_timestamps_are_preserved_as_audit_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "series.csv"
            path.write_text(
                "time,value\n1,1\n,2\n2,3\nbad,4\n", encoding="utf-8"
            )
            result = summarize_series(path, "time")
            self.assertEqual(result["rows"], 4)
            self.assertEqual(result["valid_timestamp_rows"], 2)
            self.assertEqual(result["malformed_timestamp_rows"], 2)
            self.assertEqual(result["malformed_timestamp_row_examples"], [3, 5])
            self.assertEqual(result["delta_seconds_distribution"], {1.0: 1})


if __name__ == "__main__":
    unittest.main()
