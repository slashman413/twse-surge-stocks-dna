import os, sys, time, json, gc, math
import pandas as pd
import numpy as np
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_CAPITAL = 1_000_000
FIXED_ALLOCATION = 100_000  # 每筆固定 10 萬，不隨跨股現金變動


def process_year(year):
    t0 = time.time()
    if not os.path.exists(f):
        return None

    df = pd.read_parquet(f)

        df = df[df[col].notna()]

    n_total = len(df)

    trades = []
    year_pl = 0.0
    equity_curve = []

        grp = grp.reset_index(drop=True)
        n = len(close)

        if n < 100:
            continue

        close = np.nan_to_num(close, nan=0.0)
        high = np.nan_to_num(high, nan=0.0)
        low = np.nan_to_num(low, nan=0.0)

        # Per-ticker independent budget
        ticker_cash = FIXED_ALLOCATION
        ticker_pl = 0.0

        close_s = pd.Series(close, index=range(n))
        high_s = pd.Series(high, index=range(n))
        low_s = pd.Series(low, index=range(n))

        m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

        dm = dmi(high_s, low_s, close_s, period=300)

        wr_arr = np.nan_to_num(wr(high_s, low_s, close_s, 50).values, nan=0)
        rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)

        daily_df = pd.DataFrame({
        })
        }).dropna()
        }).dropna()

        w_vr = 0.0
        if len(weekly) > 2:
            w_denom = w_bvs.replace(0, np.nan)
            w_vr = float(np.nan_to_num((100.0 * w_avs / w_denom).iloc[-1], nan=0.0)) if not w_denom.empty else 0.0

        m_vr = 0.0
        if len(monthly) > 2:
            m_denom = m_bvs.replace(0, np.nan)
            m_vr = float(np.nan_to_num((100.0 * m_avs / m_denom).iloc[-1], nan=0.0)) if not m_denom.empty else 0.0

        m_pdi1 = 0.0
        m_rsi4 = 50.0
        if len(monthly) > 14:

        step = 30
        start_i = min(100, n)
        position_shares = 0
        position_buy_price = None
        position_buy_date = None

        for i in range(start_i, n, step):
            if close[i] == 0.0:
                continue

            d4_val = float(d4[i])
            adx_val = float(adx_arr[i])
            wr_val = float(wr_arr[i])
            rsi60_val = float(rsi60_arr[i])

            # Sell check
            if position_shares > 0:
                sell_flag = False
                if m_rsi4 < 77:
                    sell_flag = True

                if sell_flag:
                    sell_price = close[i]
                    proceeds = position_shares * sell_price
                    pl = proceeds - (position_shares * position_buy_price)
                    ticker_cash += proceeds
                    trades.append({
                    })
                    equity_curve.append({
                    })
                    year_pl += pl
                    position_shares = 0
                    position_buy_price = None
                    position_buy_date = None

            # Buy check
            if position_shares == 0 and d4_val >= 3 and adx_val > 20 and wr_val < -20:
                bonus = 0
                if rsi60_val > 57: bonus += 1
                if not np.isnan(w_vr) and abs(w_vr - 150) < 50: bonus += 1
                if not np.isnan(m_vr) and abs(m_vr - 150) < 50: bonus += 1
                if m_pdi1 > 50 and m_rsi4 > 77: bonus += 1

                if bonus >= 1:
                    allocation = min(FIXED_ALLOCATION, ticker_cash)
                    if allocation > 0:
                        pos_shares = math.floor(allocation / close[i])
                        if pos_shares > 0:
                            cost = pos_shares * close[i]
                            ticker_cash -= cost
                            position_shares = pos_shares
                            position_buy_price = close[i]
                            equity_curve.append({
                            })

        # Year-end close
        if position_shares > 0 and close[-1] != 0.0:
            sell_price = close[-1]
            proceeds = position_shares * sell_price
            pl = proceeds - (position_shares * position_buy_price)
            ticker_cash += proceeds
            trades.append({
            })
        ticker_pl = ticker_cash - FIXED_ALLOCATION
        year_pl += ticker_pl

    # Final equity point - use combined year total
    equity_curve.append({
    })

    elapsed = time.time() - t0
    final_equity = INITIAL_CAPITAL + year_pl
    total_return_pct = round((final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2)

    summary = {
    }

    if trades:
            json.dump(output, fout, indent=2)


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

    for s in all_summary:

    # Overall summary - simple sum, no compound (each year is independent)



    main()
