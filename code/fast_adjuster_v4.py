#!/usr/bin/env python3

Process: load all data + exdiv → per-ticker backward adjustment → per-year parquet → merge.
import os, time
import numpy as np
import pandas as pd

os.makedirs(TEMP_DIR, exist_ok=True)

t0 = time.time()

# ── Step 1: Load ALL daily data ──
year_dirs = sorted(d for d in os.listdir(RAW_DIR) if d.isdigit())
dfs = []
for year in year_dirs:
    if os.path.exists(p):
daily = pd.concat(dfs, ignore_index=True)
daily.reset_index(drop=True, inplace=True)

# ── Step 2: Build exdiv dict {ticker: {date_str: close_exdiv}} ──
exdiv = {}
for year in year_dirs:
    year_dir = os.path.join(RAW_DIR, year)
    for fname in os.listdir(year_dir):
            continue
        ds = fname[:8]
        edf = pd.read_csv(os.path.join(year_dir, fname))
        for _, r in edf.iterrows():
            exdiv.setdefault(t, {})[dt] = c

# ── Step 3: Pre-allocate output arrays ──
n = len(daily)

adj_open = np.empty(n, dtype=np.float64)
adj_high = np.empty(n, dtype=np.float64)
adj_low = np.empty(n, dtype=np.float64)
adj_close = np.empty(n, dtype=np.float64)
adj_vol = np.empty(n, dtype=np.float64)
cum_factors = np.empty(n, dtype=np.float64)

# ── Step 4: Process per ticker ──
change_pts = np.where(tickers[1:] != tickers[:-1])[0] + 1
bounds = np.concatenate([[0], change_pts, [n]])
total = len(bounds) - 1
proc_count = 0

for gi in range(total):
    s, e = bounds[gi], bounds[gi + 1]
    ticker = tickers[s]
    evts = exdiv.get(ticker)
    m = e - s

    grp_cf = np.ones(m, dtype=np.float64)
    grp_closes = closes[s:e]
    grp_dates = dates[s:e]
    cum = 1.0

    for j in range(m - 1, -1, -1):
        grp_cf[j] = cum
        if evts and ts_naive in evts and j > 0:
            ex_c = evts[ts_naive]
            prev_c = float(grp_closes[j - 1])
            if prev_c > 0:
                cum *= min(ex_c / prev_c, 1.0)

    adj_open[s:e] = opens[s:e] * grp_cf
    adj_high[s:e] = highs[s:e] * grp_cf
    adj_low[s:e] = lows[s:e] * grp_cf
    adj_close[s:e] = closes[s:e] * grp_cf
    cum_factors[s:e] = grp_cf

    proc_count += 1
    if proc_count % 2000 == 0:


# ── Step 5: Add columns and write per-year temp files ──

# Group by year and write each

# Cleanup large daily
del daily

# ── Step 6: Merge temp files ──
temp_files = sorted(os.listdir(TEMP_DIR))
parts = [pd.read_parquet(os.path.join(TEMP_DIR, f)) for f in temp_files]
final = pd.concat(parts, ignore_index=True)
del parts


# Cleanup
for f in temp_files:
    os.remove(os.path.join(TEMP_DIR, f))
os.rmdir(TEMP_DIR)

elapsed = time.time() - t0
size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
