#!/usr/bin/env python3
"""Add weather, air-quality, calendar and derived features to stories.sqlite.

Run after build_database.py. Adds three tables and one view, without touching
`transaction_lines`:
  context_daily   one row per date   (weather, air quality, calendar)
  context_hourly  one row per hour   (weather and air quality at that clock hour)
  line_features   one row per line_id (daypart, basket, customer-history, load)
  staffing_template  expected June baskets per branch × weekday × hour, with Poisson P90
  transactions_enriched  view joining all of them to `transactions`
Also writes stories_transactions_enriched.csv (raw records: keep private).
"""
import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pandas as pd
from src.analytics import load_data
from src.features import enrich, daily_weather, hourly_context, calendar, DAY_KEEP, branch_hour_panel, staffing_template

LINE_COLUMNS = ['daypart', 'product_type', 'is_drink', 'basket_lines', 'basket_units', 'basket_revenue',
                'basket_categories', 'basket_has_food', 'basket_has_drink', 'basket_discounted',
                'basket_food_and_drink', 'branch_hour_baskets', 'branch_day_baskets', 'customer_identified',
                'customer_visit_number', 'days_since_prev_visit', 'customer_new_branch', 'customer_repeat',
                'raining_now', 'dusty_now', 'after_sunset', 'minutes_from_sunset', 'iftar_window']

def sql_ready(d):
    """Booleans → 0/1, categories → text, timestamps → ISO text."""
    d = d.copy()
    for c in d:
        if pd.api.types.is_bool_dtype(d[c]): d[c] = d[c].astype(int)
        elif isinstance(d[c].dtype, pd.CategoricalDtype): d[c] = d[c].astype(str)
        elif pd.api.types.is_datetime64_any_dtype(d[c]): d[c] = d[c].dt.strftime('%Y-%m-%dT%H:%M')
        elif d[c].dtype == object and d[c].map(type).eq(bool).any():
            d[c] = d[c].map({True: 1, False: 0})  # nullable booleans (anonymous customers)
    return d

def build(database, source, csv_path):
    if not database.exists():
        raise SystemExit(f'{database} not found; run database/build_database.py first')
    x = load_data(source); e = enrich(x)
    days = daily_weather().merge(calendar(x.date), on='date', how='inner', validate='one_to_one')
    daily = sql_ready(days[DAY_KEEP + [c for c in days if c not in DAY_KEEP and c in calendar(x.date[:1])]])
    daily['date'] = days.date.dt.strftime('%Y-%m-%d')
    hourly = hourly_context()
    hourly = sql_ready(hourly.assign(date=hourly.datetime.dt.strftime('%Y-%m-%d'),
                                     hour=hourly.datetime.dt.hour).drop(columns='datetime'))
    lines = sql_ready(e[LINE_COLUMNS]); lines.insert(0, 'line_id', range(1, len(e)+1))
    with closing(sqlite3.connect(database)) as db:
        # line_id is the 1-based CSV row order used by build_database.py; confirm before joining.
        ids = [r[0] for r in db.execute('SELECT transaction_id FROM transaction_lines ORDER BY line_id')]
        if ids != x.transaction.tolist():
            raise ValueError('transaction_lines order differs from the CSV; rebuild the database')
        db.executescript('''DROP VIEW IF EXISTS transactions_enriched;
            DROP TABLE IF EXISTS context_daily; DROP TABLE IF EXISTS context_hourly; DROP TABLE IF EXISTS line_features;''')
        daily.to_sql('context_daily', db, index=False)
        hourly.to_sql('context_hourly', db, index=False)
        lines.to_sql('line_features', db, index=False)
        db.execute('DROP TABLE IF EXISTS staffing_template')
        staffing_template(branch_hour_panel(x), x).to_sql('staffing_template', db, index=False)
        db.executescript(HERE.joinpath('features_schema.sql').read_text())
        n, revenue = db.execute('SELECT COUNT(*), ROUND(SUM(line_revenue_usd), 2) FROM transactions_enriched').fetchone()
        assert n == len(x) and abs(revenue - round(x.revenue.sum(), 2)) < .005, (n, revenue)
        assert db.execute('SELECT COUNT(*) FROM transactions_enriched WHERE temp_mean IS NULL OR hour_temp IS NULL').fetchone()[0] == 0
        db.executescript(HERE.joinpath('feature_queries.sql').read_text())  # keep examples executable
        db.commit()
    print(f'Added context_daily ({len(daily)}), context_hourly ({len(hourly)}), line_features ({len(lines)}) '
          f'and view transactions_enriched to {database.name}')
    if csv_path:
        e.drop(columns=['datetime']).to_csv(csv_path, index=False)
        print(f'Wrote {csv_path.name}: {len(e):,} rows × {e.shape[1]-1} columns')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--database', type=Path, default=HERE/'stories.sqlite')
    p.add_argument('--source', type=Path, default=HERE.parent/'stories_transactions.csv')
    p.add_argument('--csv', type=Path, default=HERE.parent/'stories_transactions_enriched.csv')
    p.add_argument('--no-csv', action='store_true')
    a = p.parse_args(); build(a.database, a.source, None if a.no_csv else a.csv)
