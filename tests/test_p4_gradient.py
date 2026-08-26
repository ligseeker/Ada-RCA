import unittest

import numpy as np
from scipy.optimize import check_grad

from src.rca.p4 import conditional_logit_loss_gradient


class P4GradientTest(unittest.TestCase):
    def test_numerical_gradient_and_l2_penalty(self):
        events = (np.array([[0.2, 1.0], [1.2, -0.3], [-0.5, 0.4]]), np.array([[1.0, 0.0], [0.0, 1.0]]))
        roots = (1, 0)
        point = np.array([0.3, -0.7])
        error = check_grad(
            lambda w: conditional_logit_loss_gradient(w, events, roots, 1.0)[0],
            lambda w: conditional_logit_loss_gradient(w, events, roots, 1.0)[1],
            point,
        )
        self.assertLess(error, 1e-6)
        loss0, grad0 = conditional_logit_loss_gradient(point, events, roots, 0.0)
        loss1, grad1 = conditional_logit_loss_gradient(point, events, roots, 1.0)
        self.assertAlmostEqual(loss1 - loss0, 0.5 * float(point.dot(point)), places=12)
        np.testing.assert_allclose(grad1 - grad0, point, rtol=0, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
