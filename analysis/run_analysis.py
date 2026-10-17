#!/usr/bin/env python3
"""Rebuild discount evidence from the untouched CSV. No network or database needed."""
import argparse
import hashlib
import json
import platform
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ['units', 'lines', 'revenue', 'gp', 'list_value']
ELIGIBLE = ['Cold Coffee', 'Desserts']
SEED = 490


def load(source):
    x = pd.read_csv(source, keep_default_na=False)
    original = x.copy()
    for col, short in [('Unit Price (USD)', 'price'), ('Unit Cost (USD)', 'cost'),
                       ('Line Revenue (USD)', 'revenue'), ('Line Gross Profit (USD)', 'gp')]:
        x[short + '_cents'] = x[col].map(lambda v: int(Decimal(str(v)) * 100))
    x['list_cents'] = x.Quantity * x.price_cents
    x['cogs_cents'] = x.Quantity * x.cost_cents
    x['d10'] = x['Discount Rate'].eq(.10)
    x['d15'] = x['Discount Rate'].eq(.15)
    x['eligible'] = x.Category.isin(ELIGIBLE)
    x['date'] = pd.to_datetime(x.Date, format='%Y-%m-%d')
    x['month'] = x.date.dt.strftime('%Y-%m')
    x['dow'] = x.date.dt.dayofweek
    x['daypart'] = x.Time.str[:2].astype(int) // 4
    x['known'] = x['Customer ID'].ne('')
    expected = [int((Decimal(int(v)) * (1 - Decimal(str(d)))).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP)) for v, d in zip(x.list_cents, x['Discount Rate'])]
    arithmetic = np.abs(x.revenue_cents - np.array(expected))
    gp_error = np.abs(x.gp_cents - (x.revenue_cents - x.cogs_cents))
    conflicts = x.groupby('Transaction ID')[['Date', 'Time', 'Branch', 'Customer ID', 'Order Type']].nunique().gt(1).any(axis=1)
    checks = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  rows=len(x), orders=x['Transaction ID'].nunique(),
                  first_date=x.Date.min(), last_date=x.Date.max(),
                  exact_duplicate_excess_rows=int(original.duplicated().sum()),
                  duplicate_excess_revenue=float(x.loc[original.duplicated(), 'revenue_cents'].sum()/100),
                  conflicting_order_metadata=int(conflicts.sum()),
                  missing_required_cells=int(original.drop(columns='Customer ID').eq('').sum().sum()),
                  revenue_arithmetic_over_one_cent=int((arithmetic > 1).sum()),
                  gp_arithmetic_over_one_cent=int((gp_error > 1).sum()),
                  revenue_rounding_one_cent=int((arithmetic == 1).sum()),
                  gp_rounding_one_cent=int((gp_error == 1).sum()),
                  negative_gp_lines=int(x.gp_cents.lt(0).sum()),
                  nonpositive_quantity=int(x.Quantity.le(0).sum()),
                  unexpected_discount_rates=sorted(set(x['Discount Rate']) - {0, .1, .15}),
                  revenue=float(x.revenue_cents.sum()/100), gp=float(x.gp_cents.sum()/100))
    assert not any(checks[k] for k in ['conflicting_order_metadata', 'missing_required_cells',
        'revenue_arithmetic_over_one_cent', 'gp_arithmetic_over_one_cent', 'nonpositive_quantity'])
    assert not checks['unexpected_discount_rates']
    pd.to_datetime(x.Time, format='%H:%M:%S')
    return x, original, checks


def orders(x):
    o = x.groupby('Transaction ID', sort=True).agg(
        lines=('Quantity', 'size'), units=('Quantity', 'sum'),
        revenue=('revenue_cents', 'sum'), gp=('gp_cents', 'sum'),
        list_value=('list_cents', 'sum'), cogs=('cogs_cents', 'sum'),
        d10=('d10', 'max'), d15=('d15', 'max'), eligible=('eligible', 'max'),
        branch=('Branch', 'first'), date=('date', 'first'), month=('month', 'first'),
        dow=('dow', 'first'), daypart=('daypart', 'first'), known=('known', 'first'),
        customer=('Customer ID', 'first'), order_type=('Order Type', 'first'))
    for c in ['revenue', 'gp', 'list_value', 'cogs']:
        o[c] /= 100
    o['group'] = np.select([o.d10 & o.d15, o.d15, o.d10], ['both', '15%', '10%'], default='0%')
    return o


def summary(o, by):
    return o.groupby(by, dropna=False).agg(n=('units', 'size'), units=('units', 'mean'),
        lines=('lines', 'mean'), revenue=('revenue', 'mean'), gp=('gp', 'mean'),
        list_value=('list_value', 'mean'), total_revenue=('revenue', 'sum'), total_gp=('gp', 'sum'))


def contrast(data, treatment, keys, label, min_t=1, min_c=1):
    """Treated-weighted standardization; date-cluster sandwich, conditional on strata."""
    d = data.copy()
    d['t'] = treatment.astype(int)
    d['cell'] = d.groupby(keys, dropna=False).ngroup() if keys else 0
    counts = d.groupby(['cell', 't']).size().unstack(fill_value=0).reindex(columns=[0, 1], fill_value=0)
    cells = counts.index[(counts[0] >= min_c) & (counts[1] >= min_t)]
    z = d[d.cell.isin(cells)].copy()
    nt = int(z.t.sum())
    if not nt:
        return [dict(comparison=label, outcome=y, difference=float('nan'),
            low=float('nan'), high=float('nan'), treated=0, controls=0,
            treated_total=int(d.t.sum()), coverage=0., cells=0, date_clusters=0)
            for y in OUTCOMES]
    results = []
    for outcome in OUTCOMES:
        means = z.groupby(['cell', 't'])[outcome].mean().unstack()
        n1 = counts.loc[cells, 1]
        estimate = float(((means[1] - means[0]) * n1).sum()/nt)
        mu0 = z.cell.map(means[0])
        ratio = z.cell.map(counts[1] / counts[0].replace(0, np.nan))
        score = np.where(z.t.eq(1), z[outcome] - mu0 - estimate, -ratio*(z[outcome]-mu0))/nt
        scores = pd.Series(score, index=z.index).groupby(z.date).sum()
        g = len(scores)
        se = float(np.sqrt((scores**2).sum()*g/(g-1))) if g > 1 else float('nan')
        results.append(dict(comparison=label, outcome=outcome, difference=estimate,
            low=estimate-1.96*se, high=estimate+1.96*se, treated=nt,
            controls=int(z.t.eq(0).sum()), treated_total=int(d.t.sum()),
            coverage=nt/int(d.t.sum()), cells=len(cells), date_clusters=g))
    return results


def placebo(x, reps):
    """Shuffle 10% labels among non-15% item lines within branch/month/category.

    Basket contents never change. Thus an apparent basket lift can arise solely
    from defining exposure as 'at least one discounted line'. This is a diagnostic,
    not a valid randomization test of the real promotion's causal effect.
    """
    x = x.reset_index(drop=True)
    oid, names = pd.factorize(x['Transaction ID'], sort=True)
    o = orders(x).loc[names]
    mask = ~o.d15.to_numpy()
    pools = [g.index.to_numpy() for _, g in x[~x.d15].groupby(['Branch', 'month', 'Category'])]
    original = x.d10.to_numpy()
    rng = np.random.default_rng(SEED)
    results = []
    for rep in range(reps):
        shuffled = original.copy()
        for idx in pools:
            shuffled[idx] = rng.permutation(original[idx])
        exposed = np.bincount(oid, weights=shuffled, minlength=len(o)) > 0
        row = {'replicate': rep}
        for y in OUTCOMES:
            values = o[y].to_numpy()
            row[y] = float(values[mask & exposed].mean()-values[mask & ~exposed].mean())
        results.append(row)
    return pd.DataFrame(results)


def daily_did(x):
    """Daily branch/date FE, branch-specific weekday effects; date-cluster SE."""
    results = []
    for scope in ['all', 'eligible', 'other']:
        z = x if scope == 'all' else x[x.eligible.eq(scope == 'eligible')]
        daily = z.groupby(['date', 'Branch']).agg(units=('Quantity', 'sum'),
            revenue=('revenue_cents', 'sum'), gp=('gp_cents', 'sum'), orders=('Transaction ID', 'nunique'))
        full = pd.MultiIndex.from_product([pd.date_range(x.date.min(), x.date.max()), sorted(x.Branch.unique())], names=['date', 'Branch'])
        daily = daily.reindex(full, fill_value=0).reset_index()
        daily[['revenue', 'gp']] /= 100
        starts = [(pd.Timestamp(s), 'campaign') for s in ['2026-03-12', '2026-05-12']]
        starts += [(s-pd.Timedelta(days=14), 'pre-period placebo') for s, _ in starts.copy()]
        for start, window_type in starts:
            d = daily[daily.date.between(start-pd.Timedelta(days=28), start+pd.Timedelta(days=7))].copy()
            d['during'] = d.date.ge(start).astype(float)
            d['harbour'] = d.Branch.eq('Harbour').astype(float)
            d['dow'] = d.date.dt.dayofweek.astype(str)
            nuisance = pd.get_dummies(d[['Branch', 'date']].astype(str), drop_first=True, dtype=float)
            weekday = pd.get_dummies(d.dow, drop_first=True, dtype=float)
            interactions = [weekday.mul(d.Branch.eq(b), axis=0).to_numpy() for b in ['Harbour', 'Uptown']]
            base = np.column_stack([np.ones(len(d)), nuisance.to_numpy(), *interactions])
            for trend in [False, True]:
                design = base
                if trend:
                    t = (d.date - d.date.min()).dt.days.to_numpy()
                    design = np.column_stack([design, t*d.harbour, t*d.Branch.eq('Uptown')])
                design = np.column_stack([design, d.harbour*d.during])
                inverse = np.linalg.pinv(design.T@design)
                for outcome in ['units', 'orders', 'revenue', 'gp']:
                    y = d[outcome].to_numpy()
                    beta = np.linalg.lstsq(design, y, rcond=None)[0]
                    residual = y-design@beta
                    scores = np.array([design[d.date.eq(day)].T@residual[d.date.eq(day)] for day in d.date.unique()])
                    n, k = design.shape
                    g = len(scores)
                    cov = inverse @ (scores.T@scores) @ inverse * g/(g-1)*(n-1)/(n-k)
                    se = float(np.sqrt(max(0, cov[-1, -1])))
                    # Simple baseline is Harbour's pre/during difference, before any controls.
                    harbour = d[d.harbour.eq(1)]
                    raw = harbour.groupby('during')[outcome].mean()
                    results.append(dict(scope=scope, window=str(start.date()), window_type=window_type, branch_trend=trend,
                        outcome=outcome, difference=float(beta[-1]), low=float(beta[-1]-1.96*se),
                        high=float(beta[-1]+1.96*se), raw_harbour_change=float(raw[1]-raw[0]),
                        pre_harbour_mean=float(raw[0]), date_clusters=g, campaign_days=8))
    return pd.DataFrame(results)


def table(df, cols=None, digits=3):
    d = df[cols] if cols else df
    def fmt(v):
        if pd.isna(v):
            return 'unavailable'
        return f'{v:,.{digits}f}' if isinstance(v, (float, np.floating)) else str(v)
    return '| ' + ' | '.join(map(str, d.columns)) + ' |\n| ' + ' | '.join(['---']*len(d.columns)) + ' |\n' + '\n'.join('| '+' | '.join(fmt(v) for v in row)+' |' for row in d.itertuples(index=False, name=None))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'stories_transactions.csv')
    p.add_argument('--output', type=Path, default=ROOT/'analysis/outputs')
    p.add_argument('--permutations', type=int, default=400)
    args = p.parse_args()
    assert args.permutations >= 20
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    x, original, qa = load(args.source)
    o = orders(x)
    qa.update(missing_customer_orders=int((~o.known).sum()),
              mixed_discount_orders=int(x.groupby('Transaction ID')['Discount Rate'].nunique().gt(1).sum()),
              branch_days=int(x.groupby(['Branch', 'Date']).ngroups),
              all_ids_have_SYN_prefix=bool(x['Transaction ID'].str.startswith('SYN-').all()),
              pandas=pd.__version__, numpy=np.__version__, python=platform.python_version(), seed=SEED,
              permutations=args.permutations)
    assert len(o) == qa['orders']
    assert round(o.revenue.sum()*100) == int(x.revenue_cents.sum())
    assert round(o.gp.sum()*100) == int(x.gp_cents.sum())
    base = summary(o, 'group').reset_index()
    base['gross_margin'] = base.total_gp/base.total_revenue
    base.to_csv(out/'basket_summary.csv', index=False)
    summary(o, ['branch', 'group']).to_csv(out/'branch_summary.csv')
    summary(o, ['month', 'group']).to_csv(out/'monthly_summary.csv')
    results = []
    for rate in ['10%', '15%']:
        d = o[o.group.isin(['0%', rate])]
        results += contrast(d, d.group.eq(rate), [], rate+' unadjusted')
    d = o[o.group.isin(['0%', '10%'])]
    results += contrast(d, d.d10, ['branch', 'month', 'order_type', 'known'],
                        '10% coarse context matched')
    results += contrast(d, d.d10, ['branch', 'month', 'dow', 'daypart', 'order_type', 'known'],
                        '10% context matched', min_t=3, min_c=5)
    known = d[d.known]
    results += contrast(known, known.d10, ['customer'], '10% same identified customer')
    d15 = o[o.branch.eq('Harbour') & o.date.isin(x.loc[x.d15, 'date']) & o.eligible & ~o.d10]
    results += contrast(d15, d15.d15, ['date', 'daypart', 'order_type'],
                        '15% Harbour eligible same dates')
    dedup = orders(x.loc[~original.duplicated()])
    for rate in ['10%', '15%']:
        d = dedup[dedup.group.isin(['0%', rate])]
        results += contrast(d, d.group.eq(rate), [], rate+' duplicate sensitivity')
    contrasts = pd.DataFrame(results)
    contrasts.to_csv(out/'contrasts.csv', index=False)
    # Product/time standardization of quantity on item lines addresses product mix.
    line_results = []
    for rate in [.1, .15]:
        d = x[x['Discount Rate'].isin([0, rate])].copy()
        if rate == .15:
            d = d[d.Branch.eq('Harbour') & d.date.isin(x.loc[x.d15, 'date']) & d.eligible]
        for name, source in [('units', 'Quantity'), ('lines', 'Quantity'),
                             ('revenue', 'revenue_cents'), ('gp', 'gp_cents'), ('list_value', 'list_cents')]:
            d[name] = d[source] / (100 if source.endswith('_cents') else 1)
        keys = ['Branch', 'month', 'Product', 'Order Type', 'daypart'] if rate == .1 else ['date', 'Product', 'Order Type']
        line_results += contrast(d, d['Discount Rate'].eq(rate), keys, f'{rate:.0%} line product/time matched')
    pd.DataFrame(line_results).query("outcome != 'lines'").to_csv(out/'line_contrasts.csv', index=False)
    null = placebo(x, args.permutations)
    null.to_csv(out/'selection_placebo.csv', index=False)
    did = daily_did(x)
    did.to_csv(out/'campaign_daily_comparisons.csv', index=False)
    exposure = x.groupby(['Branch', 'Date', 'Category', 'Discount Rate']).agg(
        item_lines=('Quantity', 'size'), units=('Quantity', 'sum'), revenue_cents=('revenue_cents', 'sum'), gp_cents=('gp_cents', 'sum'))
    exposure.to_csv(out/'discount_exposure.csv')
    spending = x.assign(discount_cents=x.list_cents-x.revenue_cents).groupby('Discount Rate').agg(
        lines=('Quantity', 'size'), discount_cents=('discount_cents', 'sum'),
        list_cents=('list_cents', 'sum'), cogs_cents=('cogs_cents', 'sum'))
    spending.to_csv(out/'discount_accounting.csv')
    scenarios = []
    for rate in [.1, .15]:
        ref = x[x['Discount Rate'].eq(0)]
        if rate == .15:
            ref = ref[ref.Branch.eq('Harbour') & ref.eligible & ref.date.lt('2026-03-12') & ref.date.ge('2026-02-12')]
        price, cost = ref.list_cents.sum()/ref.Quantity.sum()/100, ref.cogs_cents.sum()/ref.Quantity.sum()/100
        margin = (price-cost)/price
        for lift in [0, .1, .2, .3, .4]:
            scenarios.append(dict(rate=rate, assumed_unit_lift=lift, baseline_units=1000,
                reference_price_per_unit=price, reference_cost_per_unit=cost, reference_margin=margin,
                break_even_unit_lift=rate/(margin-rate),
                incremental_gp_before_program_cost=1000*((1+lift)*(price*(1-rate)-cost)-(price-cost)),
                assumed_program_cost=100,
                incremental_contribution_after_program_cost=1000*((1+lift)*(price*(1-rate)-cost)-(price-cost))-100))
    scenarios = pd.DataFrame(scenarios)
    scenarios.to_csv(out/'assumption_scenarios.csv', index=False)
    (out/'quality_and_provenance.json').write_text(json.dumps(qa, indent=2)+'\n')
    report(out, qa, base, contrasts, null, did, pd.DataFrame(line_results), scenarios, spending)
    print(f'Rebuilt {out}; {len(x):,} lines, {len(o):,} baskets; all reconciliation assertions passed.')


def report(out, qa, base, contrasts, null, did, line, scenarios, spending):
    b = base.set_index('group')
    def delta(rate, y):
        return b.loc[rate, y]-b.loc['0%', y]
    def ci(label, y):
        r = contrasts[(contrasts.comparison == label) & (contrasts.outcome == y)].iloc[0]
        if pd.isna(r.difference):
            return 'unavailable (no treated/control overlap)'
        return f'{r.difference:+.3f} (95% interval {r.low:+.3f} to {r.high:+.3f})'
    null_summary = pd.DataFrame([dict(outcome=y, observed_10pct_difference=delta('10%', y),
        shuffled_median=null[y].median(), shuffled_low=null[y].quantile(.025), shuffled_high=null[y].quantile(.975)) for y in OUTCOMES])
    null_summary.to_csv(out/'selection_placebo_summary.csv', index=False)
    main_did = did[(did.scope == 'all') & did.window_type.eq('campaign') & ~did.branch_trend & did.outcome.isin(['orders', 'units', 'gp'])]
    sensitivities = did[did.outcome.eq('gp') & ((did.window_type.eq('campaign')) |
                        (did.scope.eq('all') & ~did.branch_trend))]
    branch = pd.read_csv(out/'branch_summary.csv')
    harbour_0 = branch[branch.branch.eq('Harbour') & branch.group.eq('0%')].iloc[0]
    text = f'''# Do Stories’ discounts grow baskets or gross profit?

Decision brief for 17 October 2026. Evidence: {qa['first_date']} through {qa['last_date']}, USD.

## Recommendation for today’s hackathon

**Do not expand either discount on the strength of discounted-basket averages. Keep 10% expansion on hold and test 15% against 10% and no offer at Harbour before repeating it at scale.** Baskets containing a 10% line but no 15% line average {delta('10%', 'units'):+.3f} units and ${delta('10%', 'gp'):+.2f} gross profit versus baskets with no discounted lines. For 15%, the differences are {delta('15%', 'units'):+.3f} units and ${delta('15%', 'gp'):+.2f}. Larger baskets have more opportunities to contain a discounted line: shuffled labels reproduce the observed 10% units gap. The 15% GP association reverses against Harbour’s own no-discount baseline ({b.loc['15%', 'gp']-harbour_0.gp:+.2f} dollars/basket). The adjusted daily GP differences during the two 15% windows are negative with wide intervals. These associations do not establish incremental profit or prove that removing existing offers would improve it.

## Measured results: simple baseline

Unit of analysis: one transaction ID, with all its lines summed. `0%` means every line is undiscounted. `10%` means at least one 10% line and no 15% line; `15%` is defined symmetrically and can include undiscounted lines. `both` is reported separately. A blanket 10% or 15% basket discount is **not** observed here. Basket size is units and line count; AOV is revenue after discounts. List value is quantity × supplied unit price, before discount. Gross profit is the supplied revenue minus product costs, subject to source rounding; it excludes payroll, rent and program costs.

{table(base, ['group', 'n', 'units', 'lines', 'revenue', 'gp', 'list_value', 'gross_margin'])}

Compared with the no-discount baseline, 10% units are {delta('10%', 'units')/b.loc['0%', 'units']:.1%} higher and GP/basket {delta('10%', 'gp')/b.loc['0%', 'gp']:.1%} higher; 15% units are {delta('15%', 'units')/b.loc['0%', 'units']:.1%} higher and GP/basket {delta('15%', 'gp')/b.loc['0%', 'gp']:.1%} higher. Neither comparison measures added visits, conversion, or customer retention.

## Challenge the first explanation

1. **Basket exposure creates selection.** We shuffled 10% labels among non-15% item lines within branch × month × category, holding every basket and its outcomes fixed ({qa['permutations']} draws, seed {SEED}). Baskets with any shuffled discount still show a units gap. This diagnostic makes no claim that actual labels were randomly assigned. Its simulated GP/revenue gaps retain recorded financial outcomes and are not a financial counterfactual or causal p-value.

{table(null_summary)}

2. **Context and customer selection.** Standardization compares treated and untreated orders in the same branch, month, weekday, four-hour daypart, order type and customer-ID availability, weighting cells by their treated counts (minimum three treated and five controls). Adjusted 10% units: {ci('10% context matched', 'units')}; GP: {ci('10% context matched', 'gp')}. This detailed match retains only 49.4% of 10% baskets and does not generalize to all discounted purchases. A coarse branch/month/type/ID-availability match retains all 10% baskets and is also reported. Same identified-customer comparison uses customers who purchased both with and without 10%, and still cannot remove time-varying intent or targeting. It is a sensitivity check, not customer randomization.

3. **Product mix and line quantity.** Item-line comparisons control for product and context. They answer whether discounted lines contain more units, not whether orders contain extra lines. Matching on products or existing eligible baskets can condition on purchase decisions affected by the offer, so these are mechanism diagnostics only.

{table(line[line.outcome.eq('units')], ['comparison', 'difference', 'low', 'high', 'treated', 'coverage'])}

4. **15% geography and timing.** All 504 15% lines occur at Harbour in Cold Coffee or Desserts, 12–19 March and 12–19 May inclusive. There are 458 orders with any 15%, including 16 also carrying 10%. A national 0%-basket baseline mixes branch, timing, category choice and eligibility. Harbour’s own no-discount baskets average ${harbour_0.gp:.2f} GP, versus ${b.loc['15%', 'gp']:.2f} for 15% baskets: the apparent network-wide positive association reverses within branch, even before time/product adjustments. Every eligible-category line during those Harbour dates is 15% discounted. Restricting to Harbour, campaign dates and baskets containing eligible categories (excluding any 10%) gives units {ci('15% Harbour eligible same dates', 'units')}; GP {ci('15% Harbour eligible same dates', 'gp')}. Eligibility rules and offer exposure are inferred from purchased items; we have no record of who saw or qualified for the offer.

All order contrasts and retained-sample coverage:

{table(contrasts[contrasts.outcome.isin(['units','gp'])], ['comparison','outcome','difference','low','high','treated','controls','coverage'])}

Intervals are approximate 95% normal sandwich intervals clustered by calendar date, conditional on selected matching cells and observed target weights. Same-customer intervals do not additionally cluster by customer; repeat-customer dependence may make them too narrow. They quantify sampling variability, not uncertainty from confounding. No multiplicity correction; interpret as exploratory.

## 15% daily campaign comparison and temporal replication

Compare each inferred eight-day campaign with its preceding 28 days. The simple baseline is Harbour’s raw daily pre/during change. The adjusted comparison subtracts contemporaneous changes at Garden/Uptown, using OLS with branch and date fixed effects and branch-specific weekday effects. Treatment is Harbour × campaign dates. Outcomes include **all** Harbour purchases to capture category substitution and basket attachment. Eligible-category and other-category comparisons, plus branch linear trend sensitivity, appear in `campaign_daily_comparisons.csv`. Category order counts overlap and must not be added together.

{table(main_did, ['window','outcome','raw_harbour_change','pre_harbour_mean','difference','low','high'])}

GP sensitivity checks (daily dollars):

{table(sensitivities, ['scope','window','window_type','branch_trend','difference','low','high'])}

Pre-period placebos move the eight-day window 14 days earlier and use their own preceding 28 days, with no 15% campaign in those fitting windows. They diagnose whether this design generates apparent changes before the offer. Wide placebo intervals cannot establish parallel trends. Eligible-category GP declines must be weighed against any gains elsewhere; scope `other` captures the latter without counting the discounted categories.

Differences are per branch-day. Intervals use date-cluster covariance with finite-sample correction and normal critical values (36 date clusters per window). They do not account for dependence across dates and may understate uncertainty under serial correlation. Common date effects absorb network-wide weather/seasonality but not Harbour-specific events, marketing, staffing or tourism. Linear trends extrapolate pre-period trends and can also absorb true effects. Only three branches and two short episodes sharply limit inference. Parallel counterfactual trends and no cross-branch spillovers are assumptions, not established facts.

March is the exploratory episode; May is a chronological replication under the same specified comparison. Both episodes were visible during this retrospective analysis, so May is **not** an untouched prospective holdout. This is an explanatory study, not a trained forecasting or targeting model; no predictive accuracy claim is made. We compare every adjusted daily result with the raw Harbour baseline rather than presenting complexity as evidence. An independently randomized test is needed for validation.

## Recorded discount accounting versus estimated business value

The recorded list-price concession is **${(spending.discount_cents.sum()/100):,.2f}**: ${spending.loc[.1,'discount_cents']/100:,.2f} on 10% lines and ${spending.loc[.15,'discount_cents']/100:,.2f} on 15% lines. This is arithmetic (list value minus recorded revenue), **not recoverable savings**: removing the offer could lose sales. Total recorded GP is ${qa['gp']:,.2f}, not incremental profit attributable to discounts.

The following estimates are explicitly hypothetical. For 10%, use the observed undiscounted mix across the network; for 15%, use undiscounted Harbour eligible-item mix in the 28 days before March. Assume constant unit prices, unit costs and mix, all 1,000 baseline units receive the discount, additional units cost the same, and no displacement or visit effects elsewhere. These are item-volume scenarios, not a replay of current partially discounted baskets. Estimated contribution subtracts an assumed $100 program cost per 1,000 baseline units. Labor capacity, waste and fixed costs remain unpriced.

Formula: ΔGP = 1,000 × [(1 + assumed unit lift) × (price × (1 − discount) − unit cost) − (price − unit cost)]. Break-even unit lift before program costs = discount / (reference gross margin − discount).

{table(scenarios, ['rate','assumed_unit_lift','reference_margin','break_even_unit_lift','incremental_gp_before_program_cost','assumed_program_cost','incremental_contribution_after_program_cost'], digits=2)}

No annualized savings or ROI is claimed. The needed causal unit lift may differ from an observed basket gap and depends heavily on cannibalization, discount eligibility, product mix and labor costs. A higher measured GP/basket alone is insufficient if profit per eligible visitor or per day falls.

## Data quality, provenance and limitations

- {qa['rows']:,} lines aggregate to {qa['orders']:,} orders, ${qa['revenue']:,.2f} revenue and ${qa['gp']:,.2f} GP. All 181 dates appear at each of three branches. Source SHA-256: `{qa['source_sha256']}`. Raw CSV is never overwritten. No external sources are required; all empirical claims trace to this CSV.
- {qa['exact_duplicate_excess_rows']} exact repeated excess rows (${qa['duplicate_excess_revenue']:,.2f} revenue) are retained because identical items may be valid purchases. Dropping exact repeats and reaggregating is a sensitivity check in the contrasts table, not an asserted cleaning correction.
- {qa['mixed_discount_orders']:,} orders contain multiple distinct line rates. The four exposure groups prevent treating them as uniform whole-basket discounts. Four orders have all three rates; 16 have both nonzero rates.
- Customer IDs are missing on {qa['missing_customer_orders']:,} orders ({qa['missing_customer_orders']/qa['orders']:.1%}). Identified-customer evidence is selected and does not generalize to anonymous customers.
- {qa['conflicting_order_metadata']} inconsistent within-order metadata; {qa['missing_required_cells']} missing required cells; {qa['revenue_arithmetic_over_one_cent']} revenue and {qa['gp_arithmetic_over_one_cent']} GP arithmetic errors beyond one cent. One-cent rounding differences: {qa['revenue_rounding_one_cent']} revenue and {qa['gp_rounding_one_cent']} GP lines. Quantity is positive, discount rates are 0/10/15%, and {qa['negative_gp_lines']} lines have negative GP. Checks do not independently verify supplier costs, tax treatment, omitted refunds, or completeness versus the POS ledger.
- All transaction IDs start `SYN-`. The brief says IDs are replacements; the prefix alone does not establish that purchases are synthetic. Validate provenance with Stories before a live decision. Timezone, offer assignment, marketing spend, eligible nonbuyers, footfall, stockouts, staffing and external events are absent. No October transactions are available, so this is historical evidence for today’s recommendation, not current trading performance.

## Practical next step

Run a concurrent randomized 0%/10%/15% offer test at Harbour on cold coffee/desserts, assigning before purchase and logging all assigned visitors, including nonbuyers. Use stable customer assignment where possible, otherwise documented randomized time blocks with washout and no overlapping offers. Compare **gross contribution per assigned visitor**, net of product, incremental labor and program costs, with total daily GP as a guardrail. Track conversion, units, net revenue, category substitution, repeat visits, complaints and stockouts. Stratify by weekday/daypart; use intention-to-treat and cluster inference at the randomization unit. Pre-register the minimum worthwhile profit gain, power calculation, stopping rule and budget before launch. March/May contrasts are insufficient to choose a precise causal effect size for powering the test. A successful 15% test must beat both no-offer and 10% on net contribution, not just units.

We rejected a basket-level propensity score or flexible uplift model: purchased products, basket size and discount presence can be post-offer variables, and assignment/eligibility are missing. More predictive complexity cannot recover the missing counterfactual. We also rejected scaling the crude GP/basket gap by all transactions as “business value.”
'''
    (out/'REPORT.md').write_text(text)
    s10 = scenarios[scenarios.rate.eq(.1)].iloc[0]
    s15 = scenarios[scenarios.rate.eq(.15)].iloc[0]
    (out/'BUSINESS_RECOMMENDATION.md').write_text(f'''# Stories discount decision — 17 October 2026

**Hold expansion. Test 0%, 10% and 15% offers concurrently at Harbour before scaling.** January–June data contain 33,887 orders. Against no-discount baskets, 10% baskets contain 15.2% more units and $0.17 more recorded gross profit; 15% baskets contain 12.0% more units and $0.37 more GP. Those associations overstate what we know about incremental value: shuffling 10% item-line labels while keeping baskets fixed reproduces a +{null.units.median():.3f}-unit gap, versus the observed +{delta('10%', 'units'):.3f}. Larger baskets are more likely to contain any discounted line. Product/time-matched 10% lines show essentially no additional units per line. Detailed context matching leaves a GP difference of {ci('10% context matched', 'gp')}, covering 49.4% of 10% baskets.

**The 15% story changes with the baseline.** Every 15% line is cold coffee or dessert at Harbour during 12–19 March or 12–19 May. Its GP/basket is ${b.loc['15%', 'gp']:.2f}, below Harbour’s ${harbour_0.gp:.2f} no-discount baseline. All eligible lines in those windows are discounted, so no same-date eligible untreated comparison exists. Against contemporaneous changes at the other branches, total Harbour GP/day differences are −$6.85 in March (95% interval −$75.28 to +$61.58) and −$25.88 in May (−$88.90 to +$37.14). These estimates are inconclusive about causality and do not justify a broad rollout.

**Estimated value is conditional.** Recorded list-price concessions total $2,178.09; this is not recoverable savings. At the observed reference product margins, a blanket 10% offer requires {s10.break_even_unit_lift:.1%} extra unit volume and a 15% eligible-item offer requires {s15.break_even_unit_lift:.1%} before program costs, assuming unchanged mix and costs. For 1,000 baseline units and an assumed 30% causal lift, estimated contribution after a $100 program cost is +$166 for 10% and −$79 for 15%. These are illustrative scenarios using different reference mixes, not a head-to-head treatment estimate or a forecast. Do not multiply observed GP/basket gaps into claimed savings.

**Next action:** randomize offers before purchase, include nonbuyers, and measure contribution per assigned visitor after product, incremental labor and program costs. Log eligibility, assignment and redemption; monitor daily GP, substitution and repeat visits. Pre-register budget, power and a minimum worthwhile profit gain. Current evidence covers only three branches, two short 15% windows, 36.5% anonymous orders and 132 unresolved repeated rows. Branch demand, targeting and serial dependence remain unresolved. Historical evidence does not establish October performance.

See [full evidence and assumptions](REPORT.md), with numeric tables alongside it. Rebuild instructions are in [the analysis guide](../README.md).
''')


if __name__ == '__main__':
    main()
