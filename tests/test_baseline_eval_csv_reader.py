import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import pandas as pd

from src.baseline_eval import worker
from src.baseline_eval.confirmatory import (
    TRACE_CSV_PARSER_AMENDMENT_RELATIVE,
    TRACE_CSV_PARSER_AMENDMENT_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]
SEGFAULT_CASE_ID = "re2ob-f30e2feeaa5218b8"


def _trace_path(case_id: str) -> Path:
    source_manifest = ROOT / "artifacts/source/re2ob/sources.jsonl"
    rows = [json.loads(line) for line in source_manifest.read_text().splitlines() if line]
    return Path(next(row["traces_path"] for row in rows if row["case_id"] == case_id))


class BaselineCsvReaderRegressionTest(unittest.TestCase):
    def test_trace_csv_parser_amendment_digest_is_frozen(self):
        observed = hashlib.sha256(
            (ROOT / TRACE_CSV_PARSER_AMENDMENT_RELATIVE).read_bytes()
        ).hexdigest()
        self.assertEqual(observed, TRACE_CSV_PARSER_AMENDMENT_SHA256)

    def test_python_engine_is_scoped_to_raw_traces(self):
        sentinel = pd.DataFrame({"value": [1]})
        path = Path("synthetic.csv")
        with mock.patch.object(worker.pd, "read_csv", return_value=sentinel) as read_csv:
            self.assertIs(worker._read_csv_source(path, "traces"), sentinel)
        read_csv.assert_called_once_with(path, engine="python")

        with mock.patch.object(worker.pd, "read_csv", return_value=sentinel) as read_csv:
            self.assertIs(worker._read_csv_source(path, "simple_metrics"), sentinel)
        read_csv.assert_called_once_with(path)

    def test_problematic_trace_csv_does_not_crash_native_parser(self):
        code = """
from pathlib import Path
import sys
from src.baseline_eval.worker import _read_csv_source

frame = _read_csv_source(Path(sys.argv[1]), "traces")
print(f"{frame.shape[0]},{frame.shape[1]}")
"""
        environment = os.environ.copy()
        environment["PYTHONFAULTHANDLER"] = "1"
        completed = subprocess.run(
            (sys.executable, "-c", code, str(_trace_path(SEGFAULT_CASE_ID))),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "365484,11")


if __name__ == "__main__":
    unittest.main()
