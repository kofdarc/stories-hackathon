"""Meaningful checks of transaction grain, counterfactual identities and filters."""
import unittest
import pandas as pd
from pathlib import Path
from src.analytics import load_data,baskets,counterfactual,decomposition,validate,associations

class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.x=load_data()

    def test_grain_and_reconciliation(self):
        o=baskets(self.x)
        self.assertEqual(len(o),33887);self.assertEqual(len(self.x),51177)
        self.assertAlmostEqual(o.revenue.sum(),self.x.revenue.sum(),places=7)
        self.assertAlmostEqual(o.gp.sum(),self.x.gp.sum(),places=7)

    def test_matched_counterfactual(self):
        g=self.x[self.x.branch.eq('Garden')]
        costs=self.x[self.x.branch.eq('Harbour')].groupby('product').cost.first()
        expected=sum(g.quantity*(g.cost-g["product"].map(costs)))
        result=counterfactual(self.x,self.x)
        self.assertAlmostEqual(expected,result['matched_gap'],places=7)
        self.assertAlmostEqual(expected,15923.47,places=2)
        self.assertAlmostEqual(result['gp']-result['baseline_gp'],expected,places=7)

    def test_zero_and_loss_boundary(self):
        baseline=counterfactual(self.x,self.x,recovery=0)
        self.assertAlmostEqual(baseline['net_benefit'],0)
        total=counterfactual(self.x,self.x,demand_loss=1,expense=100)
        self.assertEqual(total['gp'],0)
        self.assertAlmostEqual(total['net_benefit'],-total['baseline_gp']-100)
        r=counterfactual(self.x,self.x,price_change=.05,expense=50)
        at_break=counterfactual(self.x,self.x,price_change=.05,expense=50,demand_loss=r['break_even_demand_loss'])
        self.assertAlmostEqual(at_break['net_benefit'],0,places=7)

    def test_scope_and_missing_matches(self):
        d=self.x[self.x.date<'2026-02-01']
        r=counterfactual(d,d);self.assertLess(r['matched_gap'],counterfactual(self.x,self.x)['matched_gap'])
        garden=d[d.branch.eq('Garden')]
        missing=counterfactual(garden,garden)
        self.assertEqual(missing['unmatched_lines'],len(garden))
        self.assertEqual(missing['matched_gap'],0)

    def test_decomposition_adds_exactly(self):
        means=self.x.groupby('branch').apply(lambda g:g.gp.sum()/g.quantity.sum())
        # Source GP rounding may differ from the analytic price/cost identity.
        analytic=self.x.assign(analytic_gp=lambda d:d.quantity*(d.price*(1-d.discount)-d.cost))
        value=analytic.groupby('branch').apply(lambda g:g.analytic_gp.sum()/g.quantity.sum())
        result=decomposition(self.x)
        self.assertAlmostEqual(result.iloc[:,1].sum(),means.Harbour-means.Garden,places=10)
        self.assertAlmostEqual(result.loc[result.factor.ne('source_rounding')].iloc[:,1].sum(),value.Harbour-value.Garden,places=10)

    def test_quality_and_half_cent_disclosure(self):
        q=validate(self.x)
        self.assertEqual(q['metadata_conflicts'],0);self.assertEqual(q['missing_required'],0)
        self.assertEqual(q['exact_duplicate_excess'],132)
        self.assertGreaterEqual(q['maximum_gp_error'],0)

    def test_invalid_scenario(self):
        with self.assertRaises(ValueError): counterfactual(self.x,self.x,recovery=2)

    def test_product_price_alignment(self):
        from src.analytics import matched_products
        p=matched_products(self.x).set_index('product')
        g=self.x[self.x.branch.eq('Garden')]
        uplift=g['product'].map(p.price_Harbour/p.price_Garden-1)
        self.assertFalse(uplift.isna().any())
        self.assertGreater((g.revenue*uplift).sum(),4000)

    def test_readme_headline_sync(self):
        from src.analytics import ROOT
        text=(ROOT/'README.md').read_text()
        for number in [f'{self.x.revenue.sum():,.2f}',f'{self.x.gp.sum():,.2f}',
                       f"{counterfactual(self.x,self.x)['matched_gap']:,.2f}"]:
            self.assertIn(number,text)

    def test_no_pair_is_supported(self):
        one=self.x[self.x["product"].eq(self.x["product"].iloc[0])]
        self.assertTrue(associations(one).empty)

if __name__=='__main__': unittest.main()
