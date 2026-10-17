"""Validate whole-basket downside gates and operational contribution accounting."""
import unittest
from src.analytics import load_data,baskets,counterfactual
from src.causal_decisions import price_retention_gates,upsell_capacity_gates,procurement_quality_gates

class CausalDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=load_data()

    def test_whole_basket_exposure_and_price_threshold(self):
        p=price_retention_gates(self.x,self.x).set_index('product').loc['Sparkling Water']
        self.assertGreater(p.containing_basket_gp,p.item_gp)
        self.assertLess(p.whole_basket_loss_break_even,p.item_only_loss_break_even)
        loss=p.whole_basket_loss_break_even
        self.assertAlmostEqual(p.hypothetical_uplift_before_response*(1-loss)-p.containing_basket_gp*loss,0,places=8)
        self.assertAlmostEqual(p.whole_basket_loss_break_even,.04848455,places=5)

    def test_price_scope_restores_complete_baskets(self):
        target=self.x[self.x.branch.eq('Garden') & self.x['product'].eq('Sparkling Water')]
        complete=self.x[self.x.transaction.isin(target.transaction)]
        result=price_retention_gates(complete,self.x).set_index('product').loc['Sparkling Water']
        self.assertAlmostEqual(result.containing_basket_gp,baskets(complete).gp.sum())

    def test_capacity_losses_and_expenses_subtract_exactly(self):
        a=upsell_capacity_gates(self.x).set_index('scope').loc['Evening 19–23']
        b=upsell_capacity_gates(self.x,expense=10,lost_baskets=40,displaced_gp=5).set_index('scope').loc['Evening 19–23']
        self.assertAlmostEqual(b.net_contribution,a.net_contribution-15-40*a.observed_gp_per_basket)
        self.assertLess(b.net_contribution,0)
        self.assertAlmostEqual(a.lost_baskets_break_even*a.observed_gp_per_basket,a.hypothetical_attachment_gp)

    def test_procurement_gates_match_independent_scenario(self):
        p=procurement_quality_gates(self.x,self.x)
        for row in p.itertuples():
            r=counterfactual(self.x,self.x,recovery=row.assumed_cash_recoverable_fraction)
            self.assertAlmostEqual(row.hypothetical_saving_before_losses,r['net_benefit'])
            self.assertAlmostEqual(row.proportional_garden_basket_loss_break_even,r['break_even_demand_loss'])

    def test_zero_adoption_and_invalid_inputs(self):
        t=upsell_capacity_gates(self.x,adoption=0,expense=10)
        self.assertTrue(t.net_contribution.eq(-10).all())
        with self.assertRaises(ValueError):upsell_capacity_gates(self.x,adoption=2)

if __name__=='__main__':unittest.main()
