"""Checks for the outside-in chains: detection power, arithmetic identities and the pricing-rule fingerprints."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import outside_in_chains as oc


class OutsideInTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = oc.load(ROOT / 'stories_transactions.csv')
        cls.o = oc.baskets(cls.x)
        cls.r = oc.research(ROOT / 'data/external/outside_research_2026.csv')

    def test_step_model_recovers_planted_declines(self):
        p = oc.planted_decline(self.o, drops=(.2, .85))
        for row in p.itertuples():
            self.assertLess(row.low, row.planted_decline + .05)
            self.assertGreater(row.high, row.planted_decline - .05)
            self.assertLess(row.high, 0)

    def test_recorded_war_step_excludes_sector_decline(self):
        s, _ = oc.war_step(self.o, placebo=False)
        self.assertGreater(s['low'], -.10)
        self.assertLess(s['low'], s['step_pct'])
        self.assertLess(s['step_pct'], s['high'])

    def test_branch_rules_are_exact_and_static(self):
        f = oc.fingerprints(self.x, self.o)
        for k in ['harbour_price_is_garden_x105', 'uptown_price_is_garden_x096',
                  'garden_cost_is_harbour_x143', 'uptown_cost_is_harbour_x096']:
            self.assertEqual(f[k], 1.0)
        self.assertEqual((f['max_distinct_prices'], f['max_distinct_costs']), (1, 1))

    def test_hour_savings_reconcile_with_gp_and_cost(self):
        g = oc.hour_economics(self.o, oc.tariff_usd(self.r))
        h = oc.hour_summary(g)
        self.assertAlmostEqual(g.gp.sum(), self.o.gp.sum(), places=6)
        row = h[(h.branch == 'Uptown') & (h.hour == 7)].iloc[0]
        s = g[(g.branch == 'Uptown') & (g.hour == 7)]
        cost = (s.cost_base * s.days).sum()
        self.assertAlmostEqual(row.six_month_saving_base_no_recapture, cost - s.gp.sum(), places=6)
        self.assertAlmostEqual(row.six_month_saving_base_half_recapture - row.six_month_saving_base_no_recapture,
                               .5 * s.gp.sum(), places=6)

    def test_tariffs_convert_at_stated_rate(self):
        t = oc.tariff_usd(self.r)
        self.assertEqual(list(t.index), [1, 2, 3, 4, 5, 6])
        self.assertAlmostEqual(t.loc[4], 49395 / oc.LBP_PER_USD)

    def test_price_points_cross_a_dollar_and_proposals_sit_below_it(self):
        _, t = oc.price_points(self.x)
        self.assertTrue(len(t) > 0)
        self.assertTrue((np.floor(t.harbour) > np.floor(t.garden)).all())
        self.assertTrue((t.proposed < np.floor(t.harbour)).all())
        self.assertTrue((t.proposed > t.harbour_cost).all())

    def test_cost_inflation_scenario_is_linear_in_war_cogs(self):
        m, shock, price, war_cogs, margin = oc.price_freeze(self.x)
        self.assertAlmostEqual(war_cogs, m.set_index('month').loc[3:6, 'cogs'].sum())
        for row in shock.itertuples():
            self.assertAlmostEqual(row.gp_overstated, row.cogs_increase_from_march * war_cogs)
        five = price[price.price_increase.eq(.05)].iloc[0]
        self.assertAlmostEqual(five.break_even_volume_loss, .05 / (margin + .05))

    def test_matcha_scenarios_scale_with_units(self):
        _, stat, shock, _, _, _ = oc.matcha(self.x, ROOT / 'missing.csv')
        units = self.x[self.x['product'].isin(oc.MATCHA)].quantity.sum()
        self.assertEqual(stat['units'], units)
        row = shock.iloc[0]
        self.assertAlmostEqual(row.six_month_gp_hit, units * row.grams_per_drink * row.usd_per_kg_increase / 1000)


if __name__ == '__main__':
    unittest.main()
