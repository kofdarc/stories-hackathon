"""External weather/calendar joins and context-model checks."""
import unittest
import pandas as pd
from src.analytics import load_data
from src.features import enrich,daily_panel,weather_effects,forecast_check,calendar,month_turn_placebo

class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=load_data(); cls.e=enrich(cls.x); cls.p=daily_panel(cls.e)

    def test_join_keeps_grain_and_totals(self):
        self.assertEqual(len(self.e),len(self.x))
        self.assertAlmostEqual(self.e.revenue.sum(),self.x.revenue.sum(),places=7)
        self.assertFalse(self.e[['temp_mean','hour_temp','rain_mm','holiday','ramadan']].isna().any().any())

    def test_calendar_flags(self):
        c=calendar(pd.to_datetime(['2026-01-01','2026-01-15','2026-03-01','2026-04-02','2026-04-30'])).set_index('date')
        self.assertTrue(c.loc['2026-01-01','holiday']);self.assertFalse(c.loc['2026-01-15','holiday'])
        self.assertTrue(c.loc['2026-03-01','ramadan']);self.assertTrue(c.loc['2026-04-02','holiday_eve'])
        self.assertTrue(c.loc['2026-04-30','payday_window']);self.assertFalse(c.loc['2026-01-15','payday_window'])

    def test_panel_matches_baskets(self):
        self.assertEqual(self.p.baskets.sum(),self.x.groupby(['date','branch']).transaction.nunique().sum())
        self.assertEqual(len(self.p),self.x.groupby(['date','branch']).ngroups)

    def test_effects_recover_planted_signal(self):
        # Plant +20% on rainy days; the estimator must find it inside its CI.
        p=self.p.copy(); p['baskets']=(p.baskets*p.rainy.map({True:1.2,False:1.0})).round()
        r=weather_effects(p).set_index('feature').loc['rainy']
        self.assertLess(r.ci_low,.2);self.assertGreater(r.ci_high,.2)
        self.assertLess(r.ci_low,r.effect);self.assertLess(r.effect,r.ci_high)

    def test_holdout_and_placebo_shapes(self):
        f=forecast_check(self.p); self.assertEqual(len(f),2);self.assertEqual(f.test_days.iloc[0],61)
        self.assertEqual(month_turn_placebo(self.p).is_payday_window.sum(),1)



class ExpandedFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.x=load_data(); cls.e=enrich(cls.x)

    def test_customer_history_uses_only_past_visits(self):
        o=self.e.drop_duplicates('transaction').dropna(subset=['customer']).sort_values('datetime')
        first=o.groupby('customer').head(1)
        self.assertTrue(first.customer_visit_number.eq(1).all())
        self.assertTrue(first.days_since_prev_visit.isna().all())
        self.assertTrue(o.days_since_prev_visit.dropna().ge(0).all())
        anon=self.e[self.e.customer.isna()]
        self.assertTrue(anon.customer_visit_number.isna().all());self.assertFalse(anon.customer_identified.any())

    def test_basket_and_load_features(self):
        o=self.x.groupby('transaction').agg(lines=('product','size'),revenue=('revenue','sum'))
        b=self.e.drop_duplicates('transaction').set_index('transaction')
        self.assertTrue((b.basket_lines==o.lines.reindex(b.index)).all())
        self.assertTrue(((b.basket_revenue-o.revenue.reindex(b.index)).abs()<1e-9).all())
        self.assertTrue((b.groupby(['branch','date']).branch_day_baskets.first()==b.groupby(['branch','date']).size()).all())

    def test_calendar_extras(self):
        c=calendar(pd.date_range('2026-01-01','2026-04-06')).set_index('date')
        self.assertTrue(c.loc['2026-01-02','bridge_day'])   # Friday between New Year and the weekend
        self.assertFalse(c.loc['2026-01-03','long_weekend'])  # plain weekend after a working bridge day
        self.assertTrue(c.loc['2026-04-03':'2026-04-05','long_weekend'].all())  # Good Friday + Easter
        self.assertEqual(c.loc['2026-01-05','days_since_last_holiday'],4)
        self.assertEqual(c.loc['2026-01-05','days_to_next_holiday'],1)

    def test_no_feature_gaps_where_unexpected(self):
        allowed={'holiday_name','commercial_event','customer','customer_visit_number','days_since_prev_visit',
                 'customer_new_branch','temp_change_vs_yesterday','rain_yesterday_mm','days_to_next_holiday'}
        gaps=set(self.e.columns[self.e.isna().any()])
        self.assertLessEqual(gaps,allowed)

class ClockTemplateTests(unittest.TestCase):
    def test_dispersion_separates_poisson_from_overdispersed(self):
        import numpy as np
        from src.features import dispersion
        rng=np.random.default_rng(1); mu=rng.uniform(1,20,20000)
        self.assertAlmostEqual(dispersion(rng.poisson(mu),mu),1,delta=.05)
        over=rng.poisson(mu*rng.gamma(2,.5,len(mu)))  # weather-like multiplicative shocks
        self.assertGreater(dispersion(over,mu),1.5)

    def test_template_recovers_planted_weather_effect(self):
        # Plant +30% demand when raining: the weather model must then beat the clock-only template.
        import numpy as np
        from src.features import branch_hour_panel,clock_template_check
        x=load_data(); g=branch_hour_panel(x)
        rng=np.random.default_rng(2); g['baskets']=rng.poisson(g.baskets.clip(lower=.5)*np.where(g.raining_now,1.3,1.))
        c=clock_template_check(g).set_index('model').holdout_mae
        self.assertLess(c.iloc[1],c.iloc[0])

    def test_panel_includes_zero_hours_and_matches_baskets(self):
        from src.features import branch_hour_panel
        x=load_data(); g=branch_hour_panel(x)
        self.assertEqual(len(g),181*3*17); self.assertEqual(g.baskets.sum(),x.transaction.nunique())

if __name__=='__main__': unittest.main()
