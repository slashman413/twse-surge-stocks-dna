#!/usr/bin/env python3
import os, sys, time
import numpy as np
import pandas as pd


def main():
    t0 = time.time()

    # ── Load yearly merged files ──
    year_dirs = sorted(d for d in os.listdir(RAW_DIR) if d.isdigit())
    dfs = []
    for year in year_dirs:
        if os.path.exists(merged):
            dfs.append(pd.read_parquet(merged))
    if not dfs:
        return
    daily = pd.concat(dfs, ignore_index=True)

    # ── Load dividend events ──
    if os.path.exists(div_file):
        events = pd.read_csv(div_file)
    else:
        return

    # ── Filter tickers with/without dividend events ──
    no_div = ~has_div

    # Process tickers with dividends
    result.reset_index(drop=True, inplace=True)

    adj_open = np.empty(len(result), dtype=np.float64)
    adj_high = np.empty(len(result), dtype=np.float64)
    adj_low = np.empty(len(result), dtype=np.float64)
    adj_close = np.empty(len(result), dtype=np.float64)
    adj_volume = np.empty(len(result), dtype=np.float64)
    cum_factors = np.empty(len(result), dtype=np.float64)

    n_tickers = len(tickers)

    for i, ticker in enumerate(tickers):
        idx = np.where(mask)[0]


        # Compute cumulative factors (backward)
        n = len(closes)
        cf = np.ones(n, dtype=np.float64)
        cum = 1.0
        event_map = {}
        for _, row in ticker_events.iterrows():

        for j in range(n - 1, -1, -1):
            cf[j] = cum
            evt = event_map.get(pd.Timestamp(dates[j]))
            if evt is not None and j > 0:
                d_cash, d_stock = evt
                prev_close = float(closes[j - 1])
                if not np.isnan(prev_close) and prev_close > 0:
                    denom = 1.0 + d_stock / 1000.0
                    ref_price = (prev_close - d_cash) / denom
                    event_factor = min(ref_price / prev_close, 1.0)
                    cum *= event_factor


        adj_open[idx] = opens * cf
        adj_high[idx] = highs * cf
        adj_low[idx] = lows * cf
        adj_close[idx] = closes * cf
        adj_volume[idx] = vols * cf
        cum_factors[idx] = cf

        if (i + 1) % 200 == 0 or i == n_tickers - 1:
            pct = (i + 1) * 100 // n_tickers
            elapsed = time.time() - t0


    # ── Include non-dividend tickers (CumFactor = 1.0) ──

    final = pd.concat([result, nodiv_df], ignore_index=True)
    final.reset_index(drop=True, inplace=True)

    # ── Save ──
    elapsed = time.time() - t0

    main()
