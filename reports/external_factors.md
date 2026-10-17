# External factors — weather, holidays, Ramadan, payday

**Weather, air quality and holidays do not explain Stories' demand in this file, so they should not drive staffing or stock decisions yet.** After branch × weekday and trend controls, rain, heavy rain, temperature surprises, dust episodes, public holidays, holiday eves, bridge days, school breaks and Ramadan move daily baskets by at most a few percent, and each of those 95% intervals includes zero. Adding them to a forecast does not improve May–June accuracy (MAE 6.608 → 7.360 baskets per branch-day); the extra features overfit the four training months. The cold-drink share of drinks stays at 60.2%–60.9% as Beirut warms from 14.0°C (January mean) to 25.5°C (June). A real café's iced-drink share normally rises with heat, so a flat share points to a fixed menu mix or a simulated source (transaction IDs start with `SYN-`). Confirm with the data team before anyone builds weather-based planning.

## Features added (not in the source file)
81 columns, built by `src/features.py` from `data/external/`. They are stored in SQLite as `context_daily`, `context_hourly`, `line_features` and the `transactions_enriched` view (`database/add_features.py`).
- **Daily weather** (Open-Meteo ERA5): mean, max, min and feels-like temperature, daily range, change since yesterday, a 15-day temperature anomaly, rain mm and hours, yesterday's rain, 3-day rain, dry streak, rainy (≥1 mm), heavy-rain (≥10 mm), hot-day (≥30°C) and windy (≥40 km/h) flags, sunshine, daylight, WMO weather type.
- **Hourly weather at the transaction hour:** temperature, feels-like, rain, humidity, dew point, cloud, wind, daylight, weather type, raining-now.
- **Air quality** (Open-Meteo CAMS): hourly PM10, PM2.5, dust, US AQI and UV. Daily maxima, dust-event (≥50 µg/m³) and poor-air (AQI >100) flags, dusty-now.
- **Calendar:** Lebanese public holidays (lunar dates are estimates), holiday eves, days to the next holiday and since the last one, bridge days, long weekends, estimated school breaks, daylight-saving time, Valentine's and Mother's Day, Ramadan (est. 18 Feb–19 Mar 2026), the iftar window and minutes from sunset, payday window, day and week of month, month start and end, quarter.
- **Derived from the transactions:** daypart, product type (hot drink, cold drink, food), basket size, value and category count, food + drink basket, discounted basket, baskets at the same branch in the same hour and on the same day, and customer visit number, days since previous visit, first visit to that branch and repeat flag. History uses only earlier visits.

## Evidence
Log-linear model of daily baskets per branch with branch × weekday effects, a linear trend and week-clustered standard errors (`tables/external_effects_baskets.csv`; revenue version alongside):

| Feature | Change in baskets | Days |
|---|---|---|
| rainy | -0.8% (95% CI -4.0% to +2.5%) | 63 |
| heavy_rain | +1.1% (95% CI -2.8% to +5.2%) | 16 |
| temp_anomaly | -0.3% (95% CI -1.1% to +0.5%) |  |
| dust_event | +1.8% (95% CI -1.9% to +5.6%) | 33 |
| holiday | -2.2% (95% CI -6.9% to +2.8%) | 16 |
| holiday_eve | +0.0% (95% CI -5.4% to +5.7%) | 13 |
| bridge_day | -3.6% (95% CI -12.4% to +6.1%) | 6 |
| school_break | -0.2% (95% CI -3.4% to +3.1%) | 34 |
| ramadan | +1.4% (95% CI -2.4% to +5.3%) | 30 |
| payday_window | +4.0% (95% CI +1.8% to +6.2%) | 36 |

- **Holdout:** training Jan–Apr, testing May–Jun, the context features leave MAE at 7.360 vs 6.608 for the baseline (`tables/external_holdout.csv`).
- **Month-turn lift (weak, hypothesis only):** the payday window shows +4.0% (95% CI +1.8% to +6.2%). A placebo test over all 31 six-day windows puts days 1–6 highest. That window was chosen after looking at the data. It estimates +9.3% (95% CI +5.1% to +13.7%) in Jan–Apr but only +2.8% (95% CI +0.9% to +4.7%) in May–Jun, and April reverses (`tables/month_turn_placebo.csv`). Treat it as a staffing hypothesis to retest, not an effect to bank.
- **Rain at the transaction hour:** within-month dine-in share changes by -3.4 percentage points (day-bootstrap CI -6.0 to -1.1). The change gets smaller as rain gets heavier, so it may be noise (`tables/rain_dine_in.csv`).
- **Ramadan:** no level shift. Because the hourly basket profile does not move toward iftar, the timing data look insensitive to it, which is another realism flag.

## Assumptions and limits
Branch locations are not given. One central-Beirut weather point stands in for Garden, Harbour and Uptown. ERA5 is reanalysis on a ~9–25 km grid, not a station at the door. Lunar holiday dates may be off by a day. Six months gives only 16 holiday days and 16 heavy-rain days, so small effects (under ~5%) cannot be ruled out. The trend is linear in log baskets. These are associations, not causal effects.

## Decision
Do not buy weather feeds or build weather-driven staffing on this evidence. If Stories' real POS data show weather sensitivity, rerun `scripts/run_analysis.py` on that data; the pipeline and holdout test are ready. Retest the month-start lift on the next quarter before using it for rosters.
