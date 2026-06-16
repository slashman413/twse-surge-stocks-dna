import os, sys, json, gc
import pandas as pd
import numpy as np

from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last
from run_yearly_backtest_v12 import fix_bad_data, load_market_data, compute_market_signals, compute_stock_signals

os.makedirs(OUT_DIR, exist_ok=True)

CUR_YEAR = 2026
TOP_N = 20
KLINE_DAYS = 120

def build_kline_data(grp, target_year, ticker):
    grp = grp.reset_index(drop=True)
    n = len(close)

    if n < 200:
        return None

    close, high, low, volume = fix_bad_data(close, high, low, volume)
    close = np.nan_to_num(close, nan=0.0)
    high = np.nan_to_num(high, nan=0.0)
    low = np.nan_to_num(low, nan=0.0)
    volume = np.nan_to_num(volume, nan=0.0)

    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    ma20 = pd.Series(close).rolling(20).mean().values
    ma50 = pd.Series(close).rolling(50).mean().values
    vol_ma20 = pd.Series(volume).rolling(20).mean().values
    rsi14_arr = np.nan_to_num(rsi(close_s, 14).values, nan=50)
    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)

    dm = dmi(high_s, low_s, close_s, period=300)

    # Monthly signals

    m_rsi4 = 50.0
    m_adx1 = 0.0
    if len(monthly) > 14:

    # Build K-line rows for target year
    kline_data = []
    for i in range(n):
        dt = pd.Timestamp(dates[i])
        if dt.year != target_year and i < n - 1 and pd.Timestamp(dates[i+1]).year != target_year:
            continue
        if close[i] == 0:
            continue

        # Only last KLINE_DAYS of target year
        if len(kline_data) > KLINE_DAYS and dt.year == target_year:
            # Already have enough, but keep collecting until end
            pass

        dist_ma20 = ((close[i] - ma20[i]) / ma20[i] * 100) if ma20[i] > 0 else 0
        dist_ma50 = ((close[i] - ma50[i]) / ma50[i] * 100) if ma50[i] > 0 else 0

        kline_data.append({
        })

    # Trim to last KLINE_DAYS + warmup
    warmup_data = warmup_data[-30:] if len(warmup_data) > 30 else warmup_data  # up to 30 warmup

    return {
    }


NAME_CACHE = None

def name_lookup(ticker):
    global NAME_CACHE
    if NAME_CACHE is None:
        import requests
        try:
        except:
            NAME_CACHE = {}


def main():
    if not os.path.exists(f):
        return

    warmup_df = None
    if os.path.exists(warmup_path):
        warmup_df = pd.read_parquet(warmup_path)
            warmup_df = warmup_df[warmup_df[col].notna()]

    df = pd.read_parquet(f)
        df = df[df[col].notna()]

    if warmup_df is not None:
        df = pd.concat([warmup_df, df], ignore_index=True)


    mkt = load_market_data(CUR_YEAR)
    mkt_signals = compute_market_signals(mkt, CUR_YEAR)
    if not mkt_signals:
        return

    # Check latest market condition
    last_mkt_date = max(mkt_signals.keys())
    last_mkt = mkt_signals[last_mkt_date]

    # Compute stock signals
    stock_sigs = {}
    price_lookup = {}

    valid_tickers = ticker_counts[ticker_counts >= 200].index

        t_str = str(ticker).zfill(4)
        if t_str[:2] in ('00', '01', '02', '03', '04', '05', '06', '07', '08') or len(t_str) != 4:
            continue
        result = compute_stock_signals(grp, CUR_YEAR)
        if result:
            t, sigs, prices = result
            stock_sigs[t] = sigs
            if prices:
                price_lookup[t] = prices


    # Collect latest signal per stock
    signal_list = []
    for ticker, sigs in stock_sigs.items():
        latest_date = max(sigs.keys())
        sig = sigs[latest_date]
        signal_list.append({
        })

    # Sort by score descending
    top_signals = signal_list[:TOP_N]

    for i, s in enumerate(top_signals):

    # Build K-line data for top signals
    kline_data = {}
    # Re-scan groups for K-line data
        t_str = str(ticker).zfill(4)
        if t_str[:2] in ('00', '01', '02', '03', '04', '05', '06', '07', '08') or len(t_str) != 4:
            continue
        t = str(ticker).zfill(4)
            kd = build_kline_data(grp, CUR_YEAR, t)
            if kd:
                kline_data[t] = kd


    # Save signals
    output = {
    }

        json.dump(output, fout, indent=2, ensure_ascii=False)

        json.dump(kline_data, fout, indent=2, ensure_ascii=False)

    del df; gc.collect()


    main()
