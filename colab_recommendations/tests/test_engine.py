import io
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from colab_recommendations import engine as E


def fixture(days=70):
    rows=[]
    for day in pd.date_range('2026-01-01',periods=days):
        for branch in ['One','Two']:
            for order,hour,products,customer in [('a',8,['A'],'PRIVATE-C1'),('b',20,['A','B'],'PRIVATE-C2'),('c',20,['B'],None)]:
                for product in products:
                    price,cost=(10.,4.) if product=='A' else (6.,2.)
                    rows.append([f'PRIVATE-T-{day.date()}-{branch}-{order}',str(day.date()),f'{hour:02}:00:00',branch,customer,'Takeaway',product,'Coffee',1,price,0.,cost,price,price-cost])
    return pd.DataFrame(rows,columns=E.COLUMNS)


def load(raw):return E.load_transactions(io.StringIO(raw.to_csv(index=False)))[0]


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=fixture();cls.x=load(cls.raw)
    def result(self,**updates):
        p=E.defaults(self.x);p.update(branch='One',destination='Two',product='A',second='B',lookback=56,horizon=30,new_open=8,new_close=21)
        p.update(updates)
        return E.evaluate(self.x,p)
    def delta(self,result,layer):return result['ranking'].set_index('scenario').loc[layer,'delta_usd']
    def test_reconciliation_and_basket_grain(self):
        x,q=E.load_transactions(io.StringIO(self.raw.to_csv(index=False)))
        self.assertEqual(q['baskets'],420);self.assertEqual(q['gp_exceptions_over_half_cent'],0)
        self.assertAlmostEqual(E.baskets(x).gp.sum(),x.gp.sum())
        self.assertEqual(q['missing_customer_basket_share'],1/3)
    def test_bad_schema_and_conflicting_metadata(self):
        with self.assertRaises(ValueError):load(self.raw.drop(columns='Quantity'))
        bad=self.raw.copy();bad.loc[2,'Branch']='Elsewhere'
        with self.assertRaises(ValueError):load(bad)
    def test_bad_financial_fields(self):
        for field,value in [('Quantity',-1),('Quantity',1.5),('Discount Rate',1.1),('Unit Cost (USD)',np.inf)]:
            bad=self.raw.copy();bad[field]=bad[field].astype(float);bad.loc[0,field]=value
            with self.assertRaises(ValueError):load(bad)
    def test_duplicate_sensitivity_preserves_baskets(self):
        raw=pd.concat([self.raw,self.raw.iloc[:1]],ignore_index=True)
        keep,q=E.load_transactions(io.StringIO(raw.to_csv(index=False)))
        drop,_=E.load_transactions(io.StringIO(raw.to_csv(index=False)),True)
        self.assertEqual(q['exact_duplicate_excess'],1)
        self.assertEqual(keep.transaction.nunique(),drop.transaction.nunique())
        self.assertAlmostEqual(keep.revenue.sum()-drop.revenue.sum(),10)
    def test_zero_interventions_and_baseline(self):
        r=self.result(price_increase=0,item_discount=0,combo_discount=0,current_order=0,service_quantile=0)
        self.assertEqual(self.delta(r,'Do nothing'),0)
        for layer in ['Opening hours','Price increase','Expiry markdown','Loyalty','Item discount','Two-item combo','Delivery offer']:
            self.assertAlmostEqual(self.delta(r,layer),0)
    def test_removed_hours_full_baskets_and_recapture(self):
        # 20:00 baskets contribute 14/day (AB=10 + B=4).
        r=self.result(new_close=20,avoidable_hour_cost=2,recapture=.25)
        self.assertAlmostEqual(self.delta(r,'Opening hours'),30*(2-14*.75))
    def test_extension_has_no_invented_demand(self):
        r=self.result(new_open=7,extension_orders_hour=3,extension_gp_order=4,extension_hour_cost=2)
        self.assertAlmostEqual(self.delta(r,'Opening hours'),30*(12-2))
    def test_closure_capacity_and_exit(self):
        r=self.result(fixed_monthly=100,fixed_avoidable=1,migration=1,destination_capacity_daily=1,exit_cost=75)
        # Source daily GP=20; destination GP/order=20/3; capacity=30.
        self.assertAlmostEqual(self.delta(r,'Permanent closure'),100-600+200-75)
        self.assertAlmostEqual(r['diagnostics']['closure_capacity_fraction'],1/3)
        r2=self.result(fixed_monthly=100,fixed_avoidable=1,migration=1,destination_capacity_daily=1,exit_cost=100)
        self.assertAlmostEqual(self.delta(r2,'Permanent closure')-self.delta(r,'Permanent closure'),-25)
    def test_same_branch_cannot_migrate(self):
        r=self.result(destination='One',migration=1,destination_capacity_daily=1000)
        self.assertAlmostEqual(self.delta(r,'Permanent closure'),-600)
    def test_migration_displacement(self):
        a=self.result(migration=1,destination_capacity_daily=10,destination_displacement=1)
        self.assertAlmostEqual(self.delta(a,'Permanent closure'),-600)
    def test_price_whole_basket_loss_identity(self):
        r=self.result(price_increase=.10,basket_loss=.10)
        # A: 2/day, +2/day, containing GP 16/day. Δ .9*60 - .1*480.
        self.assertAlmostEqual(self.delta(r,'Price increase'),6)
        uplift=r['diagnostics']['price_uplift'];exposure=r['diagnostics']['price_basket_exposure']
        gate=uplift/(uplift+exposure)
        self.assertAlmostEqual(self.delta(self.result(price_increase=.10,basket_loss=gate),'Price increase'),0)
    def test_item_loss_and_substitution(self):
        r=self.result(price_increase=.1,item_loss=.5,substitution_share=1,alternative_margin=2)
        self.assertAlmostEqual(self.delta(r,'Price increase'),30*(1-6+2))
    def test_item_discount_leakage_and_time_window(self):
        # One A/day in 8–9; $1 leakage plus 2 additional units × $5 margin/day.
        r=self.result(start_hour=8,end_hour=9,item_discount=.1,discount_incremental_units_daily=2)
        self.assertAlmostEqual(self.delta(r,'Item discount'),30*(-1+2*5))
    def test_combo_leakage_includes_discount_on_existing_A(self):
        # A-only 1/day; AB 1/day; pair price14.4. Attachment margin14.4−10−2=2.4; leakage1.6/day.
        r=self.result(start_hour=8,end_hour=21,combo_discount=.1,combo_conversion=.5)
        self.assertAlmostEqual(r['diagnostics']['combo_leakage'],48)
        self.assertAlmostEqual(r['diagnostics']['combo_incremental_margin'],2.4)
        self.assertAlmostEqual(self.delta(r,'Two-item combo'),30*(.5*2.4-1.6))
    def test_expiry_sunk_cost_and_break_even(self):
        r=self.result(expiry_units_daily=3,expiry_base_sell=.2,expiry_offer_sell=.5,expiry_discount=.2)
        self.assertAlmostEqual(self.delta(r,'Expiry markdown'),90*(.5*8-.2*10))
        # Change acquisition costs while keeping accounting consistent; sunk stock decision unchanged.
        modified=self.raw.copy();modified['Unit Cost (USD)']*=1.5
        modified['Line Gross Profit (USD)']=modified['Line Revenue (USD)']-modified['Quantity']*modified['Unit Cost (USD)']
        p=r['parameters'];r2=E.evaluate(load(modified),p)
        self.assertAlmostEqual(self.delta(r,'Expiry markdown'),self.delta(r2,'Expiry markdown'))
        gate=.2*10/8
        self.assertAlmostEqual(self.delta(self.result(expiry_units_daily=3,expiry_base_sell=.2,expiry_offer_sell=gate,expiry_discount=.2),'Expiry markdown'),0)
    def test_loyalty_organic_rewards_leak(self):
        r=self.result(loyalty_reach=1,loyalty_extra_visits=0,loyalty_base_visits=2,loyalty_reward=1)
        self.assertAlmostEqual(self.delta(r,'Loyalty'),-4)
    def test_delivery_channel_switch_and_costs(self):
        # Full-day mix: revenue32/3; cost4; GP20/3. No discount/commission = old GP.
        r=self.result(start_hour=8,end_hour=21,delivery_orders_daily=2,delivery_incremental=0,
          delivery_discount=0,delivery_commission=0,delivery_displaced_gp=20/3)
        self.assertAlmostEqual(self.delta(r,'Delivery offer'),0)
        r2=self.result(start_hour=8,end_hour=21,delivery_orders_daily=2,delivery_incremental=1,
          delivery_discount=0,delivery_commission=0,delivery_displaced_gp=20/3,delivery_packaging=1)
        self.assertAlmostEqual(self.delta(r2,'Delivery offer'),60*(20/3-1))
    def test_inventory_constraints_and_determinism(self):
        r=self.result(on_hand=100,current_order=0)
        self.assertEqual(r['restock']['order'],0)
        self.assertEqual(self.delta(r,'Restock / preparation'),0)
        a=self.result();b=self.result()
        self.assertEqual(a['restock']['target'],b['restock']['target'])
        self.assertEqual(a['restock']['delta'],b['restock']['delta'])
    def test_forecast_time_isolation(self):
        s=E.daily_series(self.x[self.x.branch.eq('One')],'A')
        first,_,_=E.forecast_backtest(s)
        changed=s.copy();changed.iloc[-7:]=999
        second,_,_=E.forecast_backtest(changed)
        left=first[first.date<=s.index[-7]].prediction.to_numpy()
        right=second[second.date<=s.index[-7]].prediction.to_numpy()
        np.testing.assert_allclose(left,right)
        # Validation winner cannot depend on final-test actuals.
        self.assertEqual(E.forecast_backtest(s)[2],E.forecast_backtest(changed)[2])
    def test_branch_calendar_zero_fills_absent_endpoint_days(self):
        subset=self.x[~(self.x.branch.eq('One') & self.x.date.eq(self.x.date.max()))].copy()
        t,days=E.scope(subset,'One',56)
        series=E.daily_series(t,'A')
        self.assertEqual(len(series),days)
        self.assertEqual(series.iloc[-1],0)
    def test_short_series_no_fake_holdout(self):
        s=E.daily_series(self.x,'A').iloc[:20]
        _,scores,model=E.forecast_backtest(s)
        self.assertTrue(scores.empty);self.assertEqual(model,'mean28')
    def test_loyalty_right_censor_and_anonymous(self):
        result=E.loyalty_evidence(self.x)
        self.assertEqual(result['mature_customers'],2)
        self.assertEqual(result['recognized_return30'],1)
        result=E.loyalty_evidence(self.x[self.x.date>self.x.date.max()-pd.Timedelta(days=14)])
        self.assertEqual(result['mature_customers'],0)
        self.assertTrue(np.isnan(result['recognized_return30']))
    def test_pair_training_selection_not_holdout_rank(self):
        pairs=E.pair_evidence(self.x)
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs.iloc[0].product_a,'A')
        self.assertGreater(pairs.iloc[0].holdout_pair_baskets,0)
    def test_report_has_no_identifiers(self):
        r=self.result();report=E.aggregate_report(r,{'rows_used':len(self.x)})
        self.assertNotIn('PRIVATE-C',report);self.assertNotIn('PRIVATE-T',report)
        self.assertIn('assumptions',report.lower())
    def test_invalid_controls_fail(self):
        for update in [{'basket_loss':1.1},{'new_open':23,'new_close':8},{'combo_discount':-1},{'product':'A','second':'A'},{'horizon':0}]:
            with self.assertRaises(ValueError):self.result(**update)
    def test_notebook_self_contained_and_output_free(self):
        root=Path(__file__).resolve().parents[1]
        nb=json.loads((root/'Stories_Coffee_Decision_Lab.ipynb').read_text())
        sources=[''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code']
        self.assertIn((root/'engine.py').read_text(),sources)
        for c in nb['cells']:
            if c['cell_type']=='code':
                self.assertEqual(c['outputs'],[]);self.assertIsNone(c['execution_count'])
        allsource=''.join(sources)
        self.assertNotIn('stories_transactions.csv\",',allsource)


if __name__=='__main__':unittest.main()
