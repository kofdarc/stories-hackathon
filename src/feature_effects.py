"""Every engineered feature, every outcome, raw vs controlled effect, with a verdict.

Shared by the dashboard's Feature Explorer, the notebook and run_analysis.py.

Effect = within-stratum OLS slope × a contrast (on vs off for flags, P10→P90 for
numbers), with day-clustered standard errors. "Raw" uses no strata; "controlled"
removes branch, season and clock (strata per feature group below). Demand
outcomes are modelled in logs and reported as % changes. Associations only.
"""
import numpy as np
import pandas as pd
from scipy import stats
from src.features import enrich, branch_hour_panel, hourly_context, COLD, HOT

# group, grain (day/hour/basket/customer), description
CATALOG = {
    # Clock (derived from the original timestamp; the features that matter)
    'hour': ('Clock', 'hour', 'Clock hour of the basket'),
    'weekday': ('Clock', 'day', 'Day of week (0 = Monday)'),
    'weekend': ('Clock', 'day', 'Saturday or Sunday'),
    'daypart': ('Clock', 'hour', 'Morning / Lunch / Afternoon / Evening / Late evening'),
    'day_of_month': ('Clock', 'day', 'Day of the month'),
    'week_of_month': ('Clock', 'day', 'Week of the month (1–5)'),
    'month_start': ('Clock', 'day', 'First 6 days of the month'),
    'month_end': ('Clock', 'day', 'Last 6 days of the month'),
    'payday_window': ('Clock', 'day', 'Last 3 + first 3 days of the month (assumed payday)'),
    'dst': ('Clock', 'day', 'Daylight-saving time in force (from 29 Mar)'),
    # Daily weather
    'temp_mean': ('Daily weather', 'day', 'Mean temperature, °C'),
    'temp_max': ('Daily weather', 'day', 'Maximum temperature, °C'),
    'temp_min': ('Daily weather', 'day', 'Minimum temperature, °C'),
    'temp_range': ('Daily weather', 'day', 'Max − min temperature, °C'),
    'feels_like': ('Daily weather', 'day', 'Mean apparent temperature, °C'),
    'temp_anomaly': ('Daily weather', 'day', 'Temperature vs surrounding 15 days, °C'),
    'temp_change_vs_yesterday': ('Daily weather', 'day', 'Change in mean temperature since yesterday, °C'),
    'rain_mm': ('Daily weather', 'day', 'Rain, mm'),
    'rain_hours': ('Daily weather', 'day', 'Hours with rain'),
    'rain_yesterday_mm': ('Daily weather', 'day', "Yesterday's rain, mm"),
    'rain_last_3d_mm': ('Daily weather', 'day', 'Rain over the last 3 days, mm'),
    'dry_streak_days': ('Daily weather', 'day', 'Days since ≥1 mm rain'),
    'rainy': ('Daily weather', 'day', 'Rain ≥1 mm'),
    'heavy_rain': ('Daily weather', 'day', 'Rain ≥10 mm'),
    'hot_day': ('Daily weather', 'day', 'Max temperature ≥30 °C'),
    'windy': ('Daily weather', 'day', 'Max wind ≥40 km/h'),
    'wind_max': ('Daily weather', 'day', 'Max wind, km/h'),
    'sunshine_hours': ('Daily weather', 'day', 'Sunshine hours'),
    'daylight_hours': ('Daily weather', 'day', 'Sunrise-to-sunset hours'),
    'weather': ('Daily weather', 'day', 'WMO weather type'),
    'temp_band': ('Daily weather', 'day', 'Temperature band'),
    # Air quality
    'dust_max': ('Air quality', 'day', 'Daily max dust, µg/m³'),
    'pm10_mean': ('Air quality', 'day', 'Daily mean PM10, µg/m³'),
    'aqi_max': ('Air quality', 'day', 'Daily max US AQI'),
    'uv_max': ('Air quality', 'day', 'Daily max UV index'),
    'dust_event': ('Air quality', 'day', 'Dust ≥50 µg/m³ in some hour'),
    'poor_air': ('Air quality', 'day', 'AQI >100 in some hour'),
    # Weather at the transaction hour
    'hour_temp': ('Hourly weather', 'hour', 'Temperature at that hour, °C'),
    'hour_feels_like': ('Hourly weather', 'hour', 'Apparent temperature at that hour, °C'),
    'hour_rain_mm': ('Hourly weather', 'hour', 'Rain that hour, mm'),
    'raining_now': ('Hourly weather', 'hour', 'Any rain that hour'),
    'hour_humidity': ('Hourly weather', 'hour', 'Relative humidity, %'),
    'hour_dew_point': ('Hourly weather', 'hour', 'Dew point, °C'),
    'hour_cloud_cover': ('Hourly weather', 'hour', 'Cloud cover, %'),
    'hour_wind': ('Hourly weather', 'hour', 'Wind, km/h'),
    'hour_daylight': ('Hourly weather', 'hour', 'Daylight that hour'),
    'hour_weather': ('Hourly weather', 'hour', 'WMO weather type that hour'),
    'hour_pm10': ('Hourly weather', 'hour', 'PM10 that hour, µg/m³'),
    'hour_pm2_5': ('Hourly weather', 'hour', 'PM2.5 that hour, µg/m³'),
    'hour_dust': ('Hourly weather', 'hour', 'Dust that hour, µg/m³'),
    'hour_aqi': ('Hourly weather', 'hour', 'US AQI that hour'),
    'hour_uv': ('Hourly weather', 'hour', 'UV index that hour'),
    'dusty_now': ('Hourly weather', 'hour', 'Dust ≥50 µg/m³ that hour'),
    'after_sunset': ('Hourly weather', 'hour', 'After sunset'),
    'minutes_from_sunset': ('Hourly weather', 'hour', 'Minutes after (+) or before (−) sunset'),
    # Calendar
    'holiday': ('Calendar', 'day', 'Lebanese public holiday'),
    'holiday_eve': ('Calendar', 'day', 'Day before a public holiday'),
    'days_to_next_holiday': ('Calendar', 'day', 'Days until the next public holiday'),
    'days_since_last_holiday': ('Calendar', 'day', 'Days since the last public holiday'),
    'bridge_day': ('Calendar', 'day', 'Workday between two days off'),
    'long_weekend': ('Calendar', 'day', 'Part of ≥3 consecutive days off including a holiday'),
    'school_break': ('Calendar', 'day', 'Estimated school break'),
    'ramadan': ('Calendar', 'day', 'Ramadan (estimated 18 Feb–19 Mar)'),
    'iftar_window': ('Calendar', 'hour', 'After sunset during Ramadan'),
    'commercial_event': ('Calendar', 'day', "Valentine's Day or Mother's Day"),
    'campaign_window': ('Calendar', 'day', '15% promotion window (12–19 Mar, 12–19 May; inferred)'),
    # Basket composition
    'basket_lines': ('Basket', 'basket', 'Item lines in the basket'),
    'basket_units': ('Basket', 'basket', 'Units in the basket'),
    'basket_revenue': ('Basket', 'basket', 'Basket revenue, USD'),
    'basket_categories': ('Basket', 'basket', 'Distinct categories in the basket'),
    'basket_has_food': ('Basket', 'basket', 'Basket contains food'),
    'basket_has_drink': ('Basket', 'basket', 'Basket contains a drink'),
    'basket_food_and_drink': ('Basket', 'basket', 'Basket contains food and a drink'),
    'basket_discounted': ('Basket', 'basket', 'Basket contains a discounted line'),
    'branch_hour_baskets': ('Basket', 'basket', 'Baskets at the branch in the same hour (load)'),
    'branch_day_baskets': ('Basket', 'basket', 'Baskets at the branch that day (load)'),
    # Customer history
    'customer_identified': ('Customer', 'customer', 'Basket has a customer ID'),
    'customer_visit_number': ('Customer', 'customer', "Customer's visit number (since 1 Jan)"),
    'days_since_prev_visit': ('Customer', 'customer', 'Days since the customer’s previous visit'),
    'customer_new_branch': ('Customer', 'customer', 'First visit by this customer to this branch'),
    'customer_repeat': ('Customer', 'customer', 'Customer seen before'),
}

OUTCOMES = {
    'daily_baskets': ('Demand', 'Baskets per branch-day', '%'),
    'hourly_baskets': ('Demand', 'Baskets per branch-hour', '%'),
    'gp': ('Basket', 'Gross profit per basket, USD', 'USD'),
    'revenue': ('Basket', 'Revenue per basket, USD', 'USD'),
    'units': ('Basket', 'Units per basket', 'units'),
    'dine_in': ('Basket', 'Dine-in share', 'pts'),
    'cold_share': ('Basket', 'Cold share of hot + cold drink units', 'pts'),
    'has_food': ('Basket', 'Food attachment share', 'pts'),
    'discounted': ('Basket', 'Discounted-basket share', 'pts'),
}
# Outcomes that are arithmetic consequences of a feature, not effects of it.
MECHANICAL = {('basket_lines', o) for o in ['gp', 'revenue', 'units', 'has_food']} | \
    {(f, o) for f in ['basket_units', 'basket_revenue', 'basket_categories'] for o in ['gp', 'revenue', 'units', 'has_food']} | \
    {('basket_has_food', 'has_food'), ('basket_food_and_drink', 'has_food'), ('basket_discounted', 'discounted'),
     ('basket_has_drink', 'cold_share'), ('basket_has_food', 'gp'), ('basket_has_food', 'revenue'),
     ('basket_has_food', 'units'), ('basket_food_and_drink', 'gp'), ('basket_food_and_drink', 'revenue'),
     ('basket_food_and_drink', 'units'), ('basket_has_drink', 'units'), ('basket_has_drink', 'gp'),
     ('basket_has_drink', 'revenue'), ('basket_has_drink', 'has_food')} | \
    {('basket_discounted', o) for o in ['gp', 'revenue', 'units', 'has_food', 'cold_share']} | \
    {(f, 'discounted') for f in ['basket_lines', 'basket_units', 'basket_revenue', 'basket_categories',
                                 'basket_has_food', 'basket_has_drink', 'basket_food_and_drink']}
# Bigger baskets are more likely to contain a discounted line by chance (exposure selection).

def controls(feature, outcome):
    """Strata that remove branch, season, clock and promotions without absorbing the feature itself."""
    demand = OUTCOMES[outcome][0] == 'Demand'
    strata = ['branch', 'month']
    # Weekday drives demand (Tuesday spike) but not basket content; keep basket cells large.
    if demand and feature not in ('weekday', 'weekend'):
        strata.append('weekday')
    if outcome != 'daily_baskets' and feature not in ('hour', 'daypart'):
        strata.append('hour')
    if feature != 'campaign_window':
        strata.append('campaign_window')
    return strata

def frames(x):
    """Basket, branch-day and branch-hour frames carrying every feature and outcome."""
    e = enrich(x)
    e = e.assign(cold=e.category.isin(COLD)*e.quantity, hot=e.category.isin(HOT)*e.quantity,
                 food=e.category.isin(['Bakery', 'Breakfast', 'Desserts', 'Meals', 'Sandwiches']))
    feats = [f for f in CATALOG if f in e]
    b = e.groupby('transaction').agg(gp=('gp', 'sum'), revenue=('revenue', 'sum'), units=('quantity', 'sum'),
        cold=('cold', 'sum'), hot=('hot', 'sum'), has_food=('food', 'any'), discounted=('discounted', 'any'))
    first = e.drop_duplicates('transaction').set_index('transaction')
    b = b.join(first[['date', 'branch', 'month'] + [f for f in feats if f not in ('hour', 'weekday')] + ['hour', 'weekday']])
    b['dine_in'] = first.order_type.eq('Dine-in').reindex(b.index)
    b['cold_share'] = b.cold/(b.cold+b.hot).replace(0, np.nan)
    day_feats = [f for f in feats if CATALOG[f][1] == 'day']
    d = e.groupby(['date', 'branch']).agg(daily_baskets=('transaction', 'nunique'),
        month=('month', 'first'), **{f: (f, 'first') for f in day_feats}).reset_index()
    g = branch_hour_panel(x).rename(columns={'baskets': 'hourly_baskets'})
    h = hourly_context().assign(date=lambda t: t.datetime.dt.normalize(), hour=lambda t: t.datetime.dt.hour)
    g = g.merge(h[['date', 'hour'] + [c for c in h if c.startswith('hour_') and c not in g]], on=['date', 'hour'], how='left')
    g['month'] = g.date.dt.strftime('%Y-%m')
    sun = e.drop_duplicates('date').set_index('date')
    g['daypart'] = pd.cut(g.hour, [0, 7, 11, 14, 17, 20, 24], labels=['Night', 'Morning', 'Lunch', 'Afternoon',
                          'Evening', 'Late evening'], right=False).astype(str)
    sunset = (sun.datetime - pd.to_timedelta(sun.minutes_from_sunset, unit='min')).reindex(g.date).to_numpy()
    slot = g.date + pd.to_timedelta(g.hour, unit='h') + pd.Timedelta(minutes=30)
    g['minutes_from_sunset'] = (slot - sunset).dt.total_seconds()/60
    g['after_sunset'] = g.minutes_from_sunset > 0
    g['iftar_window'] = g.ramadan & g.after_sunset
    return dict(basket=b.reset_index(), daily=d, hourly=g, enriched=e)

def _design(frame, feature):
    """Numeric columns to test for one feature: itself, or one dummy per category level."""
    s = frame[feature]
    if pd.api.types.is_bool_dtype(s) or (s.dtype == object and s.dropna().map(type).eq(bool).all() and s.notna().any()):
        return {feature: s.astype(float)}
    if pd.api.types.is_numeric_dtype(s):
        return {feature: s.astype(float)}
    levels = s.dropna().astype(str).value_counts()
    return {f'{feature}={lvl}': s.astype(str).eq(lvl).where(s.notna()).astype(float) for lvl in levels.index if levels[lvl] >= 30}

def _slope(xv, yv, strata, days):
    ok = xv.notna() & yv.notna()
    xv, yv, days = xv[ok], yv[ok], days[ok]
    if strata is not None:
        keys = [k[ok] for k in strata]
        xv = xv - xv.groupby(keys).transform('mean'); yv = yv - yv.groupby(keys).transform('mean')
    else:
        xv = xv - xv.mean(); yv = yv - yv.mean()
    sxx = float((xv*xv).sum())
    if sxx < 1e-9 * max(len(xv), 1):
        return np.nan, np.nan, int(ok.sum())
    beta = float((xv*yv).sum())/sxx
    score = (xv*(yv-beta*xv)).groupby(days).sum()
    g = len(score)
    se = float(np.sqrt((score**2).sum()*g/max(g-1, 1)))/sxx
    return beta, se, int(ok.sum())

def effect(frame, column, x, outcome, strata):
    """One estimate: effect in outcome units (or % for demand), CI, t, n."""
    y = frame[outcome].astype(float)
    log = OUTCOMES[outcome][0] == 'Demand'
    if log: y = np.log(y+1)
    keys = [frame[k] for k in strata] if strata else None
    beta, se, n = _slope(x, y, keys, frame.date)
    binary = set(x.dropna().unique()) <= {0.0, 1.0}
    contrast = 1.0 if binary else float(x.quantile(.9) - x.quantile(.1))
    scale = 1 if log or OUTCOMES[outcome][2] != 'pts' else 100
    point, low, high = beta*contrast, (beta-1.96*se)*contrast, (beta+1.96*se)*contrast
    if log: point, low, high = np.expm1(point)*100, np.expm1(low)*100, np.expm1(high)*100
    else: point, low, high = point*scale, low*scale, high*scale
    return dict(effect=point, ci_low=low, ci_high=high, t=beta/se if se else np.nan, n=n,
                contrast='on vs off' if binary else f'P10→P90 ({x.quantile(.1):.3g}→{x.quantile(.9):.3g})')

def effect_matrix(fr, split='2026-04-01'):
    """Every feature × outcome: raw, controlled, split-half replication, FDR, verdict."""
    rows = []
    for feature, (group, grain, description) in CATALOG.items():
        for outcome, (kind, label, unit) in OUTCOMES.items():
            if outcome == 'daily_baskets' and grain != 'day': continue
            if outcome == 'hourly_baskets' and grain not in ('hour',) : continue
            if kind == 'Basket' and grain not in ('day', 'hour', 'basket', 'customer'): continue
            if kind == 'Demand' and group in ('Basket', 'Customer'): continue
            frame = fr['daily'] if outcome == 'daily_baskets' else fr['hourly'] if outcome == 'hourly_baskets' else fr['basket']
            if feature not in frame: continue
            strata = controls(feature, outcome)
            for column, x in _design(frame, feature).items():
                if x.nunique() < 2: continue
                raw = effect(frame, column, x, outcome, None)
                ctl = effect(frame, column, x, outcome, strata)
                h = [effect(frame[m], column, x[m], outcome, strata) for m in (frame.date < split, frame.date >= split)]
                rows.append(dict(feature=column, base_feature=feature, group=group, description=description,
                    outcome=outcome, outcome_label=label, unit=unit, contrast=ctl['contrast'], n=ctl['n'],
                    raw_effect=raw['effect'], raw_t=raw['t'], effect=ctl['effect'], ci_low=ctl['ci_low'],
                    ci_high=ctl['ci_high'], t=ctl['t'], t_first_half=h[0]['t'], t_second_half=h[1]['t'],
                    controls=' × '.join(strata), mechanical=(feature, outcome) in MECHANICAL))
    m = pd.DataFrame(rows)
    for col, p in [('q', 't'), ('raw_q', 'raw_t')]:
        pv = 2*stats.norm.sf(m[p].abs()); ok = ~np.isnan(pv)
        q = np.full(len(m), np.nan); order = np.argsort(pv[ok]); ranked = pv[ok][order]*ok.sum()/np.arange(1, ok.sum()+1)
        q_ok = np.empty(ok.sum()); q_ok[order] = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1); q[ok] = q_ok
        m[col] = q
    m['replicates'] = (np.sign(m.t_first_half) == np.sign(m.t_second_half)) & (m.t_first_half.abs() > 2) & (m.t_second_half.abs() > 2)
    m['verdict'] = np.select(
        [m.mechanical, m.t.isna(), (m.q < .05) & m.replicates, m.q < .05, (m.raw_q < .05)],
        ['Mechanical or selection', 'Absorbed by controls', 'Replicated effect', 'Unreplicated (one half only)',
         'Confounded (raw only)'], 'No effect')
    return m

def feature_curve(frame, feature, outcome, strata, bins=8):
    """Raw and controlled outcome means across a feature's values (bins for numbers)."""
    s = frame[feature]; y = frame[outcome].astype(float)
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and s.nunique() > bins:
        level = pd.qcut(s, bins, duplicates='drop').astype(str); order = pd.qcut(s, bins, duplicates='drop').cat.codes
    else:
        level = s.astype(str); order = level
    keys = [frame[k] for k in strata]
    ok = y.notna() & s.notna()
    adj = y - y.groupby(keys).transform('mean') + y[ok].mean()
    t = pd.DataFrame(dict(level=level, order=order, raw=y, controlled=adj))[ok]
    out = t.groupby('level').agg(order=('order', 'min'), n=('raw', 'size'), raw=('raw', 'mean'),
                                 controlled=('controlled', 'mean')).sort_values('order').reset_index()
    return out.drop(columns='order')
