#!/usr/bin/env python3
import os, time
import numpy as np
import pandas as pd

os.makedirs(TEMP_DIR, exist_ok=True)

t0 = time.time()

# ── Step 1: Load all daily data ──
year_dirs = sorted(d for d in os.listdir(RAW_DIR) if d.isdigit())
dfs = []
for year in year_dirs:
    if os.path.exists(p):
daily = pd.concat(dfs, ignore_index=True)
daily.reset_index(drop=True, inplace=True)
n = len(daily)

# ── Step 2: Build exdiv dict ──
exdiv = {}
for year in year_dirs:
    yd = os.path.join(RAW_DIR, year)
    for fn in os.listdir(yd):
            continue
        ds = fn[:8]
        edf = pd.read_csv(os.path.join(yd, fn))
        for _, r in edf.iterrows():

# ── Step 3: Extract arrays ──

# ── Step 4: Process per ticker ──
adj_o = np.empty(n, dtype=np.float64)
adj_h = np.empty(n, dtype=np.float64)
adj_l = np.empty(n, dtype=np.float64)
adj_c = np.empty(n, dtype=np.float64)
adj_v = np.empty(n, dtype=np.float64)
cf    = np.empty(n, dtype=np.float64)

change_pts = np.where(tickers[1:] != tickers[:-1])[0] + 1
bounds = np.concatenate([[0], change_pts, [n]])
total = len(bounds) - 1

for gi in range(total):
    s, e = bounds[gi], bounds[gi + 1]
    evts = exdiv.get(tickers[s])
    m = e - s
    grp_cf = np.ones(m, dtype=np.float64)
    grp_c = closes[s:e]
    cum = 1.0
    for j in range(m - 1, -1, -1):
        grp_cf[j] = cum
        if evts and j > 0:
            ex_c = evts.get(ts_str)
            if ex_c is not None:
                prev_c = float(grp_c[j - 1])
                if prev_c > 0:
                    cum *= min(ex_c / prev_c, 1.0)
    adj_o[s:e] = opens[s:e] * grp_cf
    adj_h[s:e] = highs[s:e] * grp_cf
    adj_l[s:e] = lows[s:e] * grp_cf
    adj_c[s:e] = closes[s:e] * grp_cf
    adj_v[s:e] = (vols[s:e] * grp_cf).round(0)
    cf[s:e] = grp_cf

    if (gi + 1) % 2000 == 0 or gi == total - 1:

# ── Step 5: Write per-year temp files from arrays ──
# Use daily's Date column to find year boundaries
unique_years = np.unique(year_arr)
for yr in unique_years:
    mask = year_arr == yr
    idx = np.where(mask)[0]
    out = pd.DataFrame({
    })

# Cleanup big data
del daily, opens, highs, lows, closes, vols, adj_o, adj_h, adj_l, adj_c, adj_v, cf

# ── Step 6: Merge ──
temp_files = sorted(os.listdir(TEMP_DIR))
parts = [pd.read_parquet(os.path.join(TEMP_DIR, f)) for f in temp_files]
final = pd.concat(parts, ignore_index=True)
del parts

for f in temp_files:
    os.remove(os.path.join(TEMP_DIR, f))
os.rmdir(TEMP_DIR)

elapsed = time.time() - t0
