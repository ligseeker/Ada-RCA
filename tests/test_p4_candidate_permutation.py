import unittest

import numpy as np

from src.rca.p4 import CandidateEvent, build_candidate_representation, permute_event, rank_candidates


class P4CandidatePermutationTest(unittest.TestCase):
    def test_percentiles_and_scores_are_equivariant(self):
        event = CandidateEvent("e", ("a", "b", "c"), np.array([[1., 8.], [5., 2.], [3., 4.]]))
        weights = np.array([0.2, -0.1, 0.7, 0.4])
        original = build_candidate_representation(event.features, True)
        original_scores = original.dot(weights)
        permutation = [2, 0, 1]
        moved = permute_event(event, permutation)
        moved_representation = build_candidate_representation(moved.features, True)
        by_identity = {candidate: moved_representation[index] for index, candidate in enumerate(moved.candidates)}
        score_by_identity = {candidate: float(moved_representation[index].dot(weights)) for index, candidate in enumerate(moved.candidates)}
        for index, candidate in enumerate(event.candidates):
            np.testing.assert_allclose(by_identity[candidate], original[index], rtol=0, atol=0)
            self.assertAlmostEqual(score_by_identity[candidate], float(original_scores[index]), places=15)
        original_ranking = rank_candidates(event.candidates, original_scores)
        moved_ranking = rank_candidates(moved.candidates, moved_representation.dot(weights))
        self.assertEqual(moved_ranking, original_ranking)


if __name__ == "__main__":
    unittest.main()
