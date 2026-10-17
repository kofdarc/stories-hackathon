"""Small mathematical checks for the analysis' consequential choices."""
import unittest

import numpy as np
import pandas as pd

from run_analysis import OUTCOMES, contrast, daily_did, orders


class AnalysisChecks(unittest.TestCase):
    def test_basket_grain_and_mixed_exposure(self):
        x = pd.DataFrame({
            'Transaction ID': ['a', 'a', 'b', 'c'], 'Quantity': [1, 2, 1, 1],
            'revenue_cents': [900, 1700, 1000, 850], 'gp_cents': [500, 900, 600, 450],
            'list_cents': [1000, 2000, 1000, 1000], 'cogs_cents': [400, 800, 400, 400],
            'd10': [True, False, False, False], 'd15': [False, True, False, True],
            'eligible': [True]*4, 'Branch': ['Harbour']*4,
            'date': pd.to_datetime(['2026-03-12']*4), 'month': ['2026-03']*4,
            'dow': [3]*4, 'daypart': [2]*4, 'known': [False]*4,
            'Customer ID': ['']*4, 'Order Type': ['Takeaway']*4})
        o = orders(x)
        self.assertEqual(len(o), 3)
        self.assertEqual(o.loc['a', 'group'], 'both')
        self.assertEqual(o.loc['b', 'group'], '0%')
        self.assertEqual(o.loc['c', 'group'], '15%')
        self.assertEqual(o.loc['a', 'units'], 3)
        self.assertEqual(o.loc['a', 'revenue'], 26)
        self.assertEqual(o.loc['a', 'gp'], 14)

    def test_standardization_removes_composition_gap(self):
        # Simpson's paradox: both treated subgroups are exactly +1, crude gap is +7.
        d = pd.DataFrame({'cell_key': ['a']*4+['b']*4,
                          't': [0, 0, 0, 1, 0, 1, 1, 1],
                          'date': pd.date_range('2026-01-01', periods=8)})
        for y in OUTCOMES:
            d[y] = np.where(d.cell_key.eq('a'), 0, 12)+d.t
        raw = contrast(d, d.t, [], 'raw')[0]
        adjusted = contrast(d, d.t, ['cell_key'], 'adjusted')[0]
        self.assertAlmostEqual(raw['difference'], 7)
        self.assertAlmostEqual(adjusted['difference'], 1)
        self.assertEqual(adjusted['coverage'], 1)

    def test_no_overlap_stays_unavailable(self):
        d = pd.DataFrame({'t': [0, 0, 1, 1], 'key': ['a', 'a', 'b', 'b']})
        r = contrast(d, d.t, ['key'], 'missing comparison')[0]
        self.assertTrue(np.isnan(r['difference']))
        self.assertEqual(r['coverage'], 0)
        self.assertEqual(r['treated_total'], 2)

    def test_daily_design_recovers_known_effect_with_common_growth(self):
        rows = []
        for day, date in enumerate(pd.date_range('2026-01-01', '2026-06-30')):
            campaign = (pd.Timestamp('2026-03-12') <= date <= pd.Timestamp('2026-03-19') or
                        pd.Timestamp('2026-05-12') <= date <= pd.Timestamp('2026-05-19'))
            for b, branch in enumerate(['Garden', 'Harbour', 'Uptown']):
                treated = campaign and branch == 'Harbour'
                rows.append({'date': date, 'Branch': branch, 'eligible': True,
                    'Quantity': 100+day+10*b+7*treated,
                    'revenue_cents': 80000+day*100+500*b+5000*treated,
                    'gp_cents': 50000+day*50+300*b+3000*treated,
                    'Transaction ID': f'{day}-{b}'})
        result = daily_did(pd.DataFrame(rows))
        target = result[result.scope.eq('all') & result.window_type.eq('campaign')]
        for outcome, effect in [('units', 7), ('gp', 30), ('revenue', 50), ('orders', 0)]:
            for value in target[target.outcome.eq(outcome)].difference:
                self.assertAlmostEqual(value, effect, places=7)


if __name__ == '__main__':
    unittest.main()
