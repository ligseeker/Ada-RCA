"""Fast protocol, scheduler, firewall, and evaluation tests for rescue V2."""

from __future__ import annotations

import argparse
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import src.baseline_eval.confirmatory as confirmatory_module

from src.baseline_eval import (
    CANONICAL_SEED,
)
from src.baseline_eval import assert_performance_firewall_tree
from src.baseline_eval.confirmatory import (
    FIXED_WORKER_ENV,
    SequenceError,
    exclusive_method_execution_lock,
)
from src.baseline_eval.evaluation_v2 import (
    _aggregate_hits,
    _baseline_case_rows,
    _case_utility,
    _fault_rows,
    _bootstrap_delta,
    BOOTSTRAP_SEED,
    evaluate_v2,
    require_v2_metric_unlock,
)
from src.baseline_eval.rescue_server_v2 import serve
from src.baseline_eval.rescue_v2 import (
    PROJECT_ROOT,
    V2_ALLOWED_WORKERS,
    V2_ATTEMPT_IDS,
    V2_BLOCKING_STATUSES,
    V2_CASE_SCHEMA,
    V2_EXECUTION_ROOT_RELATIVE,
    V2_METHODS,
    V2_PROTOCOL_DIGEST,
    V2_PROTOCOL_VERSION,
    V2_TRACE_CLOSURE_ADOPTED,
    active_v2_method_lock_relative,
    actual_worker_count,
    assert_determinism_equal,
    command_parser,
    deterministic_case_subset,
    microcause_native_execution_parameters,
    parse_dataset_scope,
    pending_v2_cases,
    protocol_preflight_v2,
    reissue_v2_method_lock,
    v2_method_lock_relative,
    v2_method_lock_reissued_relative,
    v2_method_lock_reissued_v2_relative,
    v2_execution_validity,
    run_determinism_preflight,
    v2_record_relative,
    V2EvaluationBlocked,
)
from src.baseline_eval.worker import (
    DataInputError,
    InputIntegrityError,
    MICROCAUSE_SYNTHETIC_RANDOM_WALK_EPOCHS,
    MICROCAUSE_SYNTHETIC_RANDOM_WALK_STEPS,
    execute_case,
)
import pandas as pd
from src.baseline_eval.worker import _common_metric_adapter


ROOT = Path(__file__).resolve().parents[1]


class RescueV2ProtocolTest(unittest.TestCase):
    def test_01_v2_registry_and_attempts_are_exactly_five_and_isolated(self):
        self.assertEqual(V2_METHODS, ("CIRCA", "MicroCause", "MicroRank", "TraceRCA", "mmBARO"))
        self.assertEqual(set(V2_ATTEMPT_IDS), set(V2_METHODS))
        self.assertTrue(all("-a1-" not in value and "-a2-" not in value for value in V2_ATTEMPT_IDS.values()))
        self.assertNotEqual(V2_EXECUTION_ROOT_RELATIVE.as_posix(), "artifacts/baseline_eval/execution_v1")

    def test_02_worker_count_contract_caps_to_available_cpu(self):
        self.assertEqual(actual_worker_count(10, available=4), 4)
        self.assertEqual(actual_worker_count(20, available=10), 10)
        self.assertEqual(actual_worker_count(1, available=0), 1)
        with self.assertRaises(SequenceError):
            actual_worker_count(2, available=20)

    def test_03_cli_parses_10_20_and_explicit_no_timeout(self):
        parser = command_parser()
        for workers in (10, 20):
            args = parser.parse_args([
                "run", "--method", "CIRCA", "--python", "/usr/bin/python3",
                "--attempt-id", "circa-a3-rescue-v2", "--workers", str(workers),
                "--datasets", "re2ob,re2tt", "--no-timeout", "--log-file", "/tmp/circa-v2.jsonl",
            ])
            self.assertEqual(args.workers, workers)
            self.assertTrue(args.no_timeout)
        args = parser.parse_args([
            "run", "--method", "CIRCA", "--python", "/usr/bin/python3",
            "--attempt-id", "circa-a3-rescue-v2", "--workers", "4",
            "--case-timeout", "none", "--log-file", "/tmp/circa-v2.jsonl",
        ])
        self.assertEqual(args.case_timeout, "none")

    def test_04_dataset_scope_requires_both_datasets_in_order(self):
        self.assertEqual(parse_dataset_scope("re2ob,re2tt"), ("re2ob", "re2tt"))
        with self.assertRaises(SequenceError):
            parse_dataset_scope("re2tt,re2ob")

    def test_05_thread_caps_are_fixed_for_every_case_process(self):
        self.assertEqual(
            {key: FIXED_WORKER_ENV[key] for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
            {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"},
        )

    def test_06_real_server_has_structural_no_timeout_join(self):
        source = inspect.getsource(serve)
        self.assertIn("process.join()", source)
        self.assertNotIn("process.join(CASE_TIMEOUT_SECONDS)", source)
        self.assertIn('"timeout_seconds": None', inspect.getsource(__import__("src.baseline_eval.rescue_server_v2", fromlist=["x"])._process_failure_record))

    def test_07_microcause_native_parameters_remain_1000_by_1000(self):
        self.assertEqual(microcause_native_execution_parameters(), {"random_walk_epochs": 1000, "random_walk_steps": 1000})
        self.assertEqual(MICROCAUSE_SYNTHETIC_RANDOM_WALK_EPOCHS, 10)
        self.assertEqual(MICROCAUSE_SYNTHETIC_RANDOM_WALK_STEPS, 100)
        source = (Path("/home/zhangll24/RCA_project/RCAEval-clean") / "RCAEval/e2e/microcause.py").read_text(encoding="utf-8")
        self.assertIn("randomwalk(Q, 1000", source)
        self.assertIn("walk_step=1000", source)

    def test_08_per_case_seed_is_fixed_and_not_worker_dependent(self):
        import random
        import numpy as np
        from src.baseline_eval import seed_in_process

        seed_in_process(CANONICAL_SEED, include_torch=False)
        first = (random.random(), float(np.random.random()))
        seed_in_process(CANONICAL_SEED, include_torch=False)
        second = (random.random(), float(np.random.random()))
        self.assertEqual(first, second)

    def test_09_resume_returns_only_missing_cases_and_keeps_method_failure(self):
        attempt = {"method": "CIRCA", "attempt_id": "circa-a3-rescue-v2"}
        existing = {("re2ob", "re2ob-0000000000000000"): {"terminal_status": "METHOD_FAILURE"}}
        with mock.patch("src.baseline_eval.rescue_v2._case_pairs", return_value=(
            ("re2ob", "re2ob-0000000000000000"),
            ("re2tt", "re2tt-0000000000000000"),
        )), mock.patch("src.baseline_eval.rescue_v2._load_v2_records", return_value=existing):
            self.assertEqual(pending_v2_cases(ROOT, attempt), (("re2tt", "re2tt-0000000000000000"),))

    def test_10_resume_never_retries_terminal_method_failure(self):
        attempt = {"method": "CIRCA", "attempt_id": "circa-a3-rescue-v2"}
        existing = {("re2ob", "re2ob-0000000000000000"): {"terminal_status": "METHOD_FAILURE"}}
        with mock.patch("src.baseline_eval.rescue_v2._case_pairs", return_value=tuple(existing)), mock.patch(
            "src.baseline_eval.rescue_v2._load_v2_records", return_value=existing
        ):
            self.assertEqual(pending_v2_cases(ROOT, attempt), ())

    def test_11_v2_case_paths_never_overlap_v1_paths(self):
        path = v2_record_relative("mmBARO", "mmbaro-a3-rescue-v2", "re2ob", "re2ob-0000000000000000")
        self.assertTrue(path.as_posix().startswith("artifacts/baseline_eval/execution_v2/"))
        self.assertNotIn("execution_v1", path.as_posix())

    def test_12_shared_method_lock_blocks_same_method(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with exclusive_method_execution_lock("CIRCA", lock_root=root):
                with self.assertRaises(SequenceError):
                    with exclusive_method_execution_lock("CIRCA", lock_root=root):
                        pass

    def test_13_protocol_digest_and_version_are_frozen(self):
        self.assertEqual(V2_PROTOCOL_VERSION, "RCA_BASELINE_RESCUE_PROTOCOL_V2")
        self.assertEqual(len(V2_PROTOCOL_DIGEST), 64)

    def test_14_determinism_comparator_is_performance_blind(self):
        baseline = {("re2ob", "re2ob-a"): {"status": "SUCCESS", "native_output_digest": "a", "adapted_output_digest": "b"}}
        candidate = {("re2ob", "re2ob-a"): {"status": "SUCCESS", "native_output_digest": "a", "adapted_output_digest": "b"}}
        assert_determinism_equal(baseline, candidate, baseline_workers=1, candidate_workers=20)
        candidate[("re2ob", "re2ob-a")]["native_output_digest"] = "different"
        with self.assertRaises(Exception):
            assert_determinism_equal(baseline, candidate, baseline_workers=1, candidate_workers=20)

    def test_15_determinism_subset_uses_case_id_hash_order(self):
        expected = sorted(
            (row["case_id"] for row in __import__("src.baseline_eval.confirmatory", fromlist=["x"]).read_jsonl(ROOT / "artifacts/source/re2ob/inputs.jsonl")),
            key=lambda value: hashlib.sha256(value.encode()).hexdigest(),
        )[0]
        with mock.patch("src.baseline_eval.rescue_v2.expected_case_ids", side_effect=lambda _root, dataset: (expected if dataset == "re2ob" else "re2tt-0000000000000000",)):
            self.assertEqual(deterministic_case_subset(ROOT, 1)[0], ("re2ob", expected))

    def test_16_determinism_attempt_carries_native_module_digest(self):
        cases = (("re2ob", "re2ob-opaque"),)
        environment = {
            "environment_digest": "e" * 64,
            "identity": {"python_executable": "/usr/bin/python3"},
        }
        observed_attempts = []

        def capture_group(**kwargs):
            observed_attempts.append(kwargs["attempt"])
            return {
                cases[0]: {
                    "status": "SUCCESS",
                    "native_output_digest": "n" * 64,
                    "adapted_output_digest": "a" * 64,
                }
            }

        with mock.patch("src.baseline_eval.rescue_v2.global_preflight"), mock.patch(
            "src.baseline_eval.rescue_v2.verify_v2_protocol"
        ), mock.patch(
            "src.baseline_eval.rescue_v2.verify_v2_environment", return_value=environment
        ), mock.patch(
            "src.baseline_eval.rescue_v2.v2_source_manifest_digest", return_value="i" * 64
        ), mock.patch(
            "src.baseline_eval.rescue_v2._v2_candidate_digests",
            return_value={"re2ob": "c" * 64, "re2tt": "d" * 64},
        ), mock.patch(
            "src.baseline_eval.rescue_v2.git",
            return_value=type("Completed", (), {"stdout": "x" * 40})(),
        ), mock.patch(
            "src.baseline_eval.rescue_v2.deterministic_case_subset", return_value=cases
        ), mock.patch(
            "src.baseline_eval.rescue_v2.resolve_frozen_worker_environment", return_value={}
        ), mock.patch(
            "src.baseline_eval.rescue_v2.available_cpu_count", return_value=10
        ), mock.patch(
            "src.baseline_eval.rescue_v2._v2_native_module_digest", return_value="n" * 64
        ), mock.patch(
            "src.baseline_eval.rescue_v2._run_determinism_group", side_effect=capture_group
        ):
            result = run_determinism_preflight(
                ROOT,
                "CIRCA",
                python=Path("/usr/bin/python3"),
                cases_per_dataset=1,
                requested_workers=(1,),
            )

        self.assertEqual(result["requested_workers"], [1])
        self.assertEqual(len(observed_attempts), 1)
        self.assertEqual(observed_attempts[0]["native_module_digest"], "n" * 64)

    def test_17_v2_preflight_does_not_reuse_historical_v1_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifacts/baseline_eval/execution_v1/environments/microcause.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                '{"identity": {"python_executable": "/env/bin/python"}}',
                encoding="utf-8",
            )
            identity = {
                "python_executable": "/env/bin/python",
                "runtime_python_executable": "/base/bin/python",
                "dependency_manifest_digest": "d" * 64,
            }
            synthetic = {
                "status": "PASS",
                "fingerprint": "f" * 64,
                "module_paths_within_clean_checkout": True,
            }
            with mock.patch.object(
                confirmatory_module, "collect_environment_identity", return_value=identity
            ), mock.patch.object(
                confirmatory_module, "resolve_frozen_worker_environment"
            ) as resolve, mock.patch.object(
                confirmatory_module, "_run_synthetic_preflight", return_value=synthetic
            ), mock.patch.object(
                confirmatory_module, "schema_preflight", return_value={"status": "PASS"}
            ):
                confirmatory_module._environment_preflight_details(
                    root,
                    "MicroCause",
                    Path("/env/bin/python"),
                    reuse_historical_manifest=False,
                )

            resolve.assert_not_called()

    def test_18_v2_protocol_preflight_selects_new_environment_identity(self):
        identity = {
            "python_executable": "/env/bin/python",
            "runtime_python_executable": "/base/bin/python",
            "dependency_manifest_digest": "d" * 64,
        }
        synthetic = {"fingerprint": "f" * 64}
        schema = [{"dataset": dataset, "status": "PASS"} for dataset in ("re2ob", "re2tt")]
        with mock.patch("src.baseline_eval.rescue_v2.global_preflight"), mock.patch(
            "src.baseline_eval.rescue_v2.verify_v2_protocol"
        ), mock.patch(
            "src.baseline_eval.rescue_v2.v2_source_manifest_digest", return_value="i" * 64
        ), mock.patch(
            "src.baseline_eval.rescue_v2._v2_native_module_digest", return_value="n" * 64
        ), mock.patch(
            "src.baseline_eval.rescue_v2._environment_preflight_details",
            return_value=(identity, synthetic, schema),
        ) as details:
            result = protocol_preflight_v2(ROOT, "MicroCause", Path("/env/bin/python"))

        details.assert_called_once_with(
            ROOT,
            "MicroCause",
            Path("/env/bin/python"),
            reuse_historical_manifest=False,
            synthetic_timeout_seconds=None,
        )
        self.assertFalse(result["real_execution_authorized"])

class RescueV2FailureAndMetricTest(unittest.TestCase):
    def test_16_only_method_failure_gets_zero_utility(self):
        self.assertEqual(_case_utility("METHOD_FAILURE", ("root",), "root"), (0, 0, 0, 0, 0))
        for status in sorted(V2_BLOCKING_STATUSES):
            with self.subTest(status=status), self.assertRaises(V2EvaluationBlocked):
                _case_utility(status, (), "root")

    def test_17_toy_ac_and_avg5_denominator(self):
        hits = [[1, 1, 1, 1, 1]] + [[0, 0, 0, 0, 0]] * 89
        result = _aggregate_hits(hits)
        self.assertEqual(result["AC@1"], 1 / 90)
        self.assertEqual(result["AC@3"], 1 / 90)
        self.assertEqual(result["AC@5"], 1 / 90)
        self.assertEqual(result["Avg@5"], 1 / 90)
        self.assertEqual(result["MRR"], "NOT-IDENTIFIABLE")

    def test_18_fault_aggregation_and_absent_fault_are_explicit_na(self):
        rows = [{"fault_type": "cpu", "AC@1": 1, "AC@3": 1, "AC@5": 1, "Avg@5": 1}]
        output = _fault_rows("CIRCA", "re2ob", rows)
        cpu = next(row for row in output if row["fault"] == "CPU")
        loss = next(row for row in output if row["fault"] == "LOSS")
        self.assertEqual(cpu["Cases" if "Cases" in cpu else "cases"], 1)
        self.assertEqual(loss["AC@1"], "N/A")

    def test_18b_baseline_case_rows_retain_all_fault_level_prefix_metrics(self):
        case_ids = tuple(f"re2ob-{index:016x}" for index in range(90))
        labels = {
            case_id: {"root_service": "root", "fault_type": "cpu"}
            for case_id in case_ids
        }
        with mock.patch(
            "src.baseline_eval.evaluation_v2.expected_case_ids",
            return_value=case_ids,
        ), mock.patch(
            "src.baseline_eval.evaluation_v2.read_json",
            return_value={"terminal_status": "SUCCESS", "adapted_ranking": ["root"]},
        ):
            rows, metrics = _baseline_case_rows(
                ROOT, "CIRCA", "circa-a3-rescue-v2", "re2ob", labels
            )
        self.assertEqual(rows[0]["AC@3"], 1)
        self.assertEqual(rows[0]["AC@5"], 1)
        self.assertEqual(metrics["AC@3"], 1.0)

    def test_19_fault_stratified_bootstrap_is_deterministic_and_seeded(self):
        ada = [{"case_id": f"c{i}", "fault_type": "cpu" if i < 2 else "mem", "AC@1": 1, "Avg@5": 1} for i in range(4)]
        base = [{"case_id": f"c{i}", "fault_type": "cpu" if i < 2 else "mem", "AC@1": 0, "Avg@5": 0} for i in range(4)]
        left = _bootstrap_delta(ada, base, metric="Avg@5", resamples=100, seed=BOOTSTRAP_SEED)
        right = _bootstrap_delta(ada, base, metric="Avg@5", resamples=100, seed=BOOTSTRAP_SEED)
        self.assertEqual(left, right)
        self.assertEqual(left["point_estimate"], 1.0)

    def test_20_evaluation_gate_stops_before_label_join(self):
        import src.baseline_eval.evaluation_v2 as evaluation
        with mock.patch.object(evaluation, "require_clean_git"), mock.patch.object(
            evaluation, "verify_v2_global_prediction_lock", side_effect=RuntimeError("no global lock")
        ), mock.patch.object(evaluation, "_labels_after_unlock") as labels:
            with self.assertRaises(RuntimeError):
                evaluation.evaluate_v2(ROOT)
            labels.assert_not_called()

    def test_21_metric_unlock_requires_committed_global_lock(self):
        with mock.patch("src.baseline_eval.evaluation_v2.require_clean_git"), mock.patch(
            "src.baseline_eval.evaluation_v2.verify_v2_global_prediction_lock", side_effect=RuntimeError("missing")
        ):
            with self.assertRaises(RuntimeError):
                require_v2_metric_unlock(ROOT)

    def test_22_process_crash_is_not_method_failure(self):
        self.assertIn("PROCESS_CRASH/OOM", V2_BLOCKING_STATUSES)
        self.assertNotEqual("PROCESS_CRASH/OOM", "METHOD_FAILURE")

    def test_22a_empty_dataset_blocking_maps_to_integrity_valid(self):
        self.assertEqual(
            v2_execution_validity({"re2ob": {}, "re2tt": {}}),
            "INTEGRITY_VALID",
        )
        self.assertEqual(
            v2_execution_validity({"re2ob": {}, "re2tt": {"PROCESS_CRASH/OOM": 1}}),
            "INTEGRITY_INVALID",
        )

    def test_22b_reissued_lock_path_is_distinct_and_selected_as_active(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / v2_method_lock_relative("MicroRank")
            reissued = root / v2_method_lock_reissued_relative("MicroRank")
            corrected = root / v2_method_lock_reissued_v2_relative("MicroRank")
            canonical.parent.mkdir(parents=True)
            canonical.write_text("old", encoding="utf-8")
            self.assertNotEqual(canonical, reissued)
            self.assertEqual(
                active_v2_method_lock_relative(root, "MicroRank"),
                v2_method_lock_relative("MicroRank"),
            )
            reissued.write_text("new", encoding="utf-8")
            self.assertEqual(
                active_v2_method_lock_relative(root, "MicroRank"),
                v2_method_lock_reissued_relative("MicroRank"),
            )
            corrected.write_text("corrected", encoding="utf-8")
            self.assertEqual(
                active_v2_method_lock_relative(root, "MicroRank"),
                v2_method_lock_reissued_v2_relative("MicroRank"),
            )

    def test_22c_reissue_command_requires_method_and_attempt(self):
        parser = command_parser()
        args = parser.parse_args([
            "reissue-method-lock",
            "--method", "MicroRank",
            "--attempt-id", "microrank-a3-rescue-v2",
        ])
        self.assertEqual(args.method, "MicroRank")
        self.assertEqual(args.attempt_id, "microrank-a3-rescue-v2")

    def test_22d_reissue_writes_sidecar_without_overwriting_original_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / v2_method_lock_relative("MicroRank")
            canonical.parent.mkdir(parents=True)
            canonical.write_text("immutable-old-lock", encoding="utf-8")
            runtime = root / "artifacts/baseline_eval/execution_v2/runtimes/microrank/microrank-a3-rescue-v2.json"
            runtime.parent.mkdir(parents=True)
            runtime.write_text("runtime", encoding="utf-8")
            old = {
                "schema_version": "rca_baseline_rescue_method_prediction_lock_v2",
                "method": "MicroRank",
                "attempt_id": "microrank-a3-rescue-v2",
                "execution_validity": "INTEGRITY_INVALID",
                "marker": "same-evidence",
                "locked_at": "old",
                "lock_digest": "o" * 64,
            }
            candidate = {
                **old,
                "execution_validity": "INTEGRITY_VALID",
                "locked_at": "new",
                "lock_digest": "c" * 64,
            }
            with mock.patch("src.baseline_eval.rescue_v2.require_clean_git"), mock.patch(
                "src.baseline_eval.rescue_v2.global_preflight"
            ), mock.patch("src.baseline_eval.rescue_v2.verify_v2_protocol"), mock.patch(
                "src.baseline_eval.rescue_v2.verify_rcaeval_clean"
            ), mock.patch("src.baseline_eval.rescue_v2.assert_ada_rca_frozen_unchanged"), mock.patch(
                "src.baseline_eval.rescue_v2.verify_v2_method_lock", return_value=old
            ), mock.patch(
                "src.baseline_eval.rescue_v2._load_v2_attempt",
                return_value={"method": "MicroRank", "attempt_id": "microrank-a3-rescue-v2"},
            ), mock.patch(
                "src.baseline_eval.rescue_v2._load_v2_records", return_value={("re2ob", "case"): {}}
            ), mock.patch(
                "src.baseline_eval.rescue_v2._case_pairs", return_value=(("re2ob", "case"),)
            ), mock.patch(
                "src.baseline_eval.rescue_v2._build_v2_method_lock", return_value=candidate
            ), mock.patch(
                "src.baseline_eval.rescue_v2.git", return_value=mock.Mock(stdout="a" * 40)
            ), mock.patch("src.baseline_eval.rescue_v2.assert_firewall_safe_record"):
                output = reissue_v2_method_lock(root, "MicroRank", "microrank-a3-rescue-v2")

            self.assertEqual(output, root / v2_method_lock_reissued_v2_relative("MicroRank"))
            self.assertEqual(canonical.read_text(encoding="utf-8"), "immutable-old-lock")
            payload = __import__("json").loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["supersedes_lock_path"], v2_method_lock_relative("MicroRank").as_posix())
            self.assertEqual(payload["supersedes_lock_digest"], "o" * 64)
            self.assertEqual(
                payload["lock_digest"],
                __import__("hashlib").sha256(
                    (__import__("json").dumps(
                        {key: value for key, value in payload.items() if key != "lock_digest"},
                        indent=2,
                        sort_keys=True,
                    ) + "\n").encode("utf-8")
                ).hexdigest(),
            )


class RescueV2WorkerAndFirewallTest(unittest.TestCase):
    def _args(self, **overrides):
        values = {
            "method": "CIRCA",
            "dataset": "re2ob",
            "case_id": "re2ob-0000000000000000",
            "attempt_id": "circa-a3-rescue-v2",
            "execution_commit": "e" * 40,
            "environment_digest": "env",
            "input_manifest_digest": "input",
            "candidate_registry_digest": "candidate",
            "execution_worker_count": 10,
            "execution_worker_slot": 0,
            "worker_id": "circa-worker-0",
            "requested_worker_count": 10,
            "available_cpu_count": 10,
            "execution_profile": "v2",
            "record_protocol_version": V2_PROTOCOL_VERSION,
            "record_protocol_digest": V2_PROTOCOL_DIGEST,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_23_input_integrity_failure_is_distinct_in_v2_record(self):
        with mock.patch("src.baseline_eval.worker.load_legal_case_input", side_effect=InputIntegrityError("opaque")), mock.patch(
            "src.baseline_eval.worker._native_module_path", return_value=Path("/does/not/exist")
        ):
            payload = execute_case(self._args())
        self.assertEqual(payload["terminal_status"], "INPUT_INTEGRITY_FAILURE")
        self.assertIsNone(payload["timeout_seconds"])
        self.assertEqual(payload["native_output_length"], 0)
        self.assertEqual(payload["adapted_output_length"], 0)

    def test_24_firewall_tree_accepts_frozen_v2_protocol_before_lock(self):
        assert_performance_firewall_tree(ROOT)

    def test_25_old_a1_a2_artifacts_have_not_been_rewritten_by_v2_paths(self):
        old = ROOT / "artifacts/baseline_eval/execution_v1"
        self.assertTrue(old.is_dir())
        self.assertFalse((ROOT / "artifacts/baseline_eval/execution_v2/records/CIRCA").exists())

    def test_26_trace_closure_and_extended_history_are_not_adopted(self):
        self.assertFalse(V2_TRACE_CLOSURE_ADOPTED)

    def test_27_v2_case_schema_is_not_v1(self):
        self.assertEqual(V2_CASE_SCHEMA, "rca_baseline_rescue_case_record_v2")

    def test_28_v21_drops_only_nonfinite_existing_metric_timestamps(self):
        raw = pd.DataFrame({
            "time": [1_700_000_599.0, float("nan"), 1_700_000_600.0],
            "frontend_latency-90": [1.0, 2.0, 3.0],
        })
        with self.assertRaises(DataInputError):
            _common_metric_adapter(raw, "re2ob", 1_700_000_600)
        repaired = _common_metric_adapter(
            raw, "re2ob", 1_700_000_600, drop_nonfinite_time=True
        )
        self.assertEqual(len(repaired), 2)
        self.assertTrue(repaired["time"].notna().all())


if __name__ == "__main__":
    unittest.main()
