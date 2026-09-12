import unittest

import numpy as np

from src.baseline_eval.causalrca_diagnostic import (
    PageRankRecorder,
    classify_causalrca_output,
    instrument_pagerank,
)


class _FakePageRank:
    calls = 0

    def fit_transform(self, matrix, scale=1):
        type(self).calls += 1
        return np.asarray(matrix).sum(axis=1) * scale


class _RaisingPageRank:
    def fit_transform(self, matrix):
        raise ValueError("synthetic PageRank failure")


class CausalRCADiagnosticTest(unittest.TestCase):
    def test_success_preserves_return_value_and_records_scores(self):
        recorder = PageRankRecorder()
        original = _FakePageRank.fit_transform
        model = _FakePageRank()
        with instrument_pagerank(_FakePageRank, recorder):
            observed = model.fit_transform(np.array([[0.0, 1.0], [2.0, 0.0]]), scale=2)
        self.assertIs(_FakePageRank.fit_transform, original)
        self.assertTrue(np.array_equal(observed, np.array([2.0, 4.0])))
        self.assertEqual([event["event"] for event in recorder.events], [
            "pagerank_called", "pagerank_success"
        ])
        self.assertEqual(recorder.events[0]["matrix"]["nonzero_count"], 2)
        self.assertEqual(recorder.events[1]["scores"]["unique_count"], 2)

    def test_exception_is_reraised_unchanged_and_recorded(self):
        recorder = PageRankRecorder()
        with self.assertRaisesRegex(ValueError, "synthetic PageRank failure"):
            with instrument_pagerank(_RaisingPageRank, recorder):
                _RaisingPageRank().fit_transform(np.ones((2, 2)))
        self.assertEqual(recorder.events[-1]["event"], "pagerank_exception")
        self.assertEqual(recorder.events[-1]["exception_type"], "ValueError")

    def test_empty_graph_fallback_requires_independent_trigger(self):
        result = classify_causalrca_output(
            returned_ranks=["A", "B"],
            node_names=["A", "B"],
            adjacency=np.zeros((2, 2)),
        )
        self.assertEqual(result["classification"], "UNRESOLVED_SILENT_FALLBACK")
        failed = classify_causalrca_output(
            returned_ranks=["A", "B"],
            node_names=["A", "B"],
            adjacency=np.zeros((2, 2)),
            fallback_signature_observed=True,
        )
        self.assertEqual(failed["classification"], "METHOD_FAILURE")

    def test_nonempty_graph_exception_is_failure(self):
        result = classify_causalrca_output(
            returned_ranks=["A", "B"],
            node_names=["A", "B"],
            adjacency=np.ones((2, 2)),
            pagerank_exception_observed=True,
        )
        self.assertEqual(result["classification"], "METHOD_FAILURE")

    def test_valid_order_equal_ranking_is_not_failure(self):
        result = classify_causalrca_output(
            returned_ranks=["A", "B"],
            node_names=["A", "B"],
            adjacency=np.array([[0.0, 1.0], [1.0, 0.0]]),
        )
        self.assertEqual(result["classification"], "SUCCESS")
        self.assertTrue(result["ranks_equal_node_names"])

    def test_empty_ranking_is_failure(self):
        result = classify_causalrca_output(
            returned_ranks=[], node_names=["A"], adjacency=np.zeros((1, 1))
        )
        self.assertEqual(result["classification"], "METHOD_FAILURE")


if __name__ == "__main__":
    unittest.main()
