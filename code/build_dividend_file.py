#!/usr/bin/env python3

Per-day files: Raw/YYYY/YYYYMMDD_exdiv.csv  (Ticker, Close_ExDate)
Estimate Cash_Dividend from prev_close - Close_ExDate.

Output: D:/TWSE-Data/Raw/_combined_dividends.csv
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta


# Load ALL daily data for quick lookup
year_dirs = sorted(d for d in os.listdir(RAW_DIR) if d.isdigit())
dfs = []
for year in year_dirs:
    if os.path.exists(merged):
daily = pd.concat(dfs, ignore_index=True)

# Build ticker->[(date, close)] sorted lookup
ticker_map = {}
for _, row in daily.iterrows():
    if t not in ticker_map:
        ticker_map[t] = []

# For each ticker, sort by date
for t in ticker_map:
    ticker_map[t].sort(key=lambda x: x[0])


# Process per-day exdiv files
dividend_rows = []
no_price = 0
matched = 0

for year in year_dirs:
    year_dir = os.path.join(RAW_DIR, year)
    for fname in sorted(os.listdir(year_dir)):
            continue  # skip merged file, only per-day
        date_str = fname[:8]  # YYYYMMDD
        try:
        except:
            continue
        edf = pd.read_csv(os.path.join(year_dir, fname))
        for _, row in edf.iterrows():
            if t not in ticker_map:
                no_price += 1
                continue
            # Find prev trading day close
            pairs = ticker_map[t]
            prev_close = None
            for p_dt, p_close in reversed(pairs):
                if p_dt < dt:
                    prev_close = p_close
                    break
            if prev_close is None:
                no_price += 1
                continue
            cash_div = max(prev_close - ex_close, 0.0)
            if cash_div > 0:
                dividend_rows.append({
                })
                matched += 1
            # else: price went up on ex-div date, skip


if dividend_rows:
else:
