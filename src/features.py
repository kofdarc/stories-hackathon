"""Context features: Beirut weather and air quality, Lebanese calendar, customers, baskets.

None of these fields exist in the transaction file. They are joined by date and
hour from `data/external/` (see scripts/fetch_external.py). One Beirut weather
point is assumed for every branch; lunar holidays are estimates (±1 day).
"""
from pathlib import Path
import numpy as np
import pandas as pd
from src.analytics import ROOT

EXTERNAL = ROOT / 'data' / 'external'
RAMADAN = (pd.Timestamp('2026-02-18'), pd.Timestamp('2026-03-19'))  # estimated, Lebanon
COLD = ['Cold Drinks', 'Cold Coffee']
HOT = ['Hot Coffee']
TEMP_BANDS = ([-np.inf, 14, 18, 22, np.inf], ['Cold <14°C', 'Cool 14–18°C', 'Mild 18–22°C', 'Warm ≥22°C'])

# Estimated Lebanese school breaks (verify against the MEHE circular before relying on them).
SCHOOL_BREAKS = [('2026-01-01', '2026-01-06'), ('2026-03-19', '2026-03-23'), ('2026-04-02', '2026-04-13'),
                 ('2026-06-20', '2026-06-30')]
# 15% offers appear only on these dates (inferred from the file; see analysis/outputs/REPORT.md).
CAMPAIGNS = [('2026-03-12', '2026-03-19'), ('2026-05-12', '2026-05-19')]
DST_START = pd.Timestamp('2026-03-29')  # Lebanon: last Sunday of March
DUST_EVENT = 50  # µg/m³ hourly dust; khamsin-type episodes
WMO = {0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Fog',
       51: 'Drizzle', 53: 'Drizzle', 55: 'Drizzle', 61: 'Rain', 63: 'Rain', 65: 'Heavy rain',
       71: 'Snow', 73: 'Snow', 75: 'Snow', 80: 'Showers', 81: 'Showers', 82: 'Heavy showers', 95: 'Thunderstorm'}
DAYPARTS = ([0, 7, 11, 14, 17, 20, 24], ['Night', 'Morning', 'Lunch', 'Afternoon', 'Evening', 'Late evening'])
PRODUCT_TYPE = {'Hot Coffee': 'Hot drink', 'Matcha & Tea': 'Hot/iced tea', 'Cold Coffee': 'Cold drink',
                'Cold Drinks': 'Cold drink', 'Bakery': 'Food', 'Breakfast': 'Food', 'Desserts': 'Food',
                'Meals': 'Food', 'Sandwiches': 'Food'}

def load_weather(folder=EXTERNAL):
    daily = pd.read_csv(folder/'weather_daily.csv', parse_dates=['date', 'sunrise', 'sunset'])
    hourly = pd.read_csv(folder/'weather_hourly.csv', parse_dates=['datetime'])
    return daily, hourly

def load_air(folder=EXTERNAL):
    return pd.read_csv(folder/'air_quality_hourly.csv', parse_dates=['datetime'])

def calendar(dates, folder=EXTERNAL):
    """Day-level calendar features for every date in `dates`."""
    events = pd.read_csv(folder/'calendar_lebanon_2026.csv', parse_dates=['date'])
    days = pd.DataFrame({'date': pd.DatetimeIndex(sorted(set(dates)))})
    holidays = events[events.kind.eq('public_holiday')]
    days['holiday'] = days.date.isin(holidays.date)
    days['holiday_name'] = days.date.map(holidays.groupby('date').event.agg(' / '.join))
    days['holiday_eve'] = days.date.isin(holidays.date - pd.Timedelta(days=1)) & ~days.holiday
    days['commercial_event'] = days.date.map(events[events.kind.eq('commercial')].set_index('date').event)
    days['ramadan'] = days.date.between(*RAMADAN)
    # Lebanese salaries are commonly paid at month end; window = last 3 + first 3 days (assumption).
    dom, last = days.date.dt.day, days.date.dt.days_in_month
    days['payday_window'] = (dom <= 3) | (dom > last - 3)
    days['day_of_month'] = dom
    days['week_of_month'] = (dom - 1)//7 + 1
    days['quarter'] = days.date.dt.quarter
    days['month_start'] = dom <= 6
    days['month_end'] = dom > last - 6
    h = np.sort(holidays.date.unique())
    nxt = np.searchsorted(h, days.date.to_numpy(), side='left')
    prev = np.searchsorted(h, days.date.to_numpy(), side='right') - 1
    days['days_to_next_holiday'] = [(h[i]-d).days if i < len(h) else np.nan for i, d in zip(nxt, days.date)]
    days['days_since_last_holiday'] = [(d-h[i]).days if i >= 0 else np.nan for i, d in zip(prev, days.date)]
    off = days.date.dt.dayofweek.ge(5) | days.holiday  # Lebanese weekend is Saturday–Sunday
    # A bridge day is a workday sandwiched between days off; a long weekend is ≥3 consecutive days off.
    days['bridge_day'] = ~off & off.shift(1, fill_value=False) & off.shift(-1, fill_value=False)
    run = (off != off.shift()).cumsum()
    days['long_weekend'] = off & off.groupby(run).transform('size').ge(3) & days.holiday.groupby(run).transform('any')
    days['school_break'] = np.any([days.date.between(a, b) for a, b in SCHOOL_BREAKS], axis=0)
    days['dst'] = days.date >= DST_START
    days['campaign_window'] = np.any([days.date.between(a, b) for a, b in CAMPAIGNS], axis=0)
    return days

def daily_weather(folder=EXTERNAL):
    """Day-level weather and air-quality features, including lags."""
    daily, _ = load_weather(folder); air = load_air(folder)
    d = daily.assign(
        temp_mean=daily.temperature_2m_mean, temp_max=daily.temperature_2m_max, temp_min=daily.temperature_2m_min,
        feels_like=daily.apparent_temperature_mean, rain_mm=daily.precipitation_sum,
        rain_hours=daily.precipitation_hours, wind_max=daily.wind_speed_10m_max,
        sunshine_hours=daily.sunshine_duration/3600,
        daylight_hours=(daily.sunset-daily.sunrise).dt.total_seconds()/3600,
        weather=daily.weather_code.map(WMO).fillna('Other'),
        # Weather surprise vs. the surrounding fortnight separates weather from season.
        temp_anomaly=daily.temperature_2m_mean-daily.temperature_2m_mean.rolling(15, center=True, min_periods=5).mean())
    d['temp_range'] = d.temp_max - d.temp_min
    d['temp_change_vs_yesterday'] = d.temp_mean.diff()
    d['rain_yesterday_mm'] = d.rain_mm.shift(1)
    d['rain_last_3d_mm'] = d.rain_mm.rolling(3, min_periods=1).sum()
    d['dry_streak_days'] = d.groupby((d.rain_mm >= 1).cumsum()).cumcount()
    d['rainy'] = d.rain_mm >= 1
    d['heavy_rain'] = d.rain_mm >= 10
    d['hot_day'] = d.temp_max >= 30
    d['windy'] = d.wind_max >= 40
    d['temp_band'] = pd.cut(d.temp_mean, TEMP_BANDS[0], labels=TEMP_BANDS[1], right=False)
    a = air.assign(date=air.datetime.dt.normalize()).groupby('date').agg(
        dust_max=('dust', 'max'), pm10_mean=('pm10', 'mean'), aqi_max=('us_aqi', 'max'), uv_max=('uv_index', 'max'))
    d = d.merge(a.reset_index(), on='date', how='left', validate='one_to_one')
    d['dust_event'] = d.dust_max >= DUST_EVENT
    d['poor_air'] = d.aqi_max > 100
    return d

DAY_KEEP = ['date', 'temp_mean', 'temp_max', 'temp_min', 'temp_range', 'feels_like', 'temp_anomaly',
            'temp_change_vs_yesterday', 'rain_mm', 'rain_hours', 'rain_yesterday_mm', 'rain_last_3d_mm',
            'dry_streak_days', 'rainy', 'heavy_rain', 'hot_day', 'windy', 'wind_max', 'sunshine_hours',
            'daylight_hours', 'weather', 'temp_band', 'dust_max', 'pm10_mean', 'aqi_max', 'uv_max', 'dust_event',
            'poor_air', 'sunrise', 'sunset']

def hourly_context(folder=EXTERNAL):
    _, hourly = load_weather(folder); air = load_air(folder)
    h = hourly.rename(columns={'temperature_2m': 'hour_temp', 'apparent_temperature': 'hour_feels_like',
        'precipitation': 'hour_rain_mm', 'relative_humidity_2m': 'hour_humidity', 'cloud_cover': 'hour_cloud_cover',
        'dew_point_2m': 'hour_dew_point', 'wind_speed_10m': 'hour_wind', 'is_day': 'hour_daylight'})
    h['hour_weather'] = h.pop('weather_code').map(WMO).fillna('Other')
    h['hour_daylight'] = h.hour_daylight.astype(bool)
    a = air.rename(columns={'pm10': 'hour_pm10', 'pm2_5': 'hour_pm2_5', 'dust': 'hour_dust',
                            'us_aqi': 'hour_aqi', 'uv_index': 'hour_uv'})
    return h.merge(a, on='datetime', how='left', validate='one_to_one')

def internal_features(x):
    """Features derived from the transactions themselves (no external data).

    Customer history uses only earlier visits, so no future information leaks;
    visit counts are left-censored at 1 January 2026.
    """
    out = pd.DataFrame(index=x.index)
    out['daypart'] = pd.cut(x.hour, DAYPARTS[0], labels=DAYPARTS[1], right=False).astype(str)
    out['product_type'] = x.category.map(PRODUCT_TYPE).fillna('Other')
    out['is_drink'] = out.product_type.ne('Food')
    o = x.assign(food=out.product_type.eq('Food'), drink=out.is_drink).groupby('transaction').agg(
        basket_lines=('product', 'size'), basket_units=('quantity', 'sum'), basket_revenue=('revenue', 'sum'),
        basket_categories=('category', 'nunique'), basket_has_food=('food', 'any'),
        basket_has_drink=('drink', 'any'), basket_discounted=('discounted', 'any'),
        datetime=('datetime', 'first'), branch=('branch', 'first'), customer=('customer', 'first'))
    o['basket_food_and_drink'] = o.basket_has_food & o.basket_has_drink
    # Concurrent load: baskets at the same branch in the same clock hour and day.
    slot = o.datetime.dt.floor('h')
    o['branch_hour_baskets'] = o.groupby([o.branch, slot]).datetime.transform('size')
    o['branch_day_baskets'] = o.groupby([o.branch, o.datetime.dt.normalize()]).datetime.transform('size')
    known = o.dropna(subset=['customer']).sort_values(['customer', 'datetime'])
    g = known.groupby('customer')
    known['customer_visit_number'] = g.cumcount() + 1
    known['days_since_prev_visit'] = g.datetime.diff().dt.total_seconds()/86400
    known['customer_new_branch'] = ~known.duplicated(['customer', 'branch'])
    o = o.join(known[['customer_visit_number', 'days_since_prev_visit', 'customer_new_branch']])
    o['customer_identified'] = o.customer.notna()
    o['customer_repeat'] = o.customer_visit_number.gt(1)
    cols = [c for c in o if c not in ('datetime', 'branch', 'customer')]
    return out.join(x[['transaction']].join(o[cols], on='transaction').drop(columns='transaction'))

def enrich(x, folder=EXTERNAL):
    """Return item lines with weather, air quality, calendar and derived columns added."""
    d = daily_weather(folder); h = hourly_context(folder)
    h['hour_slot'] = h.pop('datetime').dt.floor('h')
    out = x.copy()
    out['hour_slot'] = out.datetime.dt.floor('h')
    out = out.merge(d[DAY_KEEP], on='date', how='left', validate='many_to_one')
    out = out.merge(h, on='hour_slot', how='left', validate='many_to_one')
    out = out.merge(calendar(out.date, folder), on='date', how='left', validate='many_to_one')
    out.index = x.index
    out['raining_now'] = out.hour_rain_mm > 0
    out['dusty_now'] = out.hour_dust >= DUST_EVENT
    out['after_sunset'] = out.datetime >= out.sunset
    out['minutes_from_sunset'] = (out.datetime - out.sunset).dt.total_seconds()/60
    out['iftar_window'] = out.ramadan & out.after_sunset
    out = out.join(internal_features(x))
    if out[['temp_mean', 'hour_temp', 'hour_dust']].isna().any().any():
        raise ValueError('Weather coverage is incomplete for the transaction dates; rerun fetch_external.py')
    return out.drop(columns=['hour_slot', 'sunset', 'sunrise'])

def daily_panel(e):
    """One row per date × branch: baskets, revenue, drink mix and context features."""
    e = e.assign(cold_units=e.quantity.where(e.category.isin(COLD), 0),
                 hot_units=e.quantity.where(e.category.isin(HOT), 0))
    context = ['temp_mean', 'temp_anomaly', 'feels_like', 'rain_mm', 'rainy', 'heavy_rain', 'hot_day', 'sunshine_hours',
               'temp_band', 'dust_event', 'poor_air', 'holiday', 'holiday_eve', 'bridge_day', 'long_weekend',
               'school_break', 'ramadan', 'payday_window', 'weekday', 'month']
    p = e.groupby(['date', 'branch'], observed=True).agg(baskets=('transaction', 'nunique'),
        revenue=('revenue', 'sum'), gp=('gp', 'sum'), cold_units=('cold_units', 'sum'),
        hot_units=('hot_units', 'sum'), **{c: (c, 'first') for c in context}).reset_index()
    p['cold_share'] = p.cold_units/(p.cold_units+p.hot_units).replace(0, np.nan)
    return p

EFFECTS = ['rainy', 'heavy_rain', 'temp_anomaly', 'dust_event', 'holiday', 'holiday_eve', 'bridge_day',
           'school_break', 'ramadan', 'payday_window']

def _design(p, cols):
    fixed = pd.get_dummies(p.branch+'_'+p.weekday.astype(str), dtype=float)  # branch × weekday baseline
    trend = (p.date-pd.Timestamp('2026-01-01')).dt.days/30.4
    X = pd.concat([fixed, trend.rename('trend_per_month')]+[p[c].astype(float) for c in cols], axis=1)
    return X

def weather_effects(p, cols=EFFECTS, outcome='baskets'):
    """Log-linear OLS: branch×weekday + linear trend + context; week-clustered SEs.

    Coefficients are associations conditional on seasonality controls, not causal
    effects. Returns per-feature % change with 95% CI.
    """
    X = _design(p, cols); y = np.log(p[outcome].astype(float))
    A = X.to_numpy(); beta, *_ = np.linalg.lstsq(A, y.to_numpy(), rcond=None)
    resid = y.to_numpy()-A@beta
    bread = np.linalg.pinv(A.T@A)
    weeks = p.date.dt.strftime('%G-W%V').to_numpy()
    meat = sum(np.outer(s, s) for s in (A[weeks == w].T@resid[weeks == w] for w in np.unique(weeks)))
    g = len(np.unique(weeks)); se = np.sqrt(np.diag(bread@meat@bread)*g/(g-1))
    idx = [X.columns.get_loc(c) for c in cols]
    rows = [dict(feature=c, effect=np.expm1(beta[i]), ci_low=np.expm1(beta[i]-1.96*se[i]),
                 ci_high=np.expm1(beta[i]+1.96*se[i]), days_with_feature=int(p.groupby('date')[c].first().astype(bool).sum())
                 if p[c].dtype == bool else None) for c, i in zip(cols, idx)]
    return pd.DataFrame(rows)

def forecast_check(p, cols=EFFECTS, split='2026-05-01'):
    """Holdout test: does context beat a branch×weekday + trend baseline on May–Jun?"""
    train, test = p[p.date < split], p[p.date >= split]
    rows = []
    for label, c in [('Baseline: branch×weekday + trend', []), ('Baseline + weather & calendar', list(cols))]:
        Xa = _design(pd.concat([train, test]), c); Xtr, Xte = Xa.iloc[:len(train)], Xa.iloc[len(train):]
        beta, *_ = np.linalg.lstsq(Xtr.to_numpy(), np.log(train.baskets.astype(float)).to_numpy(), rcond=None)
        pred = np.exp(Xte.to_numpy()@beta); err = test.baskets.to_numpy()-pred
        rows.append(dict(model=label, test_days=test.date.nunique(), mae_baskets=float(np.abs(err).mean()),
                         mape=float(np.abs(err/test.baskets.to_numpy()).mean()), bias=float(err.mean())))
    return pd.DataFrame(rows)

def drink_mix_by_weather(e):
    """Cold vs hot drink unit share by temperature band, chain-wide."""
    d = e[e.category.isin(COLD+HOT)].assign(cold=lambda d: d.category.isin(COLD)*d.quantity)
    t = d.groupby('temp_band', observed=True).agg(days=('date', 'nunique'), drink_units=('quantity', 'sum'),
                                                   cold_units=('cold', 'sum')).reset_index()
    t['cold_share'] = t.cold_units/t.drink_units
    t['temp_band'] = t.temp_band.astype(str)
    return t

def month_turn_placebo(p, width=6):
    """Estimate the same model for every `width`-day day-of-month window.

    If the payday window is not unusual among all windows, treat it as noise.
    """
    dom = p.date.dt.day; rows = []
    for start in range(1, 32):
        days = [((start-1+k) % 31)+1 for k in range(width)]
        r = weather_effects(p.assign(window=dom.isin(days)), cols=['window']).iloc[0]
        rows.append(dict(first_day=start, days=','.join(map(str, days)), effect=r['effect'],
                         ci_low=r['ci_low'], ci_high=r['ci_high'], is_payday_window=set(days) == {29, 30, 31, 1, 2, 3}))
    return pd.DataFrame(rows).sort_values('effect', ascending=False)

def rain_order_type(e, seed=0, draws=300):
    """Dine-in share when it is raining at the transaction hour vs dry, within month.

    Month-weighted difference controls for season; day-cluster bootstrap CI.
    """
    o = e.groupby('transaction').agg(month=('month', 'first'), date=('date', 'first'),
        rain=('hour_rain_mm', 'first'), dine_in=('order_type', lambda s: s.iloc[0] == 'Dine-in'))
    def diff(o, threshold):
        o = o.assign(wet=o.rain >= threshold)
        g = o.groupby(['month', 'wet']).dine_in.mean().unstack().dropna()
        n = o[o.wet].groupby('month').size().reindex(g.index)
        return float(((g[True]-g[False])*n).sum()/n.sum()), int(o.wet.sum())
    rng = np.random.default_rng(seed); days = o.date.unique(); by_day = dict(tuple(o.groupby('date')))
    rows = []
    for threshold in [0.1, 0.5, 1.0]:
        point, n = diff(o, threshold)
        boot = [diff(pd.concat([by_day[d] for d in rng.choice(days, len(days))]), threshold)[0] for _ in range(draws)]
        rows.append(dict(rain_mm_per_hour_at_least=threshold, wet_baskets=n, dine_in_share_change=point,
                         ci_low=float(np.percentile(boot, 2.5)), ci_high=float(np.percentile(boot, 97.5))))
    return pd.DataFrame(rows)

OPEN_HOURS = range(7, 24)
REGIMES = ([0, 11, 18, 24], ['07–10', '11–17', '18–23'])

def branch_hour_panel(x, folder=EXTERNAL):
    """Every date × branch × opening hour (zeros included) with hourly weather and calendar."""
    dates = pd.date_range(x.date.min(), x.date.max())
    grid = pd.MultiIndex.from_product([dates, sorted(x.branch.unique()), OPEN_HOURS],
                                      names=['date', 'branch', 'hour']).to_frame(index=False)
    o = x.drop_duplicates('transaction')
    keys = ['date', 'branch', 'hour']
    g = grid.join(o.groupby(keys).size().rename('baskets'), on=keys)
    g = g.join(o[o.order_type.eq('Dine-in')].groupby(keys).size().rename('dine_in'), on=keys).fillna({'baskets': 0, 'dine_in': 0})
    h = hourly_context(folder).assign(date=lambda d: d.datetime.dt.normalize(), hour=lambda d: d.datetime.dt.hour)
    g = g.merge(h[['date', 'hour', 'hour_temp', 'hour_rain_mm', 'hour_dust', 'hour_humidity', 'hour_wind']],
                on=['date', 'hour'], how='left', validate='many_to_one')
    g = g.merge(calendar(dates, folder)[['date', 'holiday', 'ramadan', 'school_break', 'payday_window', 'campaign_window']], on='date')
    g['weekday'] = g.date.dt.dayofweek
    g['trend_per_month'] = (g.date-dates[0]).dt.days/30.4
    g['raining_now'] = g.hour_rain_mm > 0
    g['dusty_now'] = g.hour_dust >= DUST_EVENT
    return g

HOURLY_CONTEXT = ['hour_temp', 'raining_now', 'dusty_now', 'hour_humidity', 'hour_wind', 'holiday', 'ramadan',
                  'school_break', 'payday_window']

def _clock_design(g, extra=(), clock=True):
    parts = ([pd.get_dummies(g.branch+'_h'+g.hour.astype(str), dtype=float),
              pd.get_dummies('wd'+g.weekday.astype(str)+'_h'+g.hour.astype(str), dtype=float)] if clock
             else [pd.get_dummies(g.branch, dtype=float)])
    return pd.concat(parts+[g[['trend_per_month']]]+[g[c].astype(float) for c in extra], axis=1).to_numpy()

def poisson_fit(A, y, iterations=40):
    """Poisson log-link GLM by iteratively reweighted least squares."""
    mu = np.full(len(y), max(y.mean(), 1e-9)); eta = np.log(mu)
    for _ in range(iterations):
        w = np.sqrt(mu); z = eta+(y-mu)/mu
        beta = np.linalg.lstsq(A*w[:, None], z*w, rcond=None)[0]
        eta = np.clip(A@beta, -20, 20); mu = np.exp(eta)
    return beta

def dispersion(y, mu):
    """Pearson dispersion: 1 means pure Poisson chance around mu; >1 means unexplained structure."""
    return float(((y-mu)**2/mu).mean())

def clock_template_check(g, split='2026-05-01', seed=0):
    """Holdout comparison of a clock template vs weather/calendar, plus the Poisson noise floor.

    The floor is the MAE a forecaster would get if the template's rates were exactly
    true and counts were Poisson draws. A model at the floor leaves nothing for any
    extra feature to explain.
    """
    train = (g.date < split).to_numpy(); test = ~train; y = g.baskets.to_numpy(float)
    rows = []; rng = np.random.default_rng(seed)
    for label, extra, clock in [('Clock template: branch×hour + weekday×hour + trend', [], True),
                                ('Clock template + hourly weather & calendar', HOURLY_CONTEXT, True),
                                ('Weather & calendar only (branch + trend)', HOURLY_CONTEXT, False)]:
        A = _clock_design(g, extra, clock); mu = np.exp(np.clip(A@poisson_fit(A[train], y[train]), -20, 20))
        err = y[test]-mu[test]
        rows.append(dict(model=label, holdout_mae=float(np.abs(err).mean()),
            holdout_r2=float(1-(err**2).sum()/((y[test]-y[test].mean())**2).sum()),
            train_dispersion=dispersion(y[train], mu[train]), holdout_dispersion=dispersion(y[test], mu[test]),
            poisson_floor_mae=float(np.abs(rng.poisson(mu[test], (200, test.sum()))-mu[test]).mean())))
    t = pd.DataFrame(rows); t['gap_to_floor'] = t.holdout_mae/t.poisson_floor_mae-1
    return t

def hour_regimes(x):
    """Clock regimes: dine-in share, cold-drink share and economics by regime × order type."""
    d = x.assign(cold=x.category.isin(COLD)*x.quantity, hot=x.category.isin(HOT)*x.quantity)
    o = d.groupby('transaction').agg(hour=('hour', 'first'), order_type=('order_type', 'first'),
        gp=('gp', 'sum'), units=('quantity', 'sum'), cold=('cold', 'sum'), hot=('hot', 'sum'))
    o['regime'] = pd.cut(o.hour, REGIMES[0], labels=REGIMES[1], right=False).astype(str)
    t = o.groupby(['regime', 'order_type']).agg(baskets=('gp', 'size'), gp_per_basket=('gp', 'mean'),
        units_per_basket=('units', 'mean'), cold=('cold', 'sum'), hot=('hot', 'sum')).reset_index()
    t['cold_share'] = t.cold/(t.cold+t.hot)
    t['share_of_regime_baskets'] = t.baskets/t.groupby('regime').baskets.transform('sum')
    return t.drop(columns=['cold', 'hot'])

def hourly_profile(x):
    d = x.assign(cold=x.category.isin(COLD)*x.quantity, hot=x.category.isin(HOT)*x.quantity)
    o = x.drop_duplicates('transaction')
    t = d.groupby('hour')[['cold', 'hot']].sum()
    t['cold_share'] = t.cold/(t.cold+t.hot)
    t['dine_in_share'] = o.groupby('hour').order_type.apply(lambda s: s.eq('Dine-in').mean())
    t['baskets'] = o.groupby('hour').size()
    return t.drop(columns=['cold', 'hot']).reset_index()

def staffing_template(g, x, quantile=.9):
    """Expected June baskets per branch × weekday × hour, with a Poisson planning quantile."""
    from scipy import stats
    A = _clock_design(g); mu = np.exp(np.clip(A@poisson_fit(A, g.baskets.to_numpy(float)), -20, 20))
    last = g.assign(expected=mu)[g.date >= '2026-06-01']
    t = last.groupby(['branch', 'weekday', 'hour']).expected.mean().reset_index()
    t[f'p{int(quantile*100)}_baskets'] = stats.poisson.ppf(quantile, t.expected).astype(int)
    return t
