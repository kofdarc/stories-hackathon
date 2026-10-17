"""Daily sales forecasting by branch: candidate models, rolling-origin backtest and forward forecast.

Every model predicts one target (revenue, baskets or gp) per date × branch from information
available at the forecast origin only. Features are deterministic calendar terms (branch,
weekday, day of month, trend), so a forecast of any horizon needs no future actuals. Earlier work
(`reports/external_factors.md`) found weather and holidays add no accuracy, so they are excluded.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor

TARGETS = ['revenue', 'baskets', 'gp']
EPOCH = pd.Timestamp('2026-01-01')

def daily_sales(x):
    """Complete date × branch panel of revenue, baskets and gp (absent days filled with zero)."""
    d = x.groupby(['date', 'branch'], observed=True).agg(revenue=('revenue', 'sum'),
        baskets=('transaction', 'nunique'), gp=('gp', 'sum'))
    grid = pd.MultiIndex.from_product([pd.date_range(x.date.min(), x.date.max()), sorted(x.branch.unique())],
                                      names=['date', 'branch'])
    return d.reindex(grid, fill_value=0).reset_index()

def _features(d, branches):
    """Design matrix: branch and weekday dummies, branch × weekday, branch trends, month-start."""
    b = pd.Categorical(d.branch, categories=branches)
    wd = d.date.dt.dayofweek
    X = pd.DataFrame(index=d.index)
    t = (d.date-EPOCH).dt.days/30.4
    for br in branches:
        on = (b == br).astype(float)
        X[f'b_{br}'] = on
        X[f'trend_{br}'] = on*t
        for w in range(7):
            X[f'bw_{br}_{w}'] = on*(wd == w)
    X['month_start'] = (d.date.dt.day <= 6).astype(float)
    return X

class SeasonalNaive:
    """Mean of the last four same-weekday values per branch (the standard retail benchmark)."""
    name = 'Seasonal naive (last 4 weeks)'
    def fit(self, train, target):
        last = train[train.date > train.date.max()-pd.Timedelta(days=28)]
        self.level = last.assign(wd=last.date.dt.dayofweek).groupby(['branch', 'wd'])[target].mean()
        return self
    def predict(self, future):
        idx = pd.MultiIndex.from_arrays([future.branch, future.date.dt.dayofweek])
        return self.level.reindex(idx).to_numpy()

class ClockTemplate:
    """Log-linear OLS on branch × weekday + branch trend (the template used elsewhere in the repo)."""
    name = 'Clock template (log-linear)'
    def fit(self, train, target):
        self.branches = sorted(train.branch.unique())
        X = _features(train, self.branches).to_numpy()
        y = np.log(np.maximum(train[target].to_numpy(float), 1.))
        self.beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        self.smear = np.mean(np.exp(y-X@self.beta))  # Duan smearing: unbiased back-transform
        return self
    def predict(self, future):
        return np.exp(_features(future, self.branches).to_numpy()@self.beta)*self.smear

class PoissonGLM:
    """Regularized Poisson regression (log link) on the same calendar features; fits counts and sums directly."""
    name = 'Poisson GLM (regularized)'
    def __init__(self, alpha=1e-3): self.alpha = alpha
    def fit(self, train, target):
        self.branches = sorted(train.branch.unique())
        self.scale = max(train[target].mean(), 1e-9)  # keeps the solver well conditioned for dollar targets
        self.m = PoissonRegressor(alpha=self.alpha, max_iter=3000)
        self.m.fit(_features(train, self.branches), np.maximum(train[target].to_numpy(float), 0)/self.scale)
        return self
    def predict(self, future):
        return self.m.predict(_features(future, self.branches))*self.scale

class BoostedHybrid:
    """Clock template for level and trend, plus gradient boosting on the remaining log residual.

    Trees cannot extrapolate a trend, so they model only the shape the template misses
    (day of month, weekday × branch interactions); the template carries growth forward.
    """
    name = 'Gradient-boosted hybrid'
    def __init__(self, seed=0): self.seed = seed
    def _X(self, d):
        return np.column_stack([pd.Categorical(d.branch, categories=self.branches).codes,
                                d.date.dt.dayofweek, d.date.dt.day])
    def fit(self, train, target):
        self.base = ClockTemplate().fit(train, target); self.branches = self.base.branches
        resid = np.log(np.maximum(train[target].to_numpy(float), 1.))-np.log(self.base.predict(train))
        self.gbm = HistGradientBoostingRegressor(max_iter=150, learning_rate=.05, max_depth=3, min_samples_leaf=20,
                                                 l2_regularization=1., categorical_features=[0], random_state=self.seed)
        self.gbm.fit(self._X(train), resid)
        return self
    def predict(self, future):
        return self.base.predict(future)*np.exp(self.gbm.predict(self._X(future)))

class LinearTrend:
    """Additive straight-line growth per branch × multiplicative weekday and month-start factors.

    Weekday shape comes from the clock template; a least-squares line per branch is then fitted to
    weekday-adjusted values, so growth adds a constant amount per month instead of compounding
    as the log-link models do.
    """
    name = 'Linear trend × weekday'
    def fit(self, train, target):
        self.branches = sorted(train.branch.unique()); y = train[target].to_numpy(float)
        self.base = ClockTemplate().fit(train, target)
        self.season = self._season(train)  # weekday/month-start shape from the log model, trend removed
        adj = y/self.season
        t = (train.date-EPOCH).dt.days.to_numpy()/30.4
        self.coef = {}
        for br in self.branches:
            m = (train.branch == br).to_numpy()
            self.coef[br] = np.polyfit(t[m], adj[m], 1)
        return self
    def _season(self, d):
        X = _features(d, self.branches)
        keep = [c for c in X if c.startswith('bw_') or c == 'month_start']
        beta = pd.Series(self.base.beta, index=X.columns)
        s = np.exp(X[keep].to_numpy()@beta[keep].to_numpy())
        # Normalize per branch so the weekday factors average to 1 across a week.
        ref = pd.DataFrame({'date': pd.date_range(EPOCH, periods=7).repeat(len(self.branches)),
                            'branch': self.branches*7})
        R = _features(ref, self.branches)
        norm = pd.Series(np.exp(R[keep].to_numpy()@beta[keep].to_numpy())).groupby(ref.branch.to_numpy()).mean()
        return s/d.branch.map(norm).to_numpy()
    def predict(self, future):
        t = (future.date-EPOCH).dt.days.to_numpy()/30.4
        level = np.array([np.polyval(self.coef[b], ti) for b, ti in zip(future.branch, t)])
        return np.maximum(level, 0)*self._season(future)

class Ensemble:
    """Equal-weight average of the three model-based forecasts."""
    name = 'Ensemble (mean of models)'
    def fit(self, train, target):
        self.parts = [m().fit(train, target) for m in (LinearTrend, PoissonGLM, BoostedHybrid)]
        return self
    def predict(self, future):
        return np.mean([m.predict(future) for m in self.parts], axis=0)

MODELS = [SeasonalNaive, ClockTemplate, LinearTrend, PoissonGLM, BoostedHybrid, Ensemble]

def origins(d, horizon=28, step=14, first='2026-03-01'):
    """Forecast origins every `step` days whose full horizon lies inside the data."""
    last = d.date.max()-pd.Timedelta(days=horizon-1)
    return list(pd.date_range(first, last, freq=f'{step}D'))

def backtest(d, targets=TARGETS, horizon=28, step=14, models=MODELS):
    """Rolling-origin evaluation: train on everything before each origin, forecast the next `horizon` days.

    Returns one row per origin × date × branch × target × model with the prediction and actual.
    """
    rows = []
    for origin in origins(d, horizon, step):
        train = d[d.date < origin]
        test = d[(d.date >= origin) & (d.date < origin+pd.Timedelta(days=horizon))]
        for target in targets:
            for M in models:
                pred = M().fit(train, target).predict(test)
                rows.append(test[['date', 'branch']].assign(origin=origin, target=target, model=M.name,
                    days_ahead=(test.date-origin).dt.days+1, actual=test[target].to_numpy(), pred=pred))
    return pd.concat(rows, ignore_index=True)

def scores(bt):
    """Accuracy per target × model at branch-day and branch-week grain.

    WAPE = sum |error| / sum actual (robust to small days); bias is mean (pred-actual)/actual.
    Weekly grain is what staffing and ordering decisions consume.
    """
    def agg(g):
        e = g.pred-g.actual
        return pd.Series(dict(mae=e.abs().mean(), wape=e.abs().sum()/g.actual.sum(), bias=e.sum()/g.actual.sum()))
    day = bt.groupby(['target', 'model']).apply(agg, include_groups=False)
    wk = (bt.assign(week=(bt.days_ahead-1)//7).groupby(['target', 'model', 'origin', 'branch', 'week'])[['actual', 'pred']]
          .sum().reset_index().groupby(['target', 'model']).apply(lambda g: (g.pred-g.actual).abs().sum()/g.actual.sum(),
                                                                 include_groups=False).rename('weekly_wape'))
    out = day.join(wk).reset_index()
    naive = out[out.model == SeasonalNaive.name].set_index('target').wape
    out['skill_vs_naive'] = 1-out.wape/out.target.map(naive)
    return out.sort_values(['target', 'wape']).reset_index(drop=True)

def interval_factors(bt, model, levels=(.1, .9), grain='day'):
    """Empirical multiplicative interval: quantiles of actual/pred in the backtest, per target.

    grain='day' uses branch-days; grain='week' uses chain-wide weekly totals, which is the right
    scale for monthly totals because daily noise cancels but trend errors do not.
    """
    b = bt[bt.model == model]
    if grain == 'week':
        b = b.assign(week=(b.days_ahead-1)//7).groupby(['target', 'origin', 'week'])[['actual', 'pred']].sum().reset_index()
    b = b[b.pred > 0]
    return b.assign(r=b.actual/b.pred).groupby('target').r.quantile(list(levels)).unstack()

def best_models(bt):
    """Lowest daily WAPE model per target."""
    names = {M.name: M for M in MODELS}
    return {t: names[g.iloc[0].model] for t, g in scores(bt).groupby('target')}

def forecast(d, bt, start=None, days=62, targets=TARGETS):
    """Fit each target's best backtest model on all history and forecast `days` days per branch.

    `low`/`high` give an 80% interval calibrated on that model's backtest errors.
    """
    start = pd.Timestamp(start) if start else d.date.max()+pd.Timedelta(days=1)
    future = pd.DataFrame([(dt, b) for dt in pd.date_range(start, periods=days) for b in sorted(d.branch.unique())],
                          columns=['date', 'branch'])
    best = best_models(bt); rows = []
    for target in targets:
        M = best[target]; q = interval_factors(bt, M.name).loc[target]
        pred = M().fit(d, target).predict(future)
        rows.append(future.assign(target=target, model=M.name, forecast=pred, low=pred*q[.1], high=pred*q[.9]))
    return pd.concat(rows, ignore_index=True)

def monthly(d, f, bt):
    """Actual and forecast chain-wide totals by month × target, with month-on-month growth per day.

    Forecast months get an 80% band from chain-wide weekly backtest errors of the chosen model.
    """
    hist = d.melt(id_vars=['date', 'branch'], value_vars=list(f.target.unique()), var_name='target', value_name='value')
    both = pd.concat([hist.assign(kind='actual'), f.rename(columns={'forecast': 'value'})[hist.columns].assign(kind='forecast')])
    out = (both.assign(month=both.date.dt.strftime('%Y-%m')).groupby(['target', 'month', 'kind'])
           .agg(value=('value', 'sum'), days=('date', 'nunique')).reset_index())
    model = f.groupby('target').model.first()
    q = pd.DataFrame({t: interval_factors(bt, m, grain='week').loc[t] for t, m in model.items()}).T
    fc = out.kind == 'forecast'
    out['low'] = np.where(fc, out.value*out.target.map(q[.1]), np.nan)
    out['high'] = np.where(fc, out.value*out.target.map(q[.9]), np.nan)
    out['per_day'] = out.value/out.days
    out['growth_per_day'] = out.groupby('target').per_day.pct_change()
    return out

def weekly(d, f, bt, target='revenue'):
    """Chain-wide revenue (or other target) per day by Monday–Sunday week, full weeks only.

    Forecast weeks carry an 80% band from the chosen model's chain-wide weekly backtest errors.
    """
    hist = d.groupby('date')[target].sum().rename('value').reset_index().assign(kind='actual')
    g = f[f.target == target]
    fut = g.groupby('date').forecast.sum().rename('value').reset_index().assign(kind='forecast')
    both = pd.concat([hist, fut])
    w = (both.assign(week=both.date.dt.to_period('W-SUN').dt.start_time).groupby(['week', 'kind'])
         .agg(per_day=('value', 'mean'), days=('date', 'nunique')).reset_index())
    w = w[w.days == 7].drop(columns='days').reset_index(drop=True)
    q = interval_factors(bt, g.model.iloc[0], grain='week').loc[target]
    fc = w.kind == 'forecast'
    w['low'] = np.where(fc, w.per_day*q[.1], np.nan); w['high'] = np.where(fc, w.per_day*q[.9], np.nan)
    return w
