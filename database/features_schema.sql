-- Created by add_features.py after the context tables are loaded.
-- Weather/air quality: one central-Beirut point for all branches (assumption).
CREATE UNIQUE INDEX idx_context_daily_date ON context_daily(date);
CREATE UNIQUE INDEX idx_context_hourly_slot ON context_hourly(date, hour);
CREATE UNIQUE INDEX idx_line_features_line ON line_features(line_id);

CREATE VIEW transactions_enriched AS
SELECT t.*,
       d.temp_mean, d.temp_max, d.temp_min, d.temp_range, d.feels_like, d.temp_anomaly,
       d.temp_change_vs_yesterday, d.rain_mm, d.rain_hours, d.rain_yesterday_mm, d.rain_last_3d_mm,
       d.dry_streak_days, d.rainy, d.heavy_rain, d.hot_day, d.windy, d.wind_max, d.sunshine_hours,
       d.daylight_hours, d.weather, d.temp_band, d.dust_max, d.pm10_mean, d.aqi_max, d.uv_max,
       d.dust_event, d.poor_air, d.holiday, d.holiday_name, d.holiday_eve, d.commercial_event,
       d.ramadan, d.payday_window, d.day_of_month, d.week_of_month, d.quarter, d.month_start,
       d.month_end, d.days_to_next_holiday, d.days_since_last_holiday, d.bridge_day, d.long_weekend,
       d.school_break, d.dst,
       h.hour_temp, h.hour_feels_like, h.hour_rain_mm, h.hour_humidity, h.hour_cloud_cover,
       h.hour_dew_point, h.hour_wind, h.hour_daylight, h.hour_weather, h.hour_pm10, h.hour_pm2_5,
       h.hour_dust, h.hour_aqi, h.hour_uv,
       f.daypart, f.product_type, f.is_drink, f.basket_lines, f.basket_units, f.basket_revenue,
       f.basket_categories, f.basket_has_food, f.basket_has_drink, f.basket_discounted,
       f.basket_food_and_drink, f.branch_hour_baskets, f.branch_day_baskets, f.customer_identified,
       f.customer_visit_number, f.days_since_prev_visit, f.customer_new_branch, f.customer_repeat,
       f.raining_now, f.dusty_now, f.after_sunset, f.minutes_from_sunset, f.iftar_window
FROM transactions t
JOIN context_daily d ON d.date = t.order_date
JOIN context_hourly h ON h.date = t.order_date AND h.hour = CAST(substr(t.order_time, 1, 2) AS INTEGER)
JOIN line_features f ON f.line_id = t.line_id;
