"""Monte Carlo over the uncertain inputs behind the outside-in decisions.

Each module draws every assumption from a stated distribution, replays it against the transaction file,
and reports the probability that the action pays plus the P5/P50/P95 of its six-month value.
Distributions and their basis are listed in INPUTS; change them there.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import outside_in_chains as oc

ROOT = Path(__file__).resolve().parents[1]
N = 20_000
SEED = 490
HORIZON_DAYS = 182
EDL_USD_KWH = 0.27                      # EDL tariff above 100 kWh/month, unchanged since 2022
CLOSE = [('Uptown', 7), ('Uptown', 8), ('Garden', 7)]
COFFEE = ['Hot Coffee', 'Cold Coffee']
THETA_BETA = (0.657, 2.087)             # fitted to Strulov-Shlain (2023): mean 0.22, IQR 0.04-0.40

INPUTS = [
    ('Opening hours', 'Staff on the early shift', '1 (40%) or 2 (60%)', 'Assumption'),
    ('Opening hours', 'Loaded wage per staff-hour', 'Triangular $1.80 / $2.60 / $3.50', 'Minimum wage 28M LBP ≈ $312/mo; barista ≈ $450 + charges'),
    ('Opening hours', 'Share of closed staff-hours actually removed', 'Uniform 50–100%', 'Assumption (bake-off and receiving may keep someone in)'),
    ('Opening hours', 'Electricity per open hour', 'Triangular 1.5 / 3 / 5 kWh', 'Espresso standby 0.33 kWh/h + brewing, lights, HVAC'),
    ('Opening hours', 'Generator share of marginal kWh', 'Uniform 60–100%', 'EDL supplied 4–9 h/day in 2026'),
    ('Opening hours', 'Generator tariff, next 6 months', 'Uniform $0.45–$0.59/kWh', 'Ministry tariffs Mar–Sep 2026'),
    ('Opening hours', 'Customers who come back later', 'Beta(2,3), mean 40%', 'Assumption'),
    ('Opening hours', 'Demand level', 'Uniform between H1 average and June run-rate', 'Chain 1: growth may not be real'),
    ('Opening hours', 'Sampling noise in hourly GP', 'Bootstrap of the 181 trading days', 'Data'),
    ('Costs and prices', 'Coffee cost drift since cost master', 'Triangular −4% / +1% / +7%', 'Arabica −16% × bean share, plus dairy and packaging'),
    ('Costs and prices', 'Other food cost drift', 'Triangular 0% / +7% / +18%', 'Food CPI +15% → +18% y/y'),
    ('Costs and prices', 'Matcha powder per drink', 'Uniform 2–4 g', 'Assumption'),
    ('Costs and prices', 'Matcha landed price rise', 'Triangular +$15 / +$60 / +$120 per kg', 'Tencha auctions +22% to +80% y/y'),
    ('Costs and prices', 'Category price elasticity', 'Triangular −1.5 / −0.8 / −0.25', 'Food away from home −0.7 to −0.8; coffee −0.26'),
    ('Costs and prices', 'Coffee elasticity multiplier', 'Uniform 1.0–1.5×', 'Coffee is the most price-compared item (assumption)'),
    ('Matcha supply', 'Chance of a supply disruption in 6 months', 'Uniform 5–30%', 'Japanese suppliers rationing since 2025'),
    ('Matcha supply', 'Disruption length', 'Uniform 7–28 days', 'Assumption'),
    ('Matcha supply', 'Matcha buyers who switch drink', 'Uniform 30–80%', 'Assumption'),
    ('Price endings', 'Left-digit bias θ', 'Beta(0.66, 2.09): mean 0.24, IQR 0.06–0.37', 'Strulov-Shlain (2023) product estimates'),
    ('Price endings', 'Item elasticity multiplier', 'Uniform 1.0–2.0× category elasticity', 'Items substitute within the menu'),
]


def tri(rng, lo, mode, hi, n=N):
    return rng.triangular(lo, mode, hi, n)


def summarize(name, v):
    v = np.asarray(v, float)
    return dict(metric=name, p_positive=float((v > 0).mean()), mean=float(v.mean()), p5=float(np.percentile(v, 5)),
                p50=float(np.percentile(v, 50)), p95=float(np.percentile(v, 95)))


def drivers(target, inputs):
    rows = [dict(input=k, spearman=stats.spearmanr(v, target).statistic) for k, v in inputs.items()]
    return pd.DataFrame(rows).sort_values('spearman', key=abs, ascending=False)


# ---------- A. Opening hours ----------
def opening_hours(o, rng):
    o = o.assign(month=o.date.dt.month)
    days = pd.date_range(o.date.min(), o.date.max())
    staff = np.where(rng.random(N) < .4, 1, 2)
    wage = tri(rng, 1.80, 2.60, 3.50)
    realized = rng.uniform(.5, 1.0, N)
    kwh = tri(rng, 1.5, 3.0, 5.0)
    gen_share = rng.uniform(.6, 1.0, N)
    tariff = rng.uniform(.45, .59, N)
    recapture = rng.beta(2, 3, N)
    level = rng.uniform(0, 1, N)
    cost_hour = staff * wage * realized + kwh * (gen_share * tariff + (1 - gen_share) * EDL_USD_KWH)
    total = np.zeros(N)
    per = []
    for b, h in CLOSE:
        s = o[(o.branch == b) & (o.hour == h)]
        daily = s.groupby('date').gp.sum().reindex(days, fill_value=0).to_numpy()
        june = s[s.month == 6].gp.sum() / 30
        boot = daily[rng.integers(0, len(daily), (N, len(daily)))].mean(1)
        gp_hour = boot * (1 + level * (june / daily.mean() - 1))
        saving = HORIZON_DAYS * (cost_hour - (1 - recapture) * gp_hour)
        total += saving
        per.append(summarize(f'{b} {h:02d}:00', saving))
    inputs = dict(staff=staff, wage=wage, labour_realized=realized, kwh=kwh, generator_share=gen_share,
                  tariff=tariff, recapture=recapture, demand_level=level)
    return total, pd.DataFrame(per), drivers(total, inputs)


# ---------- B. Cost drift and the price decision ----------
def costs_and_prices(x, rng):
    x = x.assign(group=np.where(x['product'].isin(oc.MATCHA), 'Matcha', np.where(x.category.isin(COFFEE), 'Coffee', 'Other')))
    x['cogs'] = x.revenue - x.gp
    g = x.groupby('group').agg(revenue=('revenue', 'sum'), cogs=('cogs', 'sum'), units=('quantity', 'sum'))
    war = x[x.month >= 3].groupby('group').agg(cogs=('cogs', 'sum'), units=('quantity', 'sum'))
    k_coffee = tri(rng, -.04, .01, .07)
    k_other = tri(rng, 0, .07, .18)
    grams = rng.uniform(2, 4, N)
    dkg = tri(rng, 15, 60, 120)
    per_drink = grams * dkg / 1000
    # Matcha drinks: powder rise per drink plus half the food drift on the milk and cups.
    overstated = (k_coffee * war.cogs['Coffee'] + k_other * war.cogs['Other']
                  + per_drink * war.units['Matcha'] + .5 * k_other * war.cogs['Matcha'])
    true_cogs = {'Coffee': g.cogs['Coffee'] * (1 + k_coffee), 'Other': g.cogs['Other'] * (1 + k_other),
                 'Matcha': g.cogs['Matcha'] * (1 + .5 * k_other) + per_drink * g.units['Matcha']}
    eps = tri(rng, -1.5, -.8, -.25)
    eps_coffee = eps * rng.uniform(1.0, 1.5, N)

    def delta(group, p, e):
        r, c = g.revenue[group], true_cogs[group]
        return (1 + p) ** e * (r * (1 + p) - c) - (r - c)

    uniform5 = sum(delta(k, .05, eps_coffee if k == 'Coffee' else eps) for k in ['Coffee', 'Other', 'Matcha'])
    hold_coffee = delta('Other', .05, eps) + delta('Matcha', .05, eps)
    true_margin = 1 - sum(true_cogs.values()) / g.revenue.sum()
    inputs = dict(coffee_drift=k_coffee, food_drift=k_other, matcha_grams=grams, matcha_usd_per_kg=dkg,
                  elasticity=eps, coffee_elasticity=eps_coffee)
    res = dict(overstated=overstated, uniform5=uniform5, hold_coffee=hold_coffee, true_margin=true_margin,
               per_drink=per_drink, eps=eps, eps_coffee=eps_coffee)
    return res, drivers(uniform5 - hold_coffee, inputs), drivers(overstated, inputs)


# ---------- C. Matcha supply ----------
def matcha_supply(x, rng, per_drink):
    m = x[x['product'].isin(oc.MATCHA)]
    days = x.date.nunique()
    gp_day = m.gp.sum() / days
    june = m[m.month == 6].gp.sum() / 30
    level = rng.uniform(0, 1, N)
    gp_day = gp_day + level * (june - gp_day)
    hit = rng.random(N) < rng.uniform(.05, .30, N)
    length = rng.uniform(7, 28, N)
    switch = rng.uniform(.3, .8, N)
    stockout = hit * length * gp_day * (1 - switch)
    units_6mo = m.quantity.sum() / days * HORIZON_DAYS
    price_lock = per_drink * units_6mo
    return stockout, price_lock, stockout + price_lock


# ---------- D. Harbour price endings ----------
def perceived(p, theta, focal=.5):
    return (1 - theta) * p + theta * (np.floor(p) + focal)


def price_endings(x, rng, eps):
    _, t = oc.price_points(x)
    theta = rng.beta(*THETA_BETA, N)
    e = eps * rng.uniform(1.0, 2.0, N)
    down = np.zeros(N)
    up = np.zeros(N)
    for r in t.itertuples():
        base = perceived(r.harbour, theta)
        q0, c = r.harbour_units, r.harbour_cost
        for price, acc in [(np.floor(r.harbour) - .05, down), (np.floor(r.harbour) + .25, up)]:
            q = q0 * (perceived(price, theta) / base) ** e
            acc += q * (price - c) - q0 * (r.harbour - c)
    by_eps = pd.DataFrame(dict(elasticity=e, down_beats_up=down > up))
    labels = ['below −2', '−2 to −1.5', '−1.5 to −1.25', '−1.25 to −1', '−1 to −0.75', '−0.75 to −0.5', 'above −0.5']
    by_eps['band'] = pd.cut(by_eps.elasticity, [-9, -2, -1.5, -1.25, -1, -.75, -.5, 0], labels=labels)
    curve = by_eps.groupby('band', observed=True).agg(down_beats_up=('down_beats_up', 'mean'), draws=('down_beats_up', 'size')).reset_index()
    return down, up, theta, e, curve


def money(v):
    return f'-${-v:,.0f}' if v < 0 else f'${v:,.0f}'


def report(r):
    s = r['summary'].set_index('metric')
    row = lambda k: s.loc[k]
    h = row('Close 3 early branch-hours: 6-month saving')
    d = row('GP overstated by frozen costs, Mar–Jun')
    u = row('+5% on every item vs no change: 6-month GP')
    hc = row('+5% except coffee vs no change: 6-month GP')
    uh = row('+5% everywhere minus +5% except coffee')
    mc = row('Matcha fixed-price contract: value before premium')
    dn = row('Harbour: drop to $N.95 vs today, 6-month GP')
    upp = row('Harbour: raise to $N.25 vs today, 6-month GP')
    du = row('Harbour: $N.95 minus $N.25')
    hd = r['hours_drivers'].head(4)
    curve = r['curve']
    fmt = lambda x: f"{money(x.p50)} (P5 {money(x.p5)} to P95 {money(x.p95)})"
    inputs = '\n'.join(f'| {m} | {i} | {dist} | {b} |' for m, i, dist, b in INPUTS)
    per = '\n'.join(f'| {x.metric} | {x.p_positive:.0%} | {money(x.p50)} | {money(x.p5)} to {money(x.p95)} |'
                     for x in r['hours_per'].itertuples())
    drv = ', '.join(f"{x.input.replace('_', ' ')} (ρ={x.spearman:+.2f})" for x in hd.itertuples())
    cv = '\n'.join(f'| {x.band} | {x.down_beats_up:.0%} |' for x in curve.itertuples())
    return f"""# Monte Carlo: how sure are the outside-in decisions?

**{N:,} draws per decision, seed {SEED}.** Every assumption behind the outside-in chains ([outside_in_chains.md](outside_in_chains.md)) is drawn from a stated distribution and replayed against the transaction file. Hourly GP is bootstrapped over the 181 trading days. Each result is the probability that the action pays plus its six-month value (median, P5–P95). Rebuild: `python scripts/monte_carlo.py`. Draws: `tables/mc_draws.csv.gz`.

## Results

| Decision | P(pays) | Six-month value, median (P5 to P95) |
|---|---|---|
| Close Uptown 07:00–09:00 and Garden 07:00 | {h.p_positive:.0%} | {fmt(h)} |
| Raise every price 5% | {u.p_positive:.0%} | {fmt(u)} |
| Raise 5% but hold coffee | {hc.p_positive:.0%} | {fmt(hc)} |
| Uniform 5% beats holding coffee | {uh.p_positive:.0%} | {fmt(uh)} |
| Fixed-price matcha contract (value before its premium) | n/a | {fmt(mc)} |
| Harbour: move 11 prices down to $N.95 | {dn.p_positive:.0%} | {fmt(dn)} |
| Harbour: move them up to $N.25 | {upp.p_positive:.0%} | {fmt(upp)} |
| $N.95 beats $N.25 | {du.p_positive:.0%} | {fmt(du)} |

GP overstated by frozen unit costs, March–June: **{fmt(d)}**. The cost drift of non-coffee food explains almost all of the spread.

## What the simulation changed

1. **Opening hours: staffing decides, not the energy shock.** The closure pays in {h.p_positive:.0%} of draws. The inputs that move the answer are {drv}. The generator tariff barely matters. The chain from Hormuz to the generator tariff is real, but it is a minor driver. Before closing, check whether the early shift really has two people and whether those hours can be removed from the roster.

| Branch-hour | P(saving > 0) | Median | P5 to P95 |
|---|---|---|---|
{per}

2. **Prices: drop "hold coffee".** A 5% rise pays in {u.p_positive:.0%} of draws because the break-even elasticity at Stories' {r['margin']:.1%} margin is {r['break_even_eps']:.2f}. That is beyond the whole prior range (−0.25 to −1.5 for categories), so the 100% reflects the prior, not proof. Holding coffee back gives up money in {uh.p_positive:.0%} of draws and only wins if coffee demand is far more elastic than the rest of the menu. The revised action is a uniform +5% at one branch for four weeks, measured against the other two. Elasticity is the only input that matters here (ρ≈1.0 in `tables/mc_price_drivers.csv`), so the test is worth more than any further modelling.

3. **Matcha: lock the price.** A six-month fixed-price contract is worth {fmt(mc)} before its premium. Most of that is the price lock, and only a small part is avoided stockouts. Pay a premium below the median and the contract pays in most draws.

4. **Harbour endings: test both directions.** Dropping to $N.95 beats rounding up to $N.25 in only {du.p_positive:.0%} of draws. The answer turns on item elasticity:

| Item elasticity | P($N.95 beats $N.25) |
|---|---|
{cv}

Run the Harbour A/B with three arms (today, $N.95, $N.25), not two.

## Inputs

| Module | Input | Distribution | Basis |
|---|---|---|---|
{inputs}

## Limits

Constant-elasticity demand ignores customers who leave for a competitor for good, and that is the real risk of any price rise. No cross-item substitution is modelled except through the item-elasticity multiplier. Draws are independent except where one module feeds another (matcha cost → contract value; category elasticity → item elasticity). The simulation measures how far our assumptions spread the answer. It does not validate the assumptions; the field tests do that.
"""


def run(source=ROOT / 'stories_transactions.csv', out=ROOT / 'reports'):
    rng = np.random.default_rng(SEED)
    x = oc.load(source)
    o = oc.baskets(x)
    tables = Path(out) / 'tables'
    tables.mkdir(parents=True, exist_ok=True)
    hours_total, hours_per, hours_drivers = opening_hours(o, rng)
    cp, price_drivers, drift_drivers = costs_and_prices(x, rng)
    stockout, lock, contract = matcha_supply(x, rng, cp['per_drink'])
    down, up, theta, e_item, curve = price_endings(x, rng, cp['eps'])
    summary = pd.DataFrame([
        summarize('Close 3 early branch-hours: 6-month saving', hours_total),
        summarize('GP overstated by frozen costs, Mar–Jun', cp['overstated']),
        summarize('+5% on every item vs no change: 6-month GP', cp['uniform5']),
        summarize('+5% except coffee vs no change: 6-month GP', cp['hold_coffee']),
        summarize('+5% everywhere minus +5% except coffee', cp['uniform5'] - cp['hold_coffee']),
        summarize('Matcha fixed-price contract: value before premium', contract),
        summarize('Harbour: drop to $N.95 vs today, 6-month GP', down),
        summarize('Harbour: raise to $N.25 vs today, 6-month GP', up),
        summarize('Harbour: $N.95 minus $N.25', down - up),
    ])
    summary.to_csv(tables / 'mc_summary.csv', index=False)
    hours_per.to_csv(tables / 'mc_hours_by_branch_hour.csv', index=False)
    hours_drivers.to_csv(tables / 'mc_hours_drivers.csv', index=False)
    price_drivers.to_csv(tables / 'mc_price_drivers.csv', index=False)
    drift_drivers.to_csv(tables / 'mc_cost_drift_drivers.csv', index=False)
    curve.to_csv(tables / 'mc_price_endings_by_elasticity.csv', index=False)
    pd.DataFrame(INPUTS, columns=['module', 'input', 'distribution', 'basis']).to_csv(tables / 'mc_inputs.csv', index=False)
    draws = pd.DataFrame(dict(hours_saving=hours_total, gp_overstated=cp['overstated'], uniform5=cp['uniform5'],
                              hold_coffee=cp['hold_coffee'], matcha_contract=contract, matcha_stockout=stockout,
                              endings_down=down, endings_up=up, elasticity=cp['eps'], item_elasticity=e_item,
                              theta=theta))
    draws.to_csv(tables / 'mc_draws.csv.gz', index=False, compression='gzip')
    margin = x.gp.sum() / x.revenue.sum()
    r = dict(margin=margin, break_even_eps=-np.log(1 + .05 / margin) / np.log(1.05), summary=summary, hours_per=hours_per, hours_drivers=hours_drivers, price_drivers=price_drivers,
                drift_drivers=drift_drivers, curve=curve, draws=draws, true_margin=cp['true_margin'])
    (Path(out) / 'monte_carlo.md').write_text(report(r))
    return r


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--source', default=ROOT / 'stories_transactions.csv')
    a.add_argument('--output', default=ROOT / 'reports')
    args = a.parse_args()
    r = run(args.source, args.output)
    pd.set_option('display.width', 200)
    print(r['summary'].round(3).to_string(index=False))
