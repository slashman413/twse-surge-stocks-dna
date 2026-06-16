
Key insight from v10 failure: buying AT breakout peak = buying overextended stocks.
Fix: use original indicators as SCREEN only, enter when price pulls back to 20MA.

import os, sys, time, json, gc, math
import pandas as pd
import numpy as np
import yfinance as yf
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_CAPITAL = 1_000_000
MAX_POSITIONS = 8
POSITION_SIZE = INITIAL_CAPITAL // 16  # ~62k per position
MIN_PRICE = 10         # stricter: skip stocks under NT$10
MIN_VOLUME = 1000      # daily volume threshold
STOP_LOSS_PCT = -20
TRAIL_STOP_PCT = -12
TAKE_PROFIT_50 = 20
RSI_EXIT = 35


def load_market_data(year):
    if df.empty:
        return None
    df.index = pd.to_datetime(df.index.date)
    return df


def compute_market_signals(mkt):
    if mkt is None or len(mkt) < 100:
        return {}

    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    dm = dmi(high_s, low_s, close_s, period=300)
    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)
    ma60 = pd.Series(close).rolling(60).mean().values

    n2_arr = np.full(len(close), np.nan)
    for i in range(42, len(close)):
        n2_arr[i] = (np.max(high[i-41:i+1]) + np.min(low[i-41:i+1])) / 2

    k6_arr = np.full(len(close), np.nan)
    k9_arr = np.full(len(close), np.nan)
    for i in range(9, len(close)):
        k6_arr[i] = sum(1 for j in range(i-5, i+1) if close[j] > close[j-1])
        k9_arr[i] = sum(1 for j in range(i-8, i+1) if close[j] > close[j-1])

    signals = {}
    for i in range(len(dates)):

        bullish = False
        if (not np.isnan(n2_arr[i]) and close[i] > n2_arr[i] and
            ((i > 0 and not np.isnan(rsi60_arr[i]) and rsi60_arr[i] > 55) or
             (not np.isnan(pdi_arr[i]) and not np.isnan(mdi_arr[i]) and pdi_arr[i] > mdi_arr[i]))):
            bullish = True

        crash = (not np.isnan(k6_arr[i]) and k6_arr[i] <= 1) or \
                (not np.isnan(k9_arr[i]) and k9_arr[i] <= 2)

        trend_up = not np.isnan(ma60[i]) and close[i] > ma60[i]

        signals[d] = {
        }
    return signals


def compute_stock_signals(grp):
    grp = grp.reset_index(drop=True)
    n = len(close)

    if n < 200:  # need more history for monthly indicators
        return None

    close = np.nan_to_num(close, nan=0.0)
    high = np.nan_to_num(high, nan=0.0)
    low = np.nan_to_num(low, nan=0.0)

    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    # Original indicators (long-term)
    m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

    dm = dmi(high_s, low_s, close_s, period=300)

    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)
    rsi14_arr = np.nan_to_num(rsi(close_s, 14).values, nan=50)
    wr_arr = np.nan_to_num(wr(high_s, low_s, close_s, 50).values, nan=0)
    wr14_arr = np.nan_to_num(wr(high_s, low_s, close_s, 14).values, nan=0)

    # Key MAs for pullback entry
    ma20 = pd.Series(close).rolling(20).mean().values
    ma50 = pd.Series(close).rolling(50).mean().values
    high20 = pd.Series(high).rolling(20).max().values
    low20 = pd.Series(low).rolling(20).min().values
    range20 = high20 - low20
    vol_ma20 = pd.Series(volume).rolling(20).mean().values

    # Monthly indicators

    m_rsi4 = 50.0
    m_adx1 = 0.0
    m_wr3 = 50.0
    if len(monthly) > 14:

    w_vr = 0.0
    if len(weekly) > 2:
        w_denom = w_bvs.replace(0, np.nan)
        if not w_denom.empty:
            w_vr = float(np.nan_to_num((100.0 * w_avs / w_denom).iloc[-1], nan=0.0))

    signals = {}
    price_lookup = {}

    for i in range(200, n):
        if close[i] == 0:
            continue

        price_lookup[d] = float(close[i])

        d4_val = float(d4_arr[i])
        adx_val = float(adx_arr[i])
        pdi_val = float(pdi_arr[i])
        mdi_val = float(mdi_arr[i])
        wr_val = float(wr_arr[i])
        rsi60_val = float(rsi60_arr[i])
        rsi14_val = float(rsi14_arr[i])

        # ── SCREEN: Original buy conditions (for identifying quality candidates) ──
        is_quality = False
        quality_score = 0

        # Condition A: MACD 4 arrows >= 3 + ADX trending
        d4_ok = d4_val >= 3
        adx_ok = adx_val > 20
        di_ok = pdi_val > mdi_val
        if d4_ok and adx_ok and di_ok:
            quality_score += 30

        # Condition B: Monthly strength
        monthly_bull = m_rsi4 > 70 and m_adx1 > 25
        if monthly_bull:
            quality_score += 25

        # Condition C: WR50 < -20 (not oversold, showing strength)
        if wr_val < -20:
            quality_score += 15

        # Condition D: Bonus conditions
        bonus = 0
        if rsi60_val > 57: bonus += 1
        if not np.isnan(vol_ma20[i]) and volume[i] > vol_ma20[i] * 1.3: bonus += 1
        if w_vr > 120: bonus += 1
        if m_adx1 > 30: bonus += 1
        quality_score += bonus * 5

        is_quality = quality_score >= 40

        # ── ENTRY: Pullback to 20MA after quality signal ──
        entry_signal = False
        entry_price = 0.0
        entry_score = 0

        if is_quality and volume[i] >= MIN_VOLUME and close[i] >= MIN_PRICE:
            # Distance from 20MA
            if not np.isnan(ma20[i]) and ma20[i] > 0:
                dist_ma20 = (close[i] - ma20[i]) / ma20[i] * 100
                dist_ma50 = (close[i] - ma50[i]) / ma50[i] * 100 if not np.isnan(ma50[i]) else 0

                # Pullback condition: price within -3% to +2% of 20MA
                # AND above 50MA (still in uptrend)
                # AND RSI(14) between 35-65 (room to run)
                at_ma20 = -3 <= dist_ma20 <= 2
                above_ma50 = dist_ma50 > -5
                rsi_ok = 35 <= rsi14_val <= 65

                if at_ma20 and above_ma50 and rsi_ok:
                    entry_signal = True
                    entry_price = close[i]
                    # Score: prefer stocks closer to 20MA with stronger quality
                    entry_score = quality_score - abs(dist_ma20) * 3 + (m_rsi4 - 70) * 2

        if entry_signal:
            signals[d] = {
            }

    if not signals:
        return None
    return ticker, signals, price_lookup


def process_year(year):
    t0 = time.time()
    if not os.path.exists(f):
        return None

    df = pd.read_parquet(f)

        df = df[df[col].notna()]
    n_total = len(df)

    mkt = load_market_data(year)
    mkt_signals = compute_market_signals(mkt)
    if not mkt_signals:
        return None

    stock_sigs = {}
    price_lookup = {}

    valid_tickers = ticker_counts[ticker_counts >= 200].index

        result = compute_stock_signals(grp)
        if result:
            t, sigs, prices = result
            stock_sigs[t] = sigs
            if prices:
                price_lookup[t] = prices


    # Build per-date candidates
    date_candidates = {}
    for ticker, sigs in stock_sigs.items():
        for d, sig in sigs.items():
            date_candidates.setdefault(d, []).append((
            ))

    for date in date_candidates:
        date_candidates[date].sort(key=lambda x: -x[1])

    all_dates = sorted(set(date_candidates.keys()) | set(mkt_signals.keys()))

    # ── Trading ──
    cash = INITIAL_CAPITAL
    positions = []
    trades = []
    missed_trades = []
    equity_curve = []

    for date in all_dates:
        mkt_sig = mkt_signals.get(date, {})
        candidates = date_candidates.get(date, [])
        top8 = set(t[0] for t in candidates[:MAX_POSITIONS])

        # Crash liquidate
        if is_crash and positions:
            for pos in list(positions):
                if sp <= 0: continue
                trades.append({
                })
            positions.clear()
            continue

        # Per-position exit
        for pos in list(positions):
            if sp <= 0: continue



            # Stop loss
            if pl_pct <= STOP_LOSS_PCT:
            # Trailing stop
                if dd <= TRAIL_STOP_PCT:
            # RSI exit (daily RSI < 35 after 5 days)
            if not sell:
                if days >= 5 and rsi < RSI_EXIT:
            # Take profit half
                if half > 0:
                    cash += half * sp
                    trades.append({
                    })
            # Out of top 8 for 5+ days

            if sell:
                trades.append({
                })
                positions.remove(pos)

        # Only buy in bullish + trending
        if not (is_bullish and trend_up):
            for t, sc, _ in candidates[:MAX_POSITIONS]:
                if t not in existing:
            continue

        # Buy
        slots = MAX_POSITIONS - len(positions)
        for ticker, score, cp in candidates:
            if slots <= 0: break
            if ticker in existing: continue
            if cp <= 0: continue
            shares = math.floor(POSITION_SIZE / cp)
            cost = shares * cp
            if cost <= 0 or cost > cash: continue
            cash -= cost
            slots -= 1


    # Year-end close
    for pos in list(positions):
        ld = all_dates[-1]
        if sp <= 0: continue
        trades.append({
        })
    positions.clear()

    final_equity = cash
    total_return_pct = round((final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2)

    summary = {
    }

    if trades:
            json.dump(output, fout, indent=2)


    del df; gc.collect()
    return summary


def main():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    years = list(range(2004, 2027))
    all_summary = []

    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_year, y): y for y in years}
        for future in as_completed(futures):
            r = future.result()
            if r:
                all_summary.append(r)

        json.dump(all_summary, f, indent=2)

    for s in all_summary:




    main()
