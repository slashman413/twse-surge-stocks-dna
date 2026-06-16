import os, sys, time, json, gc, math
import pandas as pd
import numpy as np
import yfinance as yf
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_CAPITAL = 1_000_000
MAX_POSITIONS = 5
POSITION_SIZE = INITIAL_CAPITAL // MAX_POSITIONS  # 200k per position


def load_market_data(year):
    try:
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index.date)
        return df
    except:
        return None


def compute_market_signals(mkt):
    if mkt is None or len(mkt) < 100:
        return {}, {}

    # Daily signals
    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

    dm = dmi(high_s, low_s, close_s, period=300)

    wr_arr = np.nan_to_num(wr(high_s, low_s, close_s, 50).values, nan=0)
    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)

    # N2 calculation
    n2_arr = np.full(len(close), np.nan)
    for i in range(42, len(close)):
        hh = np.max(high[i-41:i+1])
        ll = np.min(low[i-41:i+1])
        n2_arr[i] = (hh + ll) / 2

    # 6K/9K calculation (crash detection)
    k6_arr = np.full(len(close), np.nan)
    k9_arr = np.full(len(close), np.nan)
    for i in range(9, len(close)):
        up6 = sum(1 for j in range(i-5, i+1) if close[j] > close[j-1])
        up9 = sum(1 for j in range(i-8, i+1) if close[j] > close[j-1])
        k6_arr[i] = up6
        k9_arr[i] = up9

    # Build per-date signals
    signals = {}
    for i in range(len(dates)):
        bullish = False
        if not np.isnan(n2_arr[i]) and not np.isnan(close[i]) and close[i] > n2_arr[i]:
            # Also check MACD > 0 and +DI > -DI
            macd_pos = False
            di_pos = False
            if i > 0 and not np.isnan(rsi60_arr[i]) and rsi60_arr[i] > 55:
                macd_pos = True
            if not np.isnan(pdi_arr[i]) and not np.isnan(mdi_arr[i]) and pdi_arr[i] > mdi_arr[i]:
                di_pos = True
            if macd_pos or di_pos:
                bullish = True

        crash = False
        if not np.isnan(k6_arr[i]) and k6_arr[i] <= 2 and not np.isnan(k9_arr[i]) and k9_arr[i] <= 3:
            crash = True

        signals[d] = {
        }
    return signals


def compute_stock_signals(grp):
    grp = grp.reset_index(drop=True)
    n = len(close)

    if n < 100:
        return None

    close = np.nan_to_num(close, nan=0.0)
    high = np.nan_to_num(high, nan=0.0)
    low = np.nan_to_num(low, nan=0.0)

    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

    dm = dmi(high_s, low_s, close_s, period=300)

    wr_arr = np.nan_to_num(wr(high_s, low_s, close_s, 50).values, nan=0)
    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)

    # ATR for volatility
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    atr = pd.Series(tr).rolling(14).mean().values

    # Breakout detection: price breaks above 20-day high
    high20 = pd.Series(high).rolling(20).max().values
    low20 = pd.Series(low).rolling(20).min().values
    range_width = high20 - low20

    # Monthly/weekly for bonus

    m_pdi1 = 0.0
    m_rsi4 = 50.0
    if len(monthly) > 14:

    w_vr = 0.0
    if len(weekly) > 2:
        w_denom = w_bvs.replace(0, np.nan)
        w_vr = float(np.nan_to_num((100.0 * w_avs / w_denom).iloc[-1], nan=0.0)) if not w_denom.empty else 0.0

    # Build per-date signal map
    signals = {}

    # Monthly/weekly recompute per date (resample trick: last known)
    w_vr_series = np.full(n, w_vr)
    m_pdi1_series = np.full(n, m_pdi1)
    m_rsi4_series = np.full(n, m_rsi4)

    for i in range(100, n):
        if close[i] == 0:
            continue


        # Buy conditions (core 3)
        d4_val = float(d4_arr[i])
        adx_val = float(adx_arr[i])
        wr_val = float(wr_arr[i])
        rsi60_val = float(rsi60_arr[i])

        # Bonus check
        bonus = 0
        if rsi60_val > 57: bonus += 1
        if not np.isnan(w_vr) and abs(w_vr - 150) < 50: bonus += 1

        # Breakout score
        breakout = 0
        if not np.isnan(high20[i]) and not np.isnan(low20[i]) and range_width[i] > 0:
            # Price at least 2% above 20-day high = breakout
            bpt = (close[i] - high20[i]) / high20[i] * 100
            breakout = bpt
        else:
            bpt = 0

        signals[d] = {
        }

    return ticker, signals


def process_year(year):
    t0 = time.time()
    if not os.path.exists(f):
        return None

    df = pd.read_parquet(f)

        df = df[df[col].notna()]
    n_total = len(df)

    # Load market data
    mkt = load_market_data(year)
    mkt_signals = compute_market_signals(mkt)
    if not mkt_signals:
        return None

    # Pre-compute all stock signals
    stock_sigs = {}
        result = compute_stock_signals(grp)
        if result:
            t, sigs = result
            stock_sigs[t] = sigs


    # Build per-date candidate list (pre-filtered)
    date_candidates = {}  # date -> [(ticker, score, bpt), ...]
    missed_by_date = {}   # date -> [missed_trade, ...]
    for ticker, sigs in stock_sigs.items():
        for date, sig in sigs.items():

            buy_flag = d4 >= 3 and adx > 20 and wr < -20 and bonus >= 1
            near_miss = d4 >= 3 and adx > 20 and wr < -20 and bonus < 1

            if buy_flag:
                score = bpt + (bonus * 5) + (adx / 10)
            elif near_miss and bonus == 0:
                missed_by_date.setdefault(date, []).append({
                })

    # Sort candidates by score descending per date
    for date in date_candidates:
        date_candidates[date].sort(key=lambda x: -x[1])

    all_dates = sorted(set(date_candidates.keys()) | set(mkt_signals.keys()))
    if not all_dates:
        all_dates = sorted(date_candidates.keys())

    # Trading simulation
    cash = INITIAL_CAPITAL
    positions = []  # [{ticker, shares, buy_price, buy_date}]
    trades = []
    missed_trades = []
    equity_curve = []

    for date in all_dates:
        mkt_sig = mkt_signals.get(date, {})
        candidates = date_candidates.get(date, [])

        # ── Crash → liquidate all ──
        if is_crash and positions:
            for pos in list(positions):
                    continue
                cash += proceeds
                trades.append({
                })
            positions.clear()
            continue

        # ── Sell positions not in today's top 5 ──
        top5 = set(t[0] for t in candidates[:MAX_POSITIONS])
        for pos in list(positions):
                    continue
                cash += proceeds
                trades.append({
                })
                positions.remove(pos)

        # ── Only buy if market is bullish ──
        if not is_bullish:
            for ticker, score, bpt, _ in candidates:
                if ticker not in existing_tickers:
                    missed_trades.append({
                    })
            portfolio_value = sum(
                for p in positions
            )
            continue

        # ── Buy top picks ──
        slots = MAX_POSITIONS - len(positions)
        for ticker, score, bpt, close_price in candidates:
            if slots <= 0:
                break
            if ticker in existing_tickers:
                continue

            buy_price = close_price
            if buy_price <= 0:
                continue

            shares = math.floor(POSITION_SIZE / buy_price)
            cost = shares * buy_price
            if cost <= 0:
                continue

            if cost > cash:
                missed_trades.append({
                })
                continue

            cash -= cost
            positions.append({
            })
            slots -= 1

        # ── Record equity ──
        portfolio_value = sum(
            for p in positions
        )

    # Year-end close all positions
    for pos in list(positions):
        last_date = all_dates[-1]
            continue
        cash += proceeds
        trades.append({
        })
    positions.clear()

    elapsed = time.time() - t0
    final_equity = cash
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




    main()
