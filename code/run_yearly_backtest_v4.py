import os, sys, time, json, gc
import pandas as pd
import numpy as np
from indicators import macd_4arrows, macd, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

# Also log progress to a file

def log(msg):
    print(msg, flush=True)
    log_f.flush()

all_summary = []

for year in range(2004, 2027):
    t0 = time.time()
    if not os.path.exists(f):
        continue

    # Load + basic prep
    df = pd.read_parquet(f)

    load_t = time.time() - t0
    n_total = len(df)

    year_buys = 0
    year_sells = 0
    year_stocks = 0
    stocks_with_signal = []

        grp = grp.reset_index(drop=True)
        n = len(close)

        if n < 60:
            continue

        # --- Precompute all daily indicators (vectorized) ---
        close_s = pd.Series(close, index=range(n))
        high_s = pd.Series(high, index=range(n))
        low_s = pd.Series(low, index=range(n))

        m = macd_4arrows(close_s, fast=200, slow=209, signal=210)
        # also compute raw macd for other uses
        m_raw = macd(close_s, fast=200, slow=209, signal=210)

        dm = dmi(high_s, low_s, close_s, period=300)

        wr_arr = wr(high_s, low_s, close_s, 50).values
        rsi60_arr = rsi(close_s, 60).values

        # --- Weekly / Monthly indicators ---
        daily_df = pd.DataFrame({
        })

        w_vr, m_vr, m_pdi1, m_rsi4 = 0.0, 0.0, 0.0, 50.0

        }).dropna()
        }).dropna()

        if len(weekly) > 2:
            w_denom = w_bvs.replace(0, np.nan)
            w_vr = float((100.0 * w_avs / w_denom).iloc[-1]) if not w_denom.empty else 0.0

        if len(monthly) > 2:
            m_denom = m_bvs.replace(0, np.nan)
            m_vr = float((100.0 * m_avs / m_denom).iloc[-1]) if not m_denom.empty else 0.0

        if len(monthly) > 14:

        # --- Scan for buy/sell signals ---
        step = 30
        buys = 0
        sells = 0
        had_buy = False  # track if we are in a position (avoid repeated sells)
        signals = []

        start_i = min(100, n)
        for i in range(start_i, n, step):
            d4_val = float(d4[i]) if i < len(d4) and not np.isnan(d4[i]) else 0
            adx_val = float(adx_arr[i]) if i < len(adx_arr) and not np.isnan(adx_arr[i]) else 0
            adx_dir_val = float(adx_dir_arr[i]) if i < len(adx_dir_arr) else 0
            wr_val = float(wr_arr[i]) if i < len(wr_arr) and not np.isnan(wr_arr[i]) else 0
            rsi60_val = float(rsi60_arr[i]) if i < len(rsi60_arr) and not np.isnan(rsi60_arr[i]) else 50

            # BUY: C1 + C2 + C3 + at least 1 bonus from C4-C7
            c1 = d4_val >= 3
            c2 = adx_dir_val >= 0.5 and adx_val > 20
            c3 = wr_val < -20

            if c1 and c2 and c3:
                bonus = 0
                if rsi60_val > 57:
                    bonus += 1
                if not np.isnan(w_vr) and abs(w_vr - 150) < 50:
                    bonus += 1
                if not np.isnan(m_vr) and abs(m_vr - 150) < 50:
                    bonus += 1
                if m_pdi1 > 50 and m_rsi4 > 77:
                    bonus += 1

                if bonus >= 1:
                    buys += 1
                    had_buy = True
                    signals.append({
                    })

            # SELL: monthly RSI4 < 77 (only if we had a buy before)
            if had_buy and m_rsi4 < 77:
                sells += 1
                had_buy = False  # reset
                signals.append({
                })

        if signals:
            year_stocks += 1
            year_buys += buys
            year_sells += sells
            stocks_with_signal.append({
            })

    elapsed = time.time() - t0
    summary = {
    }
    all_summary.append(summary)

    # Save per-year signal data
    if stocks_with_signal:
            json.dump(stocks_with_signal, fout, indent=2)

    del df
    gc.collect()

# Save master summary
    json.dump(all_summary, f, indent=2)

for s in all_summary:

log_f.close()
