"""Sales forecasting: backtest candidate models, forecast July–August 2026, write tables, figure and report."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.analytics import ROOT, load_data
from src.forecasting import daily_sales, backtest, scores, forecast, monthly, weekly, interval_factors, SeasonalNaive

def main():
    reports = ROOT/'reports'; tables = reports/'tables'; figures = reports/'figures'
    d = daily_sales(load_data())
    bt = backtest(d); s = scores(bt); f = forecast(d, bt); m = monthly(d, f, bt)
    by_week = (bt.assign(week=(bt.days_ahead-1)//7+1).groupby(['target', 'model', 'week'])
               .apply(lambda g: (g.pred-g.actual).abs().sum()/g.actual.sum(), include_groups=False)
               .rename('wape').reset_index())
    branch = (f.assign(month=f.date.dt.strftime('%Y-%m')).groupby(['target', 'branch', 'month'])
              [['forecast', 'low', 'high']].sum().reset_index())
    chosen = f.groupby('target').model.first()
    intervals = pd.concat([interval_factors(bt, mdl, grain=g).loc[[t]].assign(model=mdl, grain=g)
                           for t, mdl in chosen.items() for g in ('day', 'week')]).rename(columns={.1: 'q10', .9: 'q90'})
    for name, t in dict(forecast_intervals=intervals.reset_index(), forecast_scores=s, forecast_horizon=by_week, forecast_daily=f,
                        forecast_monthly=m, forecast_branch_monthly=branch).items():
        t.to_csv(tables/f'{name}.csv', index=False)

    # Figure: chain revenue per day by full week, with the weekly-calibrated 80% band.
    fig, ax = plt.subplots(figsize=(10, 4.2))
    w = weekly(d, f, bt); h, fw = w[w.kind == 'actual'], w[w.kind == 'forecast']
    ax.plot(h.week, h.per_day, color='#75543d', lw=2, label='Actual')
    ax.plot(fw.week, fw.per_day, color='#547965', lw=2, ls='--', label='Forecast')
    ax.fill_between(fw.week, fw.low, fw.high, color='#547965', alpha=.18, label='80% interval')
    ax.set_ylabel('Revenue per day, weekly average (USD)'); ax.set_ylim(bottom=0); ax.set_title('Stories chain revenue: actual Jan–Jun, forecast Jul–Aug 2026')
    ax.spines[['top', 'right']].set_visible(False); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(figures/'forecast.png', dpi=150); plt.close(fig)

    (reports/'forecasting.md').write_text(report(s, m, branch, by_week, f))
    print(s.round(3).to_string(index=False)); print(m.round(1).to_string(index=False))

def report(s, m, branch, by_week, f):
    rev = m[m.target == 'revenue'].set_index('month'); gp = m[m.target == 'gp'].set_index('month')
    bk = m[m.target == 'baskets'].set_index('month')
    best = s.groupby('target').first(); naive = s[s.model == SeasonalNaive.name].set_index('target')
    model = f.groupby('target').model.first()
    br = branch[branch.target == 'revenue'].pivot(index='branch', columns='month', values='forecast')
    june = m[(m.target == 'revenue')].set_index('month').loc['2026-06', 'per_day']
    w = by_week[(by_week.target == 'revenue') & (by_week.model == model['revenue'])].set_index('week').wape
    rb = s[s.target == 'revenue'].set_index('model').bias
    clock_bias, glm_bias, lin_bias = rb['Clock template (log-linear)'], rb['Poisson GLM (regularized)'], rb['Linear trend × weekday']
    table = '\n'.join(f'| {r.target} | {r.model} | {r.wape:.1%} | {r.weekly_wape:.1%} | {r.bias:+.1%} | {r.skill_vs_naive:+.1%} |'
                      for r in s.itertuples())
    months = '\n'.join(f'| {mo} | ${rev.loc[mo, "value"]:,.0f} (${rev.loc[mo, "low"]:,.0f}–${rev.loc[mo, "high"]:,.0f}) | '
                       f'${gp.loc[mo, "value"]:,.0f} | {bk.loc[mo, "value"]:,.0f} | {rev.loc[mo, "growth_per_day"]:+.1%} |'
                       for mo in rev.index[rev.kind == 'forecast'])
    branches = '\n'.join(f'| {b} | ' + ' | '.join(f'${v:,.0f}' for v in r) + ' |' for b, r in br.iterrows())
    return f"""# Sales forecast: July–August 2026

**Stories should plan for about ${rev.loc['2026-07', 'value']:,.0f} revenue in July and ${rev.loc['2026-08', 'value']:,.0f} in August if the January–June growth path continues.** That is ${rev.loc['2026-07', 'per_day']:,.0f} and ${rev.loc['2026-08', 'per_day']:,.0f} a day, against ${june:,.0f} a day in June. Gross profit follows at about ${gp.loc['2026-07', 'value']:,.0f} and ${gp.loc['2026-08', 'value']:,.0f}. The forecast is a continuation of the observed trend, not a prediction that the trend will hold: six months of history cannot detect seasonality, saturation or a summer slowdown.

## Forecast

| Month | Revenue (80% band) | Gross profit | Baskets | Growth per day vs prior month |
|---|---|---|---|---|
{months}

By branch (revenue):

| Branch | {' | '.join(br.columns)} |
|---|{'---|'*len(br.columns)}
{branches}

Daily branch forecasts with 80% intervals are in `tables/forecast_daily.csv`; monthly totals in `tables/forecast_monthly.csv` and `tables/forecast_branch_monthly.csv`. The chart of revenue per day (weekly average) is `figures/forecast.png`.

![Revenue forecast](figures/forecast.png)

## Which model, and how well it works

Six models were compared with a rolling-origin backtest: seven forecast origins every 14 days from 1 March, each trained only on earlier days and scored on the following 28 days, for every branch and day.

| Target | Model | Daily WAPE | Weekly WAPE | Bias | Skill vs seasonal naive |
|---|---|---|---|---|---|
{table}

- **The machine-learning models beat the standard retail benchmark by {best.skill_vs_naive.min():.0%}–{best.skill_vs_naive.max():.0%} on daily error.** The benchmark (average of the last four same weekdays) lags a growing business: its bias is {naive.loc['revenue', 'bias']:+.1%}. Weekly errors fall to about {best.loc['revenue', 'weekly_wape']:.0%} because day-to-day noise cancels.
- **Simple structure wins; boosting adds nothing.** Every model sees the same branch × weekday × trend information, and gradient boosting on the residual does no better, which matches the earlier finding that this leaves only Poisson arrival noise (`feature_loop.md`). Selected: {', '.join(f'{t}: {n}' for t, n in model.items())}.
- **Growth is additive, not compounding.** The log-link models (clock template, Poisson GLM) over-forecast by {min(clock_bias, glm_bias):+.1%} to {max(clock_bias, glm_bias):+.1%} because a log trend compounds. The linear-trend model, which adds a fixed amount per month, has a bias of {lin_bias:+.1%}. Expect the gap to widen at longer horizons.
- **Error does not grow much across the 28-day horizon** (revenue WAPE {', '.join(f'week {k}: {v:.1%}' for k, v in w.items())}). August lies beyond the tested horizon; treat its band as optimistic.

## How to use it

- **Staffing and ordering:** use the weekly totals with the 80% band. Daily branch numbers carry about ±{(best.loc['baskets', 'wape']):.0%} error, mostly irreducible arrival noise.
- **Budget:** use the low end of the monthly band as the planning case until July actuals confirm the trend.
- **Re-fit monthly:** run `python scripts/forecast.py` after each month closes. If actuals fall below the low band two weeks running, the growth path has broken; stop extrapolating and investigate.

## Limits

- Six months of history: no yearly seasonality can be learned, and summer tourism, Ramadan timing and price changes are not modeled.
- Intervals are calibrated on the same backtest used to pick the model, so true coverage is likely a little below 80%.
- Weather and holiday features were excluded because they made the earlier holdout forecast worse (`external_factors.md`). Transaction IDs begin with `SYN-`; confirm the data reflects real trading before using the forecast for commitments.
"""

if __name__ == '__main__':
    main()
