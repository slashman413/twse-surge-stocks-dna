import os, sys, time, json, gc
import pandas as pd
import numpy as np
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_CAPITAL = 1_000_000  # 100萬初始資金

def process_year(year):
    t0 = time.time()
    if not os.path.exists(f):
        return None

    df = pd.read_parquet(f)

    # Drop rows with NaN prices
        df = df[df[col].notna()]

    n_total = len(df)

    year_trades = []
    year_pl = 0.0
    year_pl_pct = 0.0
    total_invested = 0.0
    trade_count = 0

        grp = grp.reset_index(drop=True)
        n = len(close)

        if n < 100:
            continue

        close_s = pd.Series(close, index=range(n))
        high_s = pd.Series(high, index=range(n))
        low_s = pd.Series(low, index=range(n))

        # Indicators
        m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

        dm = dmi(high_s, low_s, close_s, period=300)

        wr_arr = wr(high_s, low_s, close_s, 50).values
        rsi60_arr = rsi(close_s, 60).values

        # Weekly/Monthly indicators (for bonus/sell checks)
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

        # --- Scan for buy/sell signals ---
        step = 30
        start_i = min(100, n)
        buy_price = None
        buy_date = None
        buy_idx = None

        trades = []

        for i in range(start_i, n, step):
            # Skip NaN prices
            if np.isnan(close[i]) or np.isnan(high[i]) or np.isnan(low[i]):
                continue

            d4_val = float(d4[i]) if i < len(d4) and not np.isnan(d4[i]) else 0
            adx_val = float(adx_arr[i]) if i < len(adx_arr) and not np.isnan(adx_arr[i]) else 0
            wr_val = float(wr_arr[i]) if i < len(wr_arr) and not np.isnan(wr_arr[i]) else 0
            rsi60_val = float(rsi60_arr[i]) if i < len(rsi60_arr) and not np.isnan(rsi60_arr[i]) else 50

            c1 = d4_val >= 3
            c2 = adx_val > 20
            c3 = wr_val < -20

            # === SELL check (if in position, check at NEXT sample point) ===
            if buy_price is not None and buy_idx is not None:
                # Sell conditions (checked at current sample point):
                sell = False

                # 1. Monthly RSI4 < 77 (sell 50% trailing)
                if m_rsi4 < 77:
                    sell = True

                # 2. Price dropped below MA60 (stop-loss style)
                # (already have rsi60 and wr for reference)

                if sell:
                    sell_price = close[i]
                    pl = sell_price - buy_price
                    pl_pct = (pl / buy_price) * 100
                    trades.append({
                    })
                    buy_price = None
                    buy_date = None
                    buy_idx = None

            # === BUY check (only if not already in position) ===
            if buy_price is None and c1 and c2 and c3:
                bonus = 0
                if rsi60_val > 57: bonus += 1
                if not np.isnan(w_vr) and abs(w_vr - 150) < 50: bonus += 1
                if not np.isnan(m_vr) and abs(m_vr - 150) < 50: bonus += 1
                if m_pdi1 > 50 and m_rsi4 > 77: bonus += 1

                if bonus >= 1:
                    buy_price = close[i]
                    buy_idx = i

        # If still in position at year end, close at last price
        if buy_price is not None:
            sell_price = close[-1]
            pl = sell_price - buy_price
            pl_pct = (pl / buy_price) * 100
            trades.append({
            })

        if trades:
            year_trades.extend(trades)
            for t in trades:
                trade_count += 1

    elapsed = time.time() - t0
    # Average return per trade
    avg_pl_pct = 0.0
    if trade_count > 0 and total_invested > 0:
        avg_pl_pct = round((year_pl / total_invested) * 100, 2)

    summary = {
    }

    # Save per-year trade details
    if year_trades:
            json.dump(year_trades, fout, indent=2)


    del df
    gc.collect()
    return summary


def main():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    years = list(range(2004, 2027))
    all_summary = []

    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_year, y): y for y in years}
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_summary.append(result)


        json.dump(all_summary, f, indent=2)

    total_pl = 0
    for s in all_summary:

    lf.close()
    return all_summary


    main()
