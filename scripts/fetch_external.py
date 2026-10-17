"""Download external context (Beirut weather, air quality) used to enrich transactions.

Open-Meteo historical archive (ERA5 reanalysis) and air-quality API (CAMS), no API key. Branch coordinates
are not in the source file, so one Greater Beirut point stands in for all
branches; this is an assumption, not an observed location.
Run: python scripts/fetch_external.py
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.analytics import ROOT

LATITUDE, LONGITUDE = 33.8938, 35.5018  # Beirut city centre (assumed for all branches)
DAILY = ['temperature_2m_max','temperature_2m_min','temperature_2m_mean','apparent_temperature_mean',
         'precipitation_sum','rain_sum','precipitation_hours','wind_speed_10m_max',
         'sunshine_duration','sunrise','sunset','weather_code']
HOURLY = ['temperature_2m','apparent_temperature','precipitation','relative_humidity_2m','cloud_cover',
          'weather_code','dew_point_2m','wind_speed_10m','is_day']
AIR = ['pm10','pm2_5','dust','us_aqi','uv_index']

def get(url, **params):
    query = urllib.parse.urlencode(dict(latitude=LATITUDE, longitude=LONGITUDE, timezone='Asia/Beirut', **params))
    with urllib.request.urlopen(f'{url}?{query}', timeout=60) as r:
        return json.load(r)

def fetch_air(start, end):
    payload = get('https://air-quality-api.open-meteo.com/v1/air-quality', start_date=start, end_date=end,
                  hourly=','.join(AIR))
    air = pd.DataFrame(payload['hourly']).rename(columns={'time':'datetime'})
    if air.isna().mean().max() > .05:
        raise ValueError('Air-quality archive has more than 5% missing hours')
    return air.ffill().bfill()  # rare model gaps carried from the neighbouring hour

def fetch(start, end):
    payload = get('https://archive-api.open-meteo.com/v1/archive', start_date=start, end_date=end,
                  daily=','.join(DAILY), hourly=','.join(HOURLY))
    daily = pd.DataFrame(payload['daily']).rename(columns={'time':'date'})
    hourly = pd.DataFrame(payload['hourly']).rename(columns={'time':'datetime'})
    if daily.drop(columns=['sunrise','sunset']).isna().any().any() or hourly.isna().any().any():
        raise ValueError('Weather archive returned gaps; retry later (ERA5 lags ~5 days)')
    return daily, hourly

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--start', default='2026-01-01'); p.add_argument('--end', default='2026-06-30')
    p.add_argument('--output', type=Path, default=ROOT/'data'/'external'); a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    daily, hourly = fetch(a.start, a.end)
    daily.to_csv(a.output/'weather_daily.csv', index=False)
    hourly.to_csv(a.output/'weather_hourly.csv', index=False)
    air = fetch_air(a.start, a.end); air.to_csv(a.output/'air_quality_hourly.csv', index=False)
    print(f'Wrote {len(daily)} days, {len(hourly)} weather hours and {len(air)} air-quality hours to {a.output}')
