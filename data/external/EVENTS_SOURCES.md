# Competitor and market events, January to June 2026

Every row in `competitor_events_2026.csv` and `market_events_2026.csv` is a real, dated
event with a source URL. Nothing is simulated. `src/competitor_events.py` turns them into
day-level features and tests them against daily baskets.

## What was found

| File | Events | Notes |
| --- | --- | --- |
| `competitor_events_2026.csv` | 3 | Stashh opening (6 Feb), Café Najjar Raqwa Q2 launch (11 Feb), Ramadan iftar offers across about 40 Beirut venues |
| `market_events_2026.csv` | 8 | 2026 Lebanon war start (2 Mar), Beirut strikes, ceasefire milestones (16 Apr to 19 Jun) |

`date_confidence` records how sure each date is. Two need checking before anyone relies on them:
- **Stashh:** the source gives "Feb. 6" without a year. The year is inferred from the article's recency.
- **Café Najjar:** the 11 Feb date comes from search coverage of the launch. The original article could not be opened from this environment.

## Searched for, not found or out of window

- **Dunkin' Lebanon:** every 2026 Dunkin' promotion found was a US campaign, some in US towns named Lebanon.
- **Starbucks (Alshaya), Costa, Barista, Tim Hortons, Caribou, Krispy Kreme:** no Lebanon-specific 2026 event found.
- **Dancing Goat Coffee (Saifi), late September 2026, and HUMN, July 2026:** both are after the data ends.
- **IZZYY second branch, August 2026:** also after the data ends.
- **EL&N Beirut:** the report is older and gives no confirmed opening date.

Brand-run promotions are mostly posted on Instagram, which search engines index poorly. Stories'
marketing team will know its rivals' campaign calendar far better than public sources do.

## Features (`event_features`)

| Feature | Meaning |
| --- | --- |
| `competitor_new_entry_7d` | Within 7 days of a competitor store opening or product launch |
| `days_since_competitor_entry` | Days since the latest such event |
| `competitor_seasonal_offer` | Competitor Ramadan iftar offers running (estimated 18 Feb to 19 Mar) |
| `competitor_events_active` | Count of competitor events active that day |
| `war_active`, `days_since_war_start` | From 2 March 2026. The end date is open; 30 June is used |
| `conflict_shock_day`, `conflict_shock_week` | The day of, and 7 days from, the 12 March Beirut seafront strike and the 8 April strikes |
| `ceasefire_announced` | On or after 16 April 2026 |

All events are market-wide. Branch locations are not in the transaction file, so no event
is tied to a branch.

## Effect on daily baskets

The model is log daily baskets per branch with branch × weekday effects and a branch trend.
Each flag is tested alone, with week-clustered 95% intervals.

| Feature | Change | 95% CI | Days |
| --- | --- | --- | --- |
| competitor_new_entry_7d | +0.6% | -4.7% to +6.2% | 12 |
| competitor_seasonal_offer | +1.5% | -2.5% to +5.6% | 30 |
| war_active | +4.0% | -2.5% to +10.9% | 121 |
| conflict_shock_week | -4.4% | -7.8% to -0.9% | 18 |
| ceasefire_announced | -3.6% | -8.8% to +2.0% | 76 |

- **No competitor effect.** Neither the openings nor the rival Ramadan offers moved Stories' baskets.
- **The conflict-week dip is not distinguishable from chance.** In a placebo test, 400 random
  pairs of 7-day windows gave a dip at least this large 9.5% of the time. It is also one of five
  tests, and the 12 to 18 March week overlaps the 15% campaign window.
- **The war is the bigger finding.** Lebanon's restaurant and café syndicate said the sector grew
  25% in January and February and that the 2 March fighting erased that gain. It projected a
  further 60-70% decline, according to the
  [InfoPro 2026 war-impact survey](https://leadersclub.com.lb/reports/War-Impact-&-Business-Forecast.pdf).
  In this file, baskets per day rose 10.1% in March and kept growing every month of the war,
  with no break at 2 March. Either the file is not real trading data (transaction IDs start
  with `SYN-`), or these branches were far outside the conflict's reach. That is worth putting
  to Stories before any forecast built on this file is used.

Reproduce:

```sh
python3 src/competitor_events.py
```
