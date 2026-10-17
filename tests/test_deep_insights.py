"""Validate null-model mechanics and decision thresholds on small known examples."""
import unittest
import numpy as np
import pandas as pd
from src.analytics import load_data
from src.deep_insights import category_null,growth_bridge,attachment_cases,basket_economics_uncertainty

class DeepInsightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=load_data()

    def test_shuffle_never_creates_pairs_in_single_line_baskets(self):
        d=pd.DataFrame(dict(transaction=range(20),category=['A','B']*10,branch='Garden',
                            month='2026-01',order_type='Takeaway',hour=10))
        t=category_null(d,draws=19)
        self.assertEqual(t.pair_baskets.iloc[0],0)
        self.assertEqual(t.expected_pairs.iloc[0],0)
        self.assertTrue(np.isnan(t.conditional_enrichment.iloc[0]))

    def test_label_shuffle_is_seeded_and_preserves_observed_pair_counts(self):
        d=self.x[self.x.date<'2026-01-10']
        a=category_null(d,draws=19);b=category_null(d,draws=19)
        pd.testing.assert_frame_equal(a,b)
        row=a[a.category_a.eq('Bakery') & a.category_b.eq('Matcha & Tea')].iloc[0]
        sets=d.groupby('transaction').category.agg(set)
        self.assertEqual(row.pair_baskets,int(sets.map(lambda v:{'Bakery','Matcha & Tea'}.issubset(v)).sum()))
        self.assertTrue(a.enrichment_q.between(0,1).all())

    def test_growth_bridge_exactly_reconciles_recorded_gp_per_day(self):
        m,b=growth_bridge(self.x)
        self.assertAlmostEqual(b.gp_per_day_change.sum(),m.gp_per_day.iloc[-1]-m.gp_per_day.iloc[0],places=9)

    def test_rebate_leakage_and_no_discount_increment(self):
        t=attachment_cases(self.x)
        free=t[(t.assumed_adoption.eq(.03)) & t.assumed_rebate_rate.eq(0)].iloc[0]
        rebate=t[(t.assumed_adoption.eq(.03)) & t.assumed_rebate_rate.eq(.1)].iloc[0]
        self.assertAlmostEqual(free.hypothetical_gp_before_expense,
            free.eligible_a_only_baskets*.03*free.attached_unit_gp)
        self.assertAlmostEqual(free.hypothetical_gp_before_expense-rebate.hypothetical_gp_before_expense,
            rebate.rebate_per_unit*(rebate.existing_pairs+.03*rebate.eligible_a_only_baskets))
        break_even=rebate.eligible_a_only_baskets*rebate.break_even_adoption*(rebate.attached_unit_gp-rebate.rebate_per_unit)-rebate.existing_pairs*rebate.rebate_per_unit
        self.assertAlmostEqual(break_even,0,places=8)

    def test_day_block_uncertainty_is_finite_and_reproducible(self):
        a=basket_economics_uncertainty(self.x,draws=99)
        self.assertEqual(a,basket_economics_uncertainty(self.x,draws=99))
        self.assertLess(a['low'],a['high'])

if __name__=='__main__':unittest.main()
