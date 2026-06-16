import os, sys, time, json, gc
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed


os.makedirs(OUT_DIR, exist_ok=True)


def process_year(year):
    t0 = time.time()
    if not os.path.exists(f):
        return None
    
    # Import inside worker to avoid pickling issues
    import pandas as pd
    import numpy as np
    import sys
    from indicators import macd, macd_4arrows, dmi, wr, rsi
    from strategy import _safe_last

    df = pd.read_parquet(f)

    load_t = time.time() - t0
    n_total = len(df)

    year_buys = sum_buys = sum_sells = year_stocks = 0
    stocks_with_signal = []

        grp = grp.reset_index(drop=True)
        n = len(close)

        if n < 100:
            continue

        close_s = pd.Series(close, index=range(n))
        high_s = pd.Series(high, index=range(n))
        low_s = pd.Series(low, index=range(n))

        m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

        dm = dmi(high_s, low_s, close_s, period=300)

        wr_arr = wr(high_s, low_s, close_s, 50).values
        rsi60_arr = rsi(close_s, 60).values

        # Weekly / Monthly (per ticker)
        daily_df = pd.DataFrame({
        })
        }).dropna()
        }).dropna()

        w_vr = 0.0
        if len(weekly) > 2:
            w_denom = w_bvs.replace(0, np.nan)
            w_vr = float((100.0 * w_avs / w_denom).iloc[-1]) if not w_denom.empty else 0.0

        m_vr = 0.0
        if len(monthly) > 2:
            m_denom = m_bvs.replace(0, np.nan)
            m_vr = float((100.0 * m_avs / m_denom).iloc[-1]) if not m_denom.empty else 0.0

        m_pdi1 = 0.0
        m_rsi4 = 50.0
        if len(monthly) > 14:

        # Scan for signals
        step = 30
        start_i = min(100, n)
        buys = sells = 0
        had_buy = False
        signals = []

        for i in range(start_i, n, step):
            d4_val = float(d4[i]) if i < len(d4) and not np.isnan(d4[i]) else 0
            adx_val = float(adx_arr[i]) if i < len(adx_arr) and not np.isnan(adx_arr[i]) else 0
            wr_val = float(wr_arr[i]) if i < len(wr_arr) and not np.isnan(wr_arr[i]) else 0
            rsi60_val = float(rsi60_arr[i]) if i < len(rsi60_arr) and not np.isnan(rsi60_arr[i]) else 50

            c1 = d4_val >= 3
            c2 = adx_val > 20
            c3 = wr_val < -20

            if c1 and c2 and c3:
                bonus = 0
                if rsi60_val > 57: bonus += 1
                if not np.isnan(w_vr) and abs(w_vr - 150) < 50: bonus += 1
                if not np.isnan(m_vr) and abs(m_vr - 150) < 50: bonus += 1
                if m_pdi1 > 50 and m_rsi4 > 77: bonus += 1

                if bonus >= 1:
                    buys += 1
                    had_buy = True

            if had_buy and m_rsi4 < 77:
                sells += 1
                had_buy = False

        if signals:
            year_stocks += 1
            sum_buys += buys
            sum_sells += sells

    elapsed = time.time() - t0
    summary = {
    }

    # Save per-year signal data
    if stocks_with_signal:
            json.dump(stocks_with_signal, fout, indent=2)


    del df
    gc.collect()
    return summary


def main():
    years = list(range(2004, 2027))
    all_summary = []

    # Phase 1: small years (2004-2010) run sequentially on 2 workers
    # Phase 2: big years run 2 at a time
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_year, y): y for y in years}
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_summary.append(result)


    # Save master summary
        json.dump(all_summary, f, indent=2)

    for s in all_summary:


    return all_summary


    main()
