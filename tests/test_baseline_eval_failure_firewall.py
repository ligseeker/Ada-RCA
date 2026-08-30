from pathlib import Path
import os
import random
import tempfile
import unittest

import numpy as np

from src.baseline_eval import (
    CaseRecord,
    DenominatorError,
    FirewallBreach,
    TerminalStatus,
    assert_firewall_safe_record,
    canonical_seed_environment,
    detect_silent_fallback,
    persist_case_record,
    seed_in_process,
    validate_case_denominator,
)


class BaselineEvalFailureAndFirewallTest(unittest.TestCase):
    def test_each_failure_status_is_persisted_without_dummy_ranking(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for index, status in enumerate(
                (
                    TerminalStatus.METHOD_FAILURE,
                    TerminalStatus.ADAPTER_FAILURE,
                    TerminalStatus.DATA_FAILURE,
                    TerminalStatus.TIMEOUT,
                )
            ):
                record = CaseRecord(
                    protocol_version="baseline_protocol_freeze_v1",
                    method="SyntheticMethod",
                    dataset="re2ob",
                    case_id=f"case-{index}",
                    status=status,
                    native_output_kind="NONE",
                    native_ranking=(),
                    adapted_ranking=(),
                    error_type=status.value,
                )
                path = persist_case_record(output, record)
                text = path.read_text(encoding="utf-8")
                self.assertIn(status.value, text)
                self.assertNotIn("dummy", text.lower())
                self.assertNotIn("root_service", text)

    def test_silent_column_order_fallback_is_detected(self):
        columns = ("a_cpu", "b_mem")
        fallback = {"adj": [], "node_names": list(columns), "ranks": list(columns)}
        self.assertTrue(detect_silent_fallback("CIRCA", fallback, columns))
        self.assertTrue(detect_silent_fallback("CausalRCA", fallback, columns))
        self.assertFalse(detect_silent_fallback("BARO", {"ranks": list(columns)}, columns))

    def test_successful_subset_is_rejected_but_failures_keep_denominator(self):
        expected = tuple(f"case-{i:02d}" for i in range(90))
        records = tuple(
            CaseRecord(
                protocol_version="baseline_protocol_freeze_v1",
                method="SyntheticMethod",
                dataset="re2ob",
                case_id=case_id,
                status=TerminalStatus.SUCCESS if i else TerminalStatus.METHOD_FAILURE,
                native_output_kind="INDICATOR_RANKING" if i else "NONE",
                native_ranking=("a_cpu",) if i else (),
                adapted_ranking=("a",) if i else (),
            )
            for i, case_id in enumerate(expected)
        )
        validate_case_denominator(records, expected)
        with self.assertRaises(DenominatorError):
            validate_case_denominator(records[1:], expected)

    def test_seed_policy_controls_python_numpy_and_hash_environment(self):
        env = canonical_seed_environment(20260830)
        self.assertEqual(env["PYTHONHASHSEED"], "20260830")
        seed_in_process(20260830, include_torch=False)
        first = (random.random(), float(np.random.random()))
        seed_in_process(20260830, include_torch=False)
        second = (random.random(), float(np.random.random()))
        self.assertEqual(first, second)

    def test_performance_fields_are_rejected_from_case_records(self):
        safe = {
            "method": "SyntheticMethod",
            "dataset": "re2ob",
            "case_id": "case-00",
            "status": "SUCCESS",
            "adapted_ranking": ["a"],
        }
        assert_firewall_safe_record(safe)
        for forbidden in ("root_service", "root_rank", "AC@1", "Avg@5", "MRR", "winner", "delta"):
            with self.assertRaises(FirewallBreach):
                assert_firewall_safe_record({**safe, forbidden: 1})


if __name__ == "__main__":
    unittest.main()
