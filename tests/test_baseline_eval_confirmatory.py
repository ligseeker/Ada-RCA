import inspect
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from src.baseline_eval import (
    AdapterError,
    adapt_native_ranking,
    detect_silent_fallback,
    mmbaro_dataset_key,
    span_end_in_canonical_window,
    validate_native_output,
)
from src.baseline_eval.confirmatory import (
    DATASET_ORDER,
    METHOD_ORDER,
    PreflightError,
    SequenceError,
    _run_synthetic_preflight,
    assert_method_sequence_ready,
    canonical_payload_digest,
    exclusive_execution_lock,
    format_case_status,
    method_lock_relative,
    preflight_environment,
    validate_attempt_is_new,
    validate_terminal_record,
    verify_rcaeval_clean,
)
from src.baseline_eval.evaluation import failure_zero_top_k
from src.baseline_eval.worker import invoke_predictive_method, synthetic_preflight


ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=root, check=True, capture_output=True)


class ConfirmatorySequenceTest(unittest.TestCase):
    def test_01_method_execution_order_is_exactly_frozen(self):
        self.assertEqual(
            METHOD_ORDER,
            ("BARO", "CIRCA", "MicroCause", "MicroRank", "TraceRCA", "mmBARO", "CausalRCA"),
        )
        self.assertEqual(DATASET_ORDER, ("re2ob", "re2tt"))

    def test_02_two_methods_cannot_hold_execution_lock_concurrently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "execution.lock"
            with exclusive_execution_lock(path):
                with self.assertRaises(SequenceError):
                    with exclusive_execution_lock(path):
                        pass

    def test_03_method_cannot_start_before_committed_previous_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _git(root, "init")
            _git(root, "config", "user.email", "test@example.invalid")
            _git(root, "config", "user.name", "Test")
            with self.assertRaises(PreflightError):
                assert_method_sequence_ready(root, "CIRCA")
            relative = method_lock_relative("BARO")
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"method": "BARO", "disposition": "EXECUTION_COMPLETE"}), encoding="utf-8")
            _git(root, "add", relative.as_posix())
            _git(root, "commit", "-m", "freeze BARO")
            assert_method_sequence_ready(root, "CIRCA")

    def test_04_ob_and_tt_records_must_use_same_environment_digest(self):
        common = {
            "method": "BARO",
            "case_id": "re2ob-0000000000000000",
            "environment_digest": "env-a",
            "input_manifest_digest": "input",
            "protocol_digest": "aa4f03363e1347a4b4e3c6427fd846be80452f025c3a6d08042ed6f6de0a849e",
            "rcaeval_commit": "5e96b700445bfb5c599e505ecf37d53bf847bbeb",
            "terminal_status": "METHOD_FAILURE",
            "native_ranking": [],
            "adapted_ranking": [],
        }
        with self.assertRaises(Exception):
            validate_terminal_record(
                {**common, "dataset": "re2ob"},
                method="BARO",
                dataset="re2ob",
                case_id=common["case_id"],
                environment_digest="env-b",
                input_manifest_digest="input",
            )

    def test_05_environment_manifest_digest_changes_on_mutation(self):
        frozen = {"python": "3.10", "packages": [{"name": "numpy", "version": "1.26.4"}]}
        mutated = {"python": "3.10", "packages": [{"name": "numpy", "version": "2.0.0"}]}
        self.assertNotEqual(canonical_payload_digest(frozen), canonical_payload_digest(mutated))

    def test_06_new_attempt_must_restart_from_case_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt = root / "artifacts/baseline_eval/execution_v1/records/baro/attempt-2/re2ob"
            attempt.mkdir(parents=True)
            (attempt / "re2ob-0000000000000000.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(SequenceError):
                validate_attempt_is_new(root, "BARO", "attempt-2")

    def test_06a_environment_preflight_is_read_only_and_not_sequence_gated(self):
        identity = {
            "python_executable": "/external/env/bin/python",
            "runtime_python_executable": "/base/bin/python",
            "python_version": "3.10.20",
            "python_implementation": "CPython",
            "environment_path": "/external/env",
            "environment_type": "venv",
            "dependency_manifest_digest": "d" * 64,
        }
        synthetic = {
            "status": "PASS",
            "method": "mmBARO",
            "fingerprint": "f" * 64,
            "native_output_kind": "CROSS_MODALITY_INDICATOR_RANKING",
            "module_paths_within_clean_checkout": True,
        }
        schema = [{"dataset": dataset, "status": "PASS"} for dataset in DATASET_ORDER]
        with mock.patch("src.baseline_eval.confirmatory.verify_protocol_artifacts"), mock.patch(
            "src.baseline_eval.confirmatory.verify_rcaeval_clean"
        ), mock.patch("src.baseline_eval.confirmatory.assert_ada_rca_frozen_unchanged"), mock.patch(
            "src.baseline_eval.confirmatory.require_committed_file"
        ), mock.patch(
            "src.baseline_eval.confirmatory._environment_preflight_details",
            return_value=(identity, synthetic, schema),
        ), mock.patch(
            "src.baseline_eval.confirmatory.sha256_file", return_value="i" * 64
        ), mock.patch(
            "src.baseline_eval.confirmatory.assert_method_sequence_ready"
        ) as sequence:
            result = preflight_environment(ROOT, "mmBARO", Path("/external/env/bin/python"))
        sequence.assert_not_called()
        self.assertFalse(result["writes_artifacts"])
        self.assertFalse(result["authorizes_real_execution"])
        self.assertEqual(result["synthetic_preflight"]["runs"], 2)
        self.assertNotIn("packages", result["environment"])

    def test_06b_synthetic_preflight_rejects_nonclean_import_resolution(self):
        payload = {
            "status": "PASS",
            "method": "TraceRCA",
            "fingerprint": "f" * 64,
            "native_output_kind": "PARTIAL_OPERATION_RANKING",
            "module_paths_within_clean_checkout": False,
        }
        completed = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=json.dumps(payload), stderr=""
        )
        with mock.patch("src.baseline_eval.confirmatory.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(PreflightError, "outside RCAEval-clean"):
                _run_synthetic_preflight(ROOT, Path("/external/env/bin/python"), "TraceRCA")

    def test_06c_synthetic_preflight_requires_sha256_fingerprint(self):
        payload = {
            "status": "PASS",
            "method": "mmBARO",
            "fingerprint": "not-a-digest",
            "native_output_kind": "CROSS_MODALITY_INDICATOR_RANKING",
            "module_paths_within_clean_checkout": True,
        }
        completed = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=json.dumps(payload), stderr=""
        )
        with mock.patch("src.baseline_eval.confirmatory.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(PreflightError, "invalid fingerprint"):
                _run_synthetic_preflight(ROOT, Path("/external/env/bin/python"), "mmBARO")


class ConfirmatoryFirewallTest(unittest.TestCase):
    def test_07_root_coded_fields_are_absent_from_predictive_call_contract(self):
        parameters = set(inspect.signature(invoke_predictive_method).parameters)
        forbidden = {"root_service", "fault_type", "relative_directory", "source_path", "condition"}
        self.assertTrue(parameters.isdisjoint(forbidden))

    def test_08_root_path_and_prediction_cannot_be_formatted_together(self):
        payload = {
            "case_id": "re2ob-0123456789abcdef",
            "terminal_status": "SUCCESS",
            "native_output_length": 3,
            "adapted_output_length": 2,
            "wall_time_seconds": 1.25,
            "native_ranking": ["secret_operation"],
            "adapted_ranking": ["secret_service"],
            "relative_directory": "secret_fault/1",
        }
        line = format_case_status(payload)
        self.assertNotIn("secret", line)
        self.assertEqual(
            line,
            "re2ob-0123456789abcdef SUCCESS native_len=3 adapted_len=2 wall=1.250s",
        )

    def test_09_ranking_contents_are_not_exposed_by_status_formatter(self):
        payload = {
            "case_id": "re2tt-0123456789abcdef",
            "terminal_status": "SUCCESS",
            "native_output_length": 1,
            "adapted_output_length": 1,
            "wall_time_seconds": 0.1,
            "native_ranking": ["do-not-print"],
            "adapted_ranking": ["also-hidden"],
        }
        self.assertNotIn("hidden", format_case_status(payload))
        self.assertNotIn("print", format_case_status(payload))

    def test_10_post_lock_evaluator_requires_committed_global_lock(self):
        from src.baseline_eval import evaluation

        with mock.patch.object(evaluation, "require_clean_git"), mock.patch.object(
            evaluation, "verify_global_prediction_lock", side_effect=PreflightError("no lock")
        ), mock.patch.object(evaluation, "_labels") as labels:
            with self.assertRaises(PreflightError):
                evaluation.evaluate_locked_predictions(ROOT)
            labels.assert_not_called()

    def test_11_candidate_completion_is_none(self):
        result = adapt_native_ranking(("a_cpu",), ("a", "b"))
        self.assertEqual(result.services, ("a",))

    def test_12_failure_contributes_zero_top_k_utility(self):
        for status in ("METHOD_FAILURE", "ADAPTER_FAILURE", "DATA_FAILURE", "TIMEOUT"):
            self.assertEqual(failure_zero_top_k(status, ("target",), "target"), (0, 0, 0, 0, 0))

    def test_13_success_top_k_is_nested_and_denominator_independent(self):
        self.assertEqual(
            failure_zero_top_k("SUCCESS", ("a", "target", "b"), "target"),
            (0, 1, 1, 1, 1),
        )

    def test_14_duplicate_mapping_uses_first_native_occurrence(self):
        result = adapt_native_ranking(("a_cpu", "a_mem", "b_cpu"), ("a", "b"))
        self.assertEqual(result.services, ("a", "b"))
        self.assertEqual(result.duplicates, ("a_mem",))

    def test_15_unknown_mapping_is_not_invented(self):
        with self.assertRaises(AdapterError):
            adapt_native_ranking(("unknown_cpu",), ("a", "b"))

    def test_16_trace_microseconds_seconds_conversion_and_half_open_end(self):
        anchor = 1_700_000_000
        self.assertTrue(span_end_in_canonical_window(anchor * 1_000_000 - 600_000_000, 0, anchor))
        self.assertFalse(span_end_in_canonical_window(anchor * 1_000_000 + 600_000_000, 0, anchor))

    def test_17_microrank_cap_is_eleven(self):
        ranks = [f"a_{index}" for index in range(11)]
        self.assertEqual(validate_native_output("MicroRank", {"ranks": ranks}), tuple(ranks))
        with self.assertRaises(Exception):
            validate_native_output("MicroRank", {"ranks": ranks + ["a_11"]})

    def test_18_circa_silent_fallback_is_detected(self):
        columns = ("a_cpu", "b_mem")
        self.assertTrue(detect_silent_fallback("CIRCA", {"adj": [], "node_names": columns, "ranks": columns}, columns))

    def test_19_causalrca_empty_graph_input_order_is_detected(self):
        columns = ("a_cpu", "b_mem")
        self.assertTrue(detect_silent_fallback("CausalRCA", {"adj": [[0, 0], [0, 0]], "node_names": columns, "ranks": columns}, columns))

    def test_20_mmbaro_dataset_keys_are_exact(self):
        self.assertEqual(mmbaro_dataset_key("re2ob"), "mm-ob")
        self.assertEqual(mmbaro_dataset_key("re2tt"), "mm-tt")

    def test_21_seed_and_hash_controls_are_frozen_in_worker_environment(self):
        from src.baseline_eval.confirmatory import FIXED_WORKER_ENV

        self.assertEqual(FIXED_WORKER_ENV["PYTHONHASHSEED"], "20260830")
        self.assertEqual(FIXED_WORKER_ENV["CUDA_VISIBLE_DEVICES"], "")

    def test_22_baseline_mrr_is_unavailable(self):
        from src.baseline_eval import evaluation

        self.assertFalse(hasattr(evaluation, "calculate_mrr"))
        source = Path(evaluation.__file__).read_text(encoding="utf-8")
        self.assertIn('"MRR_legality": "NOT-IDENTIFIABLE"', source)

    def test_23_frozen_ada_rca_paths_unchanged(self):
        from src.baseline_eval import assert_ada_rca_frozen_unchanged

        assert_ada_rca_frozen_unchanged(ROOT)

    def test_24_rcaeval_clean_remains_clean(self):
        result = verify_rcaeval_clean()
        self.assertTrue(result["clean"])

    def test_25_microrank_synthetic_prediction_fingerprint_is_deterministic(self):
        first = synthetic_preflight("MicroRank")
        second = synthetic_preflight("MicroRank")
        self.assertEqual(first["fingerprint"], second["fingerprint"])


if __name__ == "__main__":
    unittest.main()
