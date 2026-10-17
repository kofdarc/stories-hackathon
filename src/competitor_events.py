"""Day-level competitor and market-shock features from sourced event lists.

Inputs (one row per event, each with a source URL):
  data/external/competitor_events_2026.csv  competitor openings, launches, offers
  data/external/market_events_2026.csv      2026 Lebanon war and ceasefire dates

All events are market-wide: branch locations are not in the transaction file, so no
event can be tied to a specific branch.

Run directly to print the features' association with daily baskets:
  python3 src/competitor_events.py
"""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / 'data' / 'external'
NEW_COMPETITOR = ['store_opening', 'product_launch']


def load_events(folder=EXTERNAL):
    comp = pd.read_csv(folder/'competitor_events_2026.csv', parse_dates=['start_date', 'end_date'])
    market = pd.read_csv(folder/'market_events_2026.csv', parse_dates=['start_date', 'end_date'])
    return comp, market


def _active(dates, events):
    return np.any([dates.between(s, e) for s, e in zip(events.start_date, events.end_date)], axis=0) \
        if len(events) else np.zeros(len(dates), bool)


def _days_since(dates, starts):
    """Days since the latest start on or before each date (NaN before the first)."""
    starts = np.sort(starts.values)
    idx = np.searchsorted(starts, dates.values, side='right') - 1
    out = (dates.values - starts[np.clip(idx, 0, None)]).astype('timedelta64[D]').astype(float)
    return np.where(idx >= 0, out, np.nan)


def event_features(dates, folder=EXTERNAL):
    """One row per date with competitor and market-shock flags."""
    comp, market = load_events(folder)
    d = pd.DataFrame({'date': pd.to_datetime(pd.Series(dates)).drop_duplicates().sort_values().reset_index(drop=True)})
    new = comp[comp.event_type.isin(NEW_COMPETITOR)]
    since_new = _days_since(d.date, new.start_date)
    d['competitor_new_entry_7d'] = since_new <= 6
    d['days_since_competitor_entry'] = since_new
    d['competitor_seasonal_offer'] = _active(d.date, comp[comp.event_type.eq('seasonal_offer')])
    d['competitor_events_active'] = sum(d.date.between(s, e + pd.Timedelta(days=6) if t in NEW_COMPETITOR else e)
                                        for s, e, t in zip(comp.start_date, comp.end_date, comp.event_type))
    war = market[market.event_type.eq('conflict')].iloc[0]
    d['war_active'] = d.date.between(war.start_date, war.end_date)
    d['days_since_war_start'] = np.where(d.war_active, (d.date - war.start_date).dt.days, np.nan)
    shocks = market[market.event_type.eq('conflict') & market.start_date.eq(market.end_date)]
    d['conflict_shock_day'] = d.date.isin(shocks.start_date)
    d['conflict_shock_week'] = _days_since(d.date, shocks.start_date) <= 6
    ceasefire = market[market.event_type.eq('ceasefire')].start_date.min()
    d['ceasefire_announced'] = d.date >= ceasefire
    return d


FLAGS = ['competitor_new_entry_7d', 'competitor_seasonal_offer', 'war_active',
         'conflict_shock_week', 'ceasefire_announced']


def daily_baskets(db=ROOT/'database'/'stories.sqlite'):
    with sqlite3.connect(db) as con:
        return pd.read_sql('SELECT order_date AS date, branch, COUNT(*) AS baskets FROM orders '
                           'GROUP BY order_date, branch', con, parse_dates=['date'])


def effects(panel, flags=FLAGS):
    """Log-baskets on branch x weekday + branch trend + each flag alone; week-clustered 95% CI.

    Flags that are on for a whole contiguous block (war_active, ceasefire_announced) are
    collinear with the trend and season, so read them as level shifts at best.
    """
    p = panel.copy()
    p['t'] = (p.date - p.date.min()).dt.days / 30.4
    base = pd.get_dummies(p.branch + '_' + p.date.dt.dayofweek.astype(str), dtype=float)
    base = pd.concat([base, pd.get_dummies(p.branch, dtype=float).mul(p.t, axis=0).add_prefix('trend_')], axis=1)
    y = np.log(p.baskets.to_numpy())
    week = p.date.dt.isocalendar().week.to_numpy()
    rows = []
    for f in flags:
        X = np.column_stack([base.to_numpy(), p[f].astype(float).to_numpy()])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        bread = np.linalg.pinv(X.T @ X)
        meat = sum(np.outer(g, g) for g in (X[week == w].T @ resid[week == w] for w in np.unique(week)))
        se = np.sqrt((bread @ meat @ bread)[-1, -1])
        b = beta[-1]
        rows.append(dict(feature=f, effect=np.expm1(b), ci_low=np.expm1(b - 1.96*se),
                         ci_high=np.expm1(b + 1.96*se), days=int(p.groupby('date')[f].first().sum())))
    return pd.DataFrame(rows)


def monthly_index(panel):
    m = panel.groupby(panel.date.dt.to_period('M')).agg(baskets=('baskets', 'sum'), days=('date', 'nunique'))
    m['baskets_per_day'] = m.baskets / m.days
    m['vs_prior_month'] = m.baskets_per_day.pct_change()
    return m


if __name__ == '__main__':
    panel = daily_baskets()
    panel = panel.merge(event_features(panel.date), on='date', validate='many_to_one')
    pd.set_option('display.width', 120)
    print(effects(panel).to_string(index=False, float_format=lambda v: f'{v:+.3f}'))
    print()
    print(monthly_index(panel).to_string(float_format=lambda v: f'{v:.3f}'))
