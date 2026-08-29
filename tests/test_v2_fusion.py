import inspect
from pathlib import Path
import unittest

import numpy as np
from sklearn.preprocessing import StandardScaler

from src.rca.final_method import FINAL_Z2_DIMENSION, sha256_file
from src.rca.p4 import fit_predict_oof, verify_complete_prediction
from src.rca.schema import RCACaseInput, SchemaValidationError
from src.rca.v2_fusion import (
    F1_DIMENSION,
    F1_FEATURE_NAMES,
    MODALITY_ORDER,
    PAIR_ORDER,
    XC_DIMENSION,
    XC_FEATURE_NAMES,
    FusionCaseFeatures,
    build_f1_representation,
    build_xc30,
    deterministic_misalignment_shifts,
    reorder_fusion_case,
    shifted_source_indices,
)
from src.rca.v2_stats import f1_gate_decision, paired_joint_fault_bootstrap


V1_SOURCE_SHA256 = {
    "src/rca/features.py": "91d452cc17bb2bdc51712a65e13cd079057f1d112016ef94836bbc13445e0a11",
    "src/rca/p4.py": "c173cfee9057fd9d9eadc774d19881d0db25357878f2045b77aec79498e77b1a",
    "src/rca/final_method.py": "8587e9790d6a1d0d73ce9ae3b3149baea6a8e61153475f48f0cdc7143b6dbed7",
    "src/rca/evaluator.py": "1002f10457c422560f27e22b30ccd7ef2c77d68352b750c14376b3bd8197b3fb",
    "src/rca/schema.py": "95407ed538b99f43248a2c146e706e12b72df5e220374dd5576e20d36ecf9a81",
}


def synthetic_case(case_id="opaque", candidates=None):
    candidates = tuple(candidates or ("a", "b", "c", "d", "e"))
    n = len(candidates)
    base = np.zeros((n, 4, 8), dtype=np.float64)
    morphology = np.zeros((n, 4, 9), dtype=np.float64)
    trajectories = np.zeros((n, 4, 80), dtype=np.float64)
    masks = np.ones((n, 4, 80), dtype=bool)
    active = np.ones((n, 4), dtype=np.float64)
    base[:, :, 7] = 1.0
    morphology[:, :, 8] = active
    for candidate in range(n):
        for modality in range(4):
            base[candidate, modality, 3] = 15.0 * (candidate + modality)
            base[candidate, modality, 4] = 0.0
            morphology[candidate, modality, 3] = (candidate + modality) / float(n + 4)
            morphology[candidate, modality, 4] = (candidate + 2 * modality) / float(n + 8)
            trajectories[candidate, modality, 40 + ((candidate + modality) % 5)] = 1.0
    return FusionCaseFeatures(case_id, candidates, base, morphology, trajectories, masks, active)


class V2FusionRepresentationTest(unittest.TestCase):
    def test_v1_source_and_artifact_integrity_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        for relative, expected in V1_SOURCE_SHA256.items():
            self.assertEqual(sha256_file(root / relative), expected)
        for dataset in ("re2ob", "re2tt"):
            audit = __import__("json").loads(
                (root / "artifacts" / "final_method" / dataset / "replay_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(audit["integrity_status"], "INTEGRITY_VALID")
            self.assertTrue(audit["persisted_state_to_committed_p4_a2"]["ranking_identical"])

    def test_dimensions_and_frozen_orders(self):
        self.assertEqual(FINAL_Z2_DIMENSION, 68)
        self.assertEqual(MODALITY_ORDER, ("M", "L", "TE", "TL"))
        self.assertEqual(PAIR_ORDER, (("M", "L"), ("M", "TE"), ("M", "TL"), ("L", "TE"), ("L", "TL"), ("TE", "TL")))
        self.assertEqual(XC_DIMENSION, 30)
        self.assertEqual(len(XC_FEATURE_NAMES), 30)
        self.assertEqual(F1_DIMENSION, 98)
        self.assertEqual(len(F1_FEATURE_NAMES), 98)

    def test_aligned_xc_semantics_and_finiteness(self):
        case = synthetic_case()
        xc = build_xc30(case)
        self.assertEqual(xc.shape, (5, 30))
        self.assertTrue(np.all(np.isfinite(xc)))
        self.assertTrue(np.all(xc[:, 4::5] == 1.0))
        self.assertTrue(np.all((xc[:, 3::5] >= 0.0) & (xc[:, 3::5] <= 1.0)))

    def test_missing_and_sentinel_semantics(self):
        case = synthetic_case()
        base = case.base.copy()
        morphology = case.morphology.copy()
        masks = case.observation_masks.copy()
        active = case.morphology_active.copy()
        base[0, 0, 4] = 1.0
        active[0, 1] = 0.0
        morphology[0, 1, 8] = 0.0
        masks[0, 0, 40:] = False
        modified = FusionCaseFeatures(case.case_id, case.candidates, base, morphology, case.trajectories, masks, active)
        xc = build_xc30(modified)
        self.assertEqual(xc[0, 0], 1.0)
        self.assertEqual(xc[0, 1], 1.0)
        self.assertEqual(xc[0, 2], 1.0)
        self.assertEqual(xc[0, 3], 0.0)
        self.assertEqual(xc[0, 4], 0.0)

    def test_feature_builder_has_no_label_or_identity_input(self):
        parameters = set(inspect.signature(build_xc30).parameters)
        self.assertEqual(parameters, {"case", "shifts"})
        forbidden = ("root", "fault", "service_identity")
        self.assertFalse(any(token in name for name in XC_FEATURE_NAMES for token in forbidden))

    def test_misalignment_is_deterministic_nonzero_and_distinct(self):
        first = deterministic_misalignment_shifts("opaque-case", 11)
        second = deterministic_misalignment_shifts("opaque-case", 11)
        self.assertEqual(first, second)
        self.assertEqual(first["M"], 0)
        non_metric = tuple(first[modality] for modality in MODALITY_ORDER[1:])
        self.assertTrue(all(value != 0 for value in non_metric))
        self.assertEqual(len(set(non_metric)), 3)

    def test_misalignment_preserves_each_modality_row_multiset(self):
        case = synthetic_case(candidates=tuple("abcdefghijk"))
        shifts = deterministic_misalignment_shifts(case.case_id, len(case.candidates))
        sources = shifted_source_indices(len(case.candidates), shifts)
        for modality_index, modality in enumerate(MODALITY_ORDER):
            indices = sources[modality]
            self.assertEqual(sorted(indices.tolist()), list(range(len(case.candidates))))
            for values in (
                case.base,
                case.morphology,
                case.trajectories,
                case.observation_masks,
            ):
                original = np.sort(values[:, modality_index, :], axis=0)
                shifted = np.sort(values[indices, modality_index, :], axis=0)
                np.testing.assert_array_equal(original, shifted)
            np.testing.assert_array_equal(
                np.sort(case.morphology_active[:, modality_index]),
                np.sort(case.morphology_active[indices, modality_index]),
            )

    def test_misalignment_does_not_change_original_z2(self):
        case = synthetic_case(candidates=tuple("abcdefghijk"))
        aligned = build_f1_representation(case, misaligned=False)
        misaligned = build_f1_representation(case, misaligned=True)
        np.testing.assert_array_equal(aligned.z2, misaligned.z2)
        np.testing.assert_array_equal(aligned.event.features[:, :68], misaligned.event.features[:, :68])
        self.assertFalse(np.array_equal(aligned.xc30, misaligned.xc30))

    def test_candidate_permutation_can_be_restored_before_building(self):
        case = synthetic_case()
        permutation = (2, 4, 0, 3, 1)
        permuted = reorder_fusion_case(case, tuple(case.candidates[index] for index in permutation))
        restored = reorder_fusion_case(permuted, case.candidates)
        np.testing.assert_array_equal(build_xc30(restored), build_xc30(case))
        np.testing.assert_array_equal(restored.z2_values(), case.z2_values())

    def test_complete_rankings_and_train_only_scaler(self):
        events = {}
        roots = {}
        assignments = {}
        for index in range(9):
            case = synthetic_case(case_id="event-{}".format(index))
            base = case.base.copy()
            base[:, 0, 0] += float(index)
            varied = FusionCaseFeatures(
                case.case_id,
                case.candidates,
                base,
                case.morphology,
                case.trajectories,
                case.observation_masks,
                case.morphology_active,
            )
            representation = build_f1_representation(varied)
            events[case.case_id] = representation.event
            roots[case.case_id] = case.candidates[index % len(case.candidates)]
            assignments[case.case_id] = index % 3
        predictions, fits = fit_predict_oof(events, roots, assignments, relative=False)
        self.assertEqual(len(predictions), 9)
        for row in predictions:
            verify_complete_prediction(row, events[row["case_id"]].candidates, roots[row["case_id"]])
        train_rows = np.concatenate([
            event.features for case_id, event in events.items() if assignments[case_id] != 0
        ])
        expected = StandardScaler().fit(train_rows)
        np.testing.assert_allclose(fits[0].scaler_mean, expected.mean_, rtol=0, atol=0)
        np.testing.assert_allclose(fits[0].scaler_scale, expected.scale_, rtol=0, atol=0)
        all_rows = np.concatenate([event.features for event in events.values()])
        self.assertFalse(np.array_equal(fits[0].scaler_mean, StandardScaler().fit(all_rows).mean_))

    def test_label_firewall_remains_active(self):
        with self.assertRaises(SchemaValidationError):
            RCACaseInput(
                case_id="opaque",
                dataset="d",
                anchor_time=0.0,
                services=("a", "b"),
                metrics=None,
                logs=None,
                traces=None,
                metadata={"fault_type": "cpu"},
            )


class V2StatisticsTest(unittest.TestCase):
    @staticmethod
    def paired_rows(delta):
        left = {}
        right = {}
        faults = ("cpu", "mem", "disk", "socket", "delay", "loss")
        for dataset in ("re2ob", "re2tt"):
            left[dataset] = {}
            right[dataset] = {}
            for fault in faults:
                for index in range(15):
                    case_id = "{}-{}-{}".format(dataset, fault, index)
                    left[dataset][case_id] = {"fault_type": fault, "Avg@5": 0.5 + delta, "AC@1": 0.5, "AC@3": 0.5, "AC@5": 0.5, "MRR": 0.5}
                    right[dataset][case_id] = {"fault_type": fault, "Avg@5": 0.5, "AC@1": 0.5, "AC@3": 0.5, "AC@5": 0.5, "MRR": 0.5}
        return left, right

    def test_bootstrap_is_deterministic(self):
        left, right = self.paired_rows(0.1)
        first = paired_joint_fault_bootstrap(left, right, "Avg@5", resamples=100, seed=20260829)
        second = paired_joint_fault_bootstrap(left, right, "Avg@5", resamples=100, seed=20260829)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["equal_dataset_mean"]["point_delta"], 0.1)
        self.assertGreater(first["equal_dataset_mean"]["ci95"][0], 0.0)

    def test_gate_is_mechanical(self):
        bootstrap = {"equal_dataset_mean": {"ci95": [0.001, 0.1]}}
        deltas = {
            "aligned_minus_z2": {
                "re2ob": {"Avg@5": 0.01, "AC@1": 0.0},
                "re2tt": {"Avg@5": 0.02, "AC@1": -1.0 / 90.0},
            },
            "aligned_minus_misaligned": {
                "re2ob": {"Avg@5": 0.01},
                "re2tt": {"Avg@5": 0.01},
            },
        }
        decision = f1_gate_decision(bootstrap, bootstrap, deltas, True)
        self.assertEqual(decision["V2_F1"], "GO")
        deltas["aligned_minus_misaligned"]["re2tt"]["Avg@5"] = 0.0
        self.assertEqual(f1_gate_decision(bootstrap, bootstrap, deltas, True)["V2_F1"], "NO_GO")

    def test_ac1_guard_accepts_exact_one_case_loss(self):
        bootstrap = {"equal_dataset_mean": {"ci95": [0.001, 0.1]}}
        deltas = {
            "aligned_minus_z2": {
                "re2ob": {"Avg@5": 0.01, "AC@1": 0.0},
                "re2tt": {"Avg@5": 0.01, "AC@1": 0.7 - 0.7111111111111111},
            },
            "aligned_minus_misaligned": {
                "re2ob": {"Avg@5": 0.01},
                "re2tt": {"Avg@5": 0.01},
            },
        }
        decision = f1_gate_decision(bootstrap, bootstrap, deltas, True)
        self.assertTrue(decision["performance_checks"]["tt_ac1_guard"])
        self.assertEqual(decision["V2_F1"], "GO")


if __name__ == "__main__":
    unittest.main()
