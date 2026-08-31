import hashlib
from pathlib import Path
import tempfile
import unittest

from src.baseline_eval.confirmatory import (
    METHOD_ORDER,
    PARALLEL_AMENDMENT_RELATIVE,
    PARALLEL_AMENDMENT_SHA256,
    environment_relative,
    method_execution_lock_path,
    method_lock_relative,
    method_records_relative,
)


ROOT = Path(__file__).resolve().parents[1]


class ParallelExecutionProtocolTest(unittest.TestCase):
    def test_parallel_amendment_digest_is_frozen(self):
        observed = hashlib.sha256(
            (ROOT / PARALLEL_AMENDMENT_RELATIVE).read_bytes()
        ).hexdigest()
        self.assertEqual(observed, PARALLEL_AMENDMENT_SHA256)

    def test_method_artifact_paths_are_pairwise_disjoint(self):
        owned_paths = {}
        for method in METHOD_ORDER:
            owned_paths[method] = {
                environment_relative(method),
                method_lock_relative(method),
                method_records_relative(method, "attempt-a", "re2ob"),
                method_records_relative(method, "attempt-a", "re2tt"),
            }
        for index, method in enumerate(METHOD_ORDER):
            for other in METHOD_ORDER[index + 1 :]:
                self.assertTrue(owned_paths[method].isdisjoint(owned_paths[other]))

    def test_method_process_lock_paths_are_pairwise_disjoint(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_root = Path(directory)
            paths = {
                method_execution_lock_path(method, lock_root) for method in METHOD_ORDER
            }
        self.assertEqual(len(paths), len(METHOD_ORDER))


if __name__ == "__main__":
    unittest.main()
