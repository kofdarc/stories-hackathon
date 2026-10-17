"""Forecasting: panel totals, no look-ahead, planted-trend recovery, backtest skill and output shape."""
import unittest
import numpy as np
import pandas as pd
from src.analytics import load_data
from src.forecasting import (daily_sales, backtest, scores, forecast, monthly, weekly, MODELS,
                             LinearTrend, SeasonalNaive)

class ForecastingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = load_data(); cls.d = daily_sales(cls.x)
        cls.bt = backtest(cls.d); cls.s = scores(cls.bt); cls.f = forecast(cls.d, cls.bt)

    def test_panel_is_complete_and_reconciles(self):
        self.assertEqual(len(self.d), self.d.date.nunique()*self.d.branch.nunique())
        self.assertAlmostEqual(self.d.revenue.sum(), self.x.revenue.sum(), places=6)
        self.assertEqual(self.d.baskets.sum(), self.x.groupby(['date', 'branch']).transaction.nunique().sum())

    def test_no_look_ahead(self):
        # Corrupting every day on or after the origin must not change any model's forecast.
        origin = pd.Timestamp('2026-04-01'); test = self.d[self.d.date >= origin]
        bad = self.d.copy(); bad.loc[bad.date >= origin, 'revenue'] *= 10
        for M in MODELS:
            a = M().fit(self.d[self.d.date < origin], 'revenue').predict(test)
            b = M().fit(bad[bad.date < origin], 'revenue').predict(test)
            np.testing.assert_allclose(a, b, err_msg=M.name)

    def test_linear_trend_recovers_planted_growth(self):
        dates = pd.date_range('2026-01-01', periods=150)
        rng = np.random.default_rng(0); shape = np.array([1, 1.6, 1, 1, 1.1, .7, .8])
        rows = [(dt, b, (base+slope*i/30.4)*shape[dt.dayofweek]) for b, base, slope in [('A', 100, 10), ('B', 50, 3)]
                for i, dt in enumerate(dates)]
        d = pd.DataFrame(rows, columns=['date', 'branch', 'mean'])
        d['revenue'] = rng.poisson(d['mean']).astype(float)
        m = LinearTrend().fit(d, 'revenue')
        self.assertAlmostEqual(m.coef['A'][0], 10, delta=1.5); self.assertAlmostEqual(m.coef['B'][0], 3, delta=1)
        future = pd.DataFrame({'date': pd.date_range('2026-06-01', periods=28).repeat(2), 'branch': ['A', 'B']*28})
        truth = [(100 if b == 'A' else 50)+(10 if b == 'A' else 3)*(dt-dates[0]).days/30.4 for dt, b in zip(future.date, future.branch)]
        truth = np.array(truth)*shape[future.date.dt.dayofweek]
        self.assertLess(np.abs(m.predict(future)/truth-1).mean(), .05)

    def test_models_beat_seasonal_naive(self):
        best = self.s.groupby('target').first()
        self.assertTrue((best.model != SeasonalNaive.name).all())
        self.assertTrue((best.skill_vs_naive > .05).all())
        self.assertTrue((best.bias.abs() < .05).all())

    def test_forecast_shape_and_bands(self):
        self.assertEqual(len(self.f), 62*3*3)
        self.assertEqual(self.f.date.min(), pd.Timestamp('2026-07-01'))
        self.assertTrue((self.f.forecast > 0).all())
        self.assertTrue(((self.f.low <= self.f.forecast) & (self.f.forecast <= self.f.high)).all())
        m = monthly(self.d, self.f, self.bt)
        self.assertEqual(set(m[m.kind == 'forecast'].month), {'2026-07', '2026-08'})
        act = m[(m.kind == 'actual') & (m.target == 'revenue')].value.sum()
        self.assertAlmostEqual(act, self.x.revenue.sum(), places=4)
        w = weekly(self.d, self.f, self.bt)
        self.assertTrue(w.week.dt.dayofweek.eq(0).all())

if __name__ == '__main__':
    unittest.main()
