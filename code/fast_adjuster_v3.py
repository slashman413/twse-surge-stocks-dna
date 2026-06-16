#!/usr/bin/env python3

Processes year by year (memory efficient), builds exdiv event dict from per-day files.
Computes event factor from Close_ExDate / prev_close ratio.
import os, sys, time
import numpy as np
import pandas as pd
from pathlib import Path

os.makedirs(ADJ_DIR, exist_ok=True)

t0 = time.time()

# ── Step 1: Load ALL ex-div events across all years ──
exdiv = {}  # ticker -> {date_str -> close_val}
years = sorted(d for d in os.listdir(RAW_DIR) if d.isdigit())
for year in years:
    year_dir = os.path.join(RAW_DIR, year)
    for fname in os.listdir(year_dir):
            continue
        ds = fname[:8]
        edf = pd.read_csv(os.path.join(year_dir, fname))
        for _, row in edf.iterrows():
            if t not in exdiv:
                exdiv[t] = {}
            if dt not in exdiv[t]:
                exdiv[t][dt] = c

total_events = sum(len(v) for v in exdiv.values())

# ── Step 2: Process year by year ──
os.makedirs(temp_dir, exist_ok=True)
temp_files = []

for year in years:
    ty = time.time()
    if not os.path.exists(daily_path):
        continue

    df = pd.read_parquet(daily_path)

    # Prepare arrays
    cf = np.ones(len(df), dtype=np.float64)

    # Find group boundaries for each ticker
    # ticker changes: where ticker[i] != ticker[i-1]
    change_points = np.where(tickers[1:] != tickers[:-1])[0] + 1
    boundaries = np.concatenate([[0], change_points, [len(tickers)]])

    for gi in range(len(boundaries) - 1):
        start, end = boundaries[gi], boundaries[gi + 1]
        ticker = tickers[start]
        if ticker not in exdiv:
            continue

        evts = exdiv[ticker]  # {date_str: close_val}
        n = end - start
        grp_cf = np.ones(n, dtype=np.float64)
        grp_dates = dates[start:end]
        grp_closes = closes[start:end]

        cum = 1.0
        for j in range(n - 1, -1, -1):
            grp_cf[j] = cum
            ts = pd.Timestamp(grp_dates[j])
            if ts_str in evts and j > 0:
                ex_close = evts[ts_str]
                prev_close = float(grp_closes[j - 1])
                if prev_close > 0:
                    event_factor = min(ex_close / prev_close, 1.0)
                    cum *= event_factor

        cf[start:end] = grp_cf

    # Build output

    temp_files.append(temp_path)


# ── Step 3: Merge all temp files ──
parts = [pd.read_parquet(f) for f in temp_files]
final = pd.concat(parts, ignore_index=True)
del parts


# Cleanup temp
for f in temp_files:
    os.remove(f)
os.rmdir(temp_dir)

elapsed = time.time() - t0
