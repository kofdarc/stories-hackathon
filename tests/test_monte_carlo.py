"""Checks for the Monte Carlo: reproducibility, the left-digit formula and break-even identities."""
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import monte_carlo as mc


class MonteCarloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.r = mc.run(out=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_perceived_price_matches_paper_example(self):
        # Strulov-Shlain (2023): p=4.99, theta=0.5, focal ending 0.19 -> 4.59
        self.assertAlmostEqual(mc.perceived(4.99, .5, .19), 4.59, places=6)
        self.assertAlmostEqual(mc.perceived(5.09, 0.0), 5.09)

    def test_left_digit_crossing_is_perceived_as_larger_than_cents(self):
        jump = mc.perceived(5.00, .22) - mc.perceived(4.99, .22)
        self.assertGreater(jump, .2)

    def test_seeded_run_is_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            again = mc.run(out=d)
        np.testing.assert_allclose(again['draws'].to_numpy(), self.r['draws'].to_numpy())

    def test_break_even_elasticity_gives_zero_gp_change(self):
        m, e = self.r['margin'], self.r['break_even_eps']
        self.assertAlmostEqual(1.05 ** e * (1.05 - (1 - m)) - m, 0, places=9)

    def test_summary_probabilities_are_valid(self):
        s = self.r['summary']
        self.assertTrue(s.p_positive.between(0, 1).all())
        self.assertTrue((s.p5 <= s.p50).all() and (s.p50 <= s.p95).all())
        self.assertEqual(len(self.r['draws']), mc.N)

    def test_elasticity_curve_is_monotone(self):
        c = self.r['curve'].down_beats_up.to_numpy()
        self.assertTrue((np.diff(c) <= 1e-9).all())


if __name__ == '__main__':
    unittest.main()
