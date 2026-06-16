#!/usr/bin/env python3

For each year, loads daily data + exdiv data. For each exdiv event,
finds the exact date by matching Close_ExDate within the same ticker's data,
then computes event factor from Close_ExDate / prev_close.

Output: D:/TWSE-Data/Adjusted/adjusted_all.parquet
import os, sys, time
import numpy as np
import pandas as pd

os.makedirs(ADJ_DIR, exist_ok=True)

t0 = time.time()
year_dirs = sorted(d for d in os.listdir(RAW_DIR) if d.isdigit())

# First pass: collect ALL exdiv events per ticker across all years
all_exdiv = {}  # ticker -> {date: close_exdiv}
for year in year_dirs:
    year_dir = os.path.join(RAW_DIR, year)
    for fname in sorted(os.listdir(year_dir)):
            continue
        date_str = fname[:8]
        edf = pd.read_csv(os.path.join(year_dir, fname))
        for _, row in edf.iterrows():
            if t not in all_exdiv:
                all_exdiv[t] = {}
            # Keep first (oldest) per date; some stocks have multiple entries same day
            if dt not in all_exdiv[t]:
                all_exdiv[t][dt] = c


# Second pass: process year by year
all_parts = []

for year in year_dirs:
    ty = time.time()
    if not os.path.exists(daily_path):
        continue

    df = pd.read_parquet(daily_path)

    n = len(df)
    cf = np.ones(n, dtype=np.float64)

    # Process per ticker
    ticker_count = 0

    for ticker, grp in ticker_groups:
        if ticker not in all_exdiv:
            continue

        exdiv_dict = all_exdiv[ticker]
        grp_idx = grp.index.values
        grp_dates = dates[grp_idx]
        grp_closes = closes[grp_idx]
        grp_cf = np.ones(len(grp_idx), dtype=np.float64)

        cum = 1.0
        for j in range(len(grp_idx) - 1, -1, -1):
            grp_cf[j] = cum
            ts = pd.Timestamp(grp_dates[j])
            if ts in exdiv_dict and j > 0:
                ex_close = exdiv_dict[ts]
                prev_close = float(grp_closes[j - 1])
                if prev_close > 0:
                    event_factor = min(ex_close / prev_close, 1.0)
                    cum *= event_factor

        cf[grp_idx] = grp_cf
        ticker_count += 1

    # Build output

    all_parts.append(out)
    t_elapsed = time.time() - ty

# Concatenate
final = pd.concat(all_parts, ignore_index=True)
del all_parts

elapsed = time.time() - t0
