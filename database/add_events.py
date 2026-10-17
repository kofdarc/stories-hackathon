#!/usr/bin/env python3
"""Add sourced competitor and market events to stories.sqlite and write an enriched CSV.

Run after build_database.py (and after add_features.py, if you use it; nothing it
creates is touched). Adds:
  competitor_events         one row per sourced competitor event
  market_events             one row per sourced war / ceasefire event
  event_days                one row per date with the day-level flags
  transactions_with_events  view: every transaction line plus its day's flags
Writes data/stories_transactions_with_events.csv (all source columns plus the flags).
"""
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import pandas as pd
from src.competitor_events import load_events, event_features

DB = HERE / 'stories.sqlite'
CSV = ROOT / 'data' / 'stories_transactions_with_events.csv'

VIEW = '''
CREATE VIEW transactions_with_events AS
SELECT t.*, e.competitor_new_entry_7d, e.days_since_competitor_entry,
       e.competitor_seasonal_offer, e.competitor_events_active, e.war_active,
       e.days_since_war_start, e.conflict_shock_day, e.conflict_shock_week,
       e.ceasefire_announced
FROM transactions t JOIN event_days e ON e.date = t.order_date;
'''


def main():
    comp, market = load_events()
    with sqlite3.connect(DB) as db:
        first, last = db.execute('SELECT MIN(order_date), MAX(order_date) FROM transaction_lines').fetchone()
        days = event_features(pd.date_range(first, last))
        days['date'] = days.date.dt.strftime('%Y-%m-%d')
        for frame in (comp, market):
            for c in ('start_date', 'end_date'):
                frame[c] = frame[c].dt.strftime('%Y-%m-%d')
        db.execute('DROP VIEW IF EXISTS transactions_with_events')
        comp.to_sql('competitor_events', db, index=False, if_exists='replace')
        market.to_sql('market_events', db, index=False, if_exists='replace')
        days.to_sql('event_days', db, index=False, if_exists='replace')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_event_days_date ON event_days(date)')
        db.executescript(VIEW)
        n_lines, revenue = db.execute('SELECT COUNT(*), SUM(line_revenue_cents) FROM transaction_lines').fetchone()
        enriched = pd.read_sql('SELECT * FROM transactions_with_events ORDER BY line_id', db)
    assert len(enriched) == n_lines, (len(enriched), n_lines)
    assert round(enriched.line_revenue_usd.sum() * 100) == revenue
    assert enriched[['war_active', 'competitor_seasonal_offer']].notna().all().all()
    CSV.parent.mkdir(exist_ok=True)
    enriched.to_csv(CSV, index=False)
    print(f'{len(comp)} competitor events, {len(market)} market events, {len(days)} event days')
    print(f'{CSV.relative_to(ROOT)}: {len(enriched):,} rows x {enriched.shape[1]} columns')


if __name__ == '__main__':
    main()
