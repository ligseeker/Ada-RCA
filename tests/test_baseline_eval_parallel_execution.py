import hashlib
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest

from src.baseline_eval.confirmatory import (
    CASE_PARALLEL_METHODS,
    CASE_PARALLEL_ATTEMPT_WORKERS,
    CASE_PARALLELISM_AMENDMENT_RELATIVE,
    CASE_PARALLELISM_AMENDMENT_SHA256,
    MAX_CASE_WORKERS,
    METHOD_ORDER,
    PARALLEL_AMENDMENT_RELATIVE,
    PARALLEL_AMENDMENT_SHA256,
    SequenceError,
    attempt_runtime_relative,
    build_attempt_runtime_summary,
    environment_relative,
    execute_case_shards,
    git_common_execution_lock_root,
    method_execution_lock_path,
    method_lock_relative,
    method_records_relative,
    partition_pending_cases,
    validate_case_worker_count,
    validate_attempt_worker_contract,
    validate_attempt_runtime_summary,
)


ROOT = Path(__file__).resolve().parents[1]


class ParallelExecutionProtocolTest(unittest.TestCase):
    def test_parallel_amendment_digest_is_frozen(self):
        observed = hashlib.sha256(
            (ROOT / PARALLEL_AMENDMENT_RELATIVE).read_bytes()
        ).hexdigest()
        self.assertEqual(observed, PARALLEL_AMENDMENT_SHA256)

    def test_case_parallelism_amendment_digest_is_frozen(self):
        observed = hashlib.sha256(
            (ROOT / CASE_PARALLELISM_AMENDMENT_RELATIVE).read_bytes()
        ).hexdigest()
        self.assertEqual(observed, CASE_PARALLELISM_AMENDMENT_SHA256)

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

    def test_process_locks_live_in_the_shared_git_common_directory(self):
        common = subprocess.run(
            ("git", "rev-parse", "--git-common-dir"),
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        expected_common = Path(common)
        if not expected_common.is_absolute():
            expected_common = ROOT / expected_common
        lock_root = git_common_execution_lock_root(ROOT)
        self.assertEqual(lock_root.parent, expected_common.resolve())

    def test_case_parallelism_is_scoped_and_bounded(self):
        self.assertEqual(CASE_PARALLEL_METHODS, frozenset({"CIRCA", "MicroCause"}))
        self.assertEqual(MAX_CASE_WORKERS, 4)
        for method in CASE_PARALLEL_METHODS:
            self.assertEqual(validate_case_worker_count(method, 4), 4)
        with self.assertRaises(SequenceError):
            validate_case_worker_count("MicroRank", 2)
        for invalid in (0, 5):
            with self.assertRaises(SequenceError):
                validate_case_worker_count("CIRCA", invalid)

    def test_parallel_workers_are_bound_to_the_authorized_a2_attempts(self):
        self.assertEqual(
            CASE_PARALLEL_ATTEMPT_WORKERS,
            {
                ("CIRCA", "circa-a2-20260901"): 4,
                ("MicroCause", "microcause-a2-20260901"): 4,
            },
        )
        self.assertEqual(
            validate_attempt_worker_contract("CIRCA", "circa-a2-20260901", 4),
            4,
        )
        with self.assertRaises(SequenceError):
            validate_attempt_worker_contract("CIRCA", "circa-a2-20260901", 3)
        with self.assertRaises(SequenceError):
            validate_attempt_worker_contract("CIRCA", "unapproved-attempt", 4)
        with self.assertRaises(SequenceError):
            validate_attempt_worker_contract(
                "MicroCause", "microcause-a1-20260831", 1, resume=True
            )

    def test_pending_cases_are_partitioned_deterministically_round_robin(self):
        cases = tuple(("re2ob", f"case-{index}") for index in range(7))
        self.assertEqual(
            partition_pending_cases(cases, 3),
            (
                (cases[0], cases[3], cases[6]),
                (cases[1], cases[4]),
                (cases[2], cases[5]),
            ),
        )

    def test_case_shards_execute_concurrently(self):
        barrier = threading.Barrier(2)
        active = 0
        maximum = 0
        guard = threading.Lock()

        def run_shard(slot, shard):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            barrier.wait(timeout=2)
            time.sleep(0.02)
            with guard:
                active -= 1
            return slot, tuple(shard)

        shards = ((('re2ob', 'case-a'),), (('re2ob', 'case-b'),))
        self.assertEqual(
            execute_case_shards(shards, run_shard),
            ((0, shards[0]), (1, shards[1])),
        )
        self.assertEqual(maximum, 2)

    def test_attempt_runtime_summary_preserves_every_case_timing(self):
        ordered = (("re2ob", "case-a"), ("re2tt", "case-b"))
        records = {
            ordered[0]: {
                "terminal_status": "SUCCESS",
                "start_timestamp": "2026-09-01T00:00:00+00:00",
                "end_timestamp": "2026-09-01T00:00:02+00:00",
                "wall_time_seconds": 2.0,
                "execution_worker_count": 4,
                "execution_worker_slot": 0,
            },
            ordered[1]: {
                "terminal_status": "TIMEOUT",
                "start_timestamp": "2026-09-01T00:00:00+00:00",
                "end_timestamp": "2026-09-01T01:00:00+00:00",
                "wall_time_seconds": 3600.0,
                "execution_worker_count": 4,
                "execution_worker_slot": 1,
            },
        }
        summary = build_attempt_runtime_summary(
            method="CIRCA",
            attempt_id="circa-a2-20260901",
            execution_commit="a" * 40,
            worker_count=4,
            attempt_start_timestamp="2026-09-01T00:00:00+00:00",
            attempt_end_timestamp="2026-09-01T01:00:01+00:00",
            attempt_wall_time_seconds=3601.0,
            ordered_case_keys=ordered,
            records=records,
        )
        self.assertEqual(summary["terminal_case_count"], 2)
        self.assertEqual(summary["aggregate_case_wall_time_seconds"], 3602.0)
        self.assertEqual(summary["dataset_case_wall_time_seconds"], {"re2ob": 2.0, "re2tt": 3600.0})
        self.assertEqual([row["case_id"] for row in summary["case_timings"]], ["case-a", "case-b"])
        validate_attempt_runtime_summary(
            summary,
            method="CIRCA",
            attempt_id="circa-a2-20260901",
            execution_commit="a" * 40,
            worker_count=4,
            ordered_case_keys=ordered,
            records=records,
        )
        corrupted = dict(summary)
        corrupted["aggregate_case_wall_time_seconds"] = 1.0
        with self.assertRaisesRegex(Exception, "aggregate"):
            validate_attempt_runtime_summary(
                corrupted,
                method="CIRCA",
                attempt_id="circa-a2-20260901",
                execution_commit="a" * 40,
                worker_count=4,
                ordered_case_keys=ordered,
                records=records,
            )
        self.assertEqual(
            attempt_runtime_relative("CIRCA", "circa-a2-20260901").as_posix(),
            "artifacts/baseline_eval/execution_v1/runtimes/circa/circa-a2-20260901.json",
        )


if __name__ == "__main__":
    unittest.main()
