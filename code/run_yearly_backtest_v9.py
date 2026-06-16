
Fixes v8 issues:
1. Add hard stop-loss (-20% from buy price)
2. Add trailing stop (-12% from peak since buy)
3. Add take-profit (sell 50% at +20%, rest at +40%)
4. Add technical exit (daily RSI < 35 after 3+ days in position)
5. Fix breakout: buy within +0.5% of 20-day high (not 2%+)
6. Add 5 bonus conditions (was 2)
7. Reduce position size from 200k to 100k

import os, sys, time, json, gc, math
import pandas as pd
import numpy as np
import yfinance as yf
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_CAPITAL = 1_000_000
MAX_POSITIONS = 5
POSITION_SIZE = INITIAL_CAPITAL // 10  # 100k per position (10%)
MIN_PRICE = 5          # skip penny stocks
STOP_LOSS_PCT = -20       # hard stop: -20% from buy price
TRAIL_STOP_PCT = -12      # trailing stop: -12% from peak since buy
TAKE_PROFIT_50 = 20       # sell 50% at +20%
TAKE_PROFIT_ALL = 40      # sell remaining at +40%
RSI_EXIT = 35             # sell if RSI < 35


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

    # N2
    n2_arr = np.full(len(close), np.nan)
    for i in range(42, len(close)):
        n2_arr[i] = (np.max(high[i-41:i+1]) + np.min(low[i-41:i+1])) / 2

    # 6K/9K
    k6_arr = np.full(len(close), np.nan)
    k9_arr = np.full(len(close), np.nan)
    for i in range(9, len(close)):
        k6_arr[i] = sum(1 for j in range(i-5, i+1) if close[j] > close[j-1])
        k9_arr[i] = sum(1 for j in range(i-8, i+1) if close[j] > close[j-1])

    signals = {}
    for i in range(len(dates)):

        # Bullish: close > N2 AND (RSI60>55 OR PDI>MDI)
        bullish = False
        if (not np.isnan(n2_arr[i]) and close[i] > n2_arr[i] and
            ((i > 0 and not np.isnan(rsi60_arr[i]) and rsi60_arr[i] > 55) or
             (not np.isnan(pdi_arr[i]) and not np.isnan(mdi_arr[i]) and pdi_arr[i] > mdi_arr[i]))):
            bullish = True

        # Crash: 6K <= 1 OR 9K <= 2 (stricter)
        crash = (not np.isnan(k6_arr[i]) and k6_arr[i] <= 1) or \
                (not np.isnan(k9_arr[i]) and k9_arr[i] <= 2)

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

    # MACD 4 arrows
    m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)

    # DMI
    dm = dmi(high_s, low_s, close_s, period=300)

    wr_arr = np.nan_to_num(wr(high_s, low_s, close_s, 50).values, nan=0)
    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)
    rsi14_arr = np.nan_to_num(rsi(close_s, 14).values, nan=50)

    # 20-day high/low
    high20 = pd.Series(high).rolling(20).max().values
    low20 = pd.Series(low).rolling(20).min().values
    range_width = high20 - low20

    # Volume MA
    vol_ma20 = pd.Series(volume).rolling(20).mean().values

    # Monthly RSI4, ADX1, W%R3

    m_rsi4 = 50.0
    m_adx1 = 0.0
    m_wr3 = 50.0
    if len(monthly) > 14:

    # Weekly VR
    w_vr = 0.0
    if len(weekly) > 2:
        w_denom = w_bvs.replace(0, np.nan)
        if not w_denom.empty:
            w_vr = float(np.nan_to_num((100.0 * w_avs / w_denom).iloc[-1], nan=0.0))

    signals = {}

    for i in range(100, n):
        if close[i] == 0:
            continue

        d4_val = float(d4_arr[i])
        adx_val = float(adx_arr[i])
        wr_val = float(wr_arr[i])
        rsi60_val = float(rsi60_arr[i])
        rsi14_val = float(rsi14_arr[i])
        pdi_val = float(pdi_arr[i])
        mdi_val = float(mdi_arr[i])

        # --- 5 Bonus/Surge indicators ---
        bonus = 0
        # 1. RSI60 > 57 (mid-term momentum)
        if rsi60_val > 57: bonus += 1
        # 2. ADX trending + PDI > MDI (trend strength with direction)
        if adx_val > 25 and pdi_val > mdi_val: bonus += 1
        # 3. Volume surge (>1.5x 20-day avg)
        if not np.isnan(vol_ma20[i]) and vol_ma20[i] > 0 and volume[i] > vol_ma20[i] * 1.5: bonus += 1
        # 4. Monthly ADX1 > 30 (strong monthly trend)
        if m_adx1 > 30: bonus += 1
        # 5. Weekly VR > 150 (volume rising on up weeks)
        if w_vr > 150: bonus += 1

        # --- Breakout detection ---
        bpt = 0.0
        if not np.isnan(high20[i]) and range_width[i] > 0:
            bpt = (close[i] - high20[i]) / high20[i] * 100

        # Daily data entry (for ALL dates — needed for sell checks)
        entry = {
        }

        # Buy condition check
        d4_ok = d4_val >= 3
        adx_ok = adx_val > 20
        wr_ok = wr_val < -20
        bonus_ok = bonus >= 2
        breakout_ok = 0 <= bpt < 1.5  # tighter: just breaking out

        if d4_ok and adx_ok and wr_ok and bonus_ok and breakout_ok:
            # Score: weighted by bonus strength and ADX, penalize large bpt

        signals[d] = entry

    if not signals:
        return None
    return ticker, signals


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
        result = compute_stock_signals(grp)
        if result:
            t, sigs = result
            stock_sigs[t] = sigs


    # Build per-date candidate list (only buy_signal=True, min price)
    date_candidates = {}
    missed_by_date = {}
    for ticker, sigs in stock_sigs.items():
        for date, sig in sigs.items():
                continue
                continue
            date_candidates.setdefault(date, []).append((
            ))
            # Record candidates that would have been in top 5 but have lower score
            # (we handle this during trading loop)

    for date in date_candidates:
        date_candidates[date].sort(key=lambda x: -x[1])

    all_dates = sorted(set(date_candidates.keys()) | set(mkt_signals.keys()))

    # ── Trading simulation ──
    cash = INITIAL_CAPITAL
    positions = []  # [{ticker, shares, buy_price, buy_date, peak_price, sold_half}]
    trades = []
    missed_trades = []
    equity_curve = []

    for date in all_dates:
        mkt_sig = mkt_signals.get(date, {})
        candidates = date_candidates.get(date, [])
        top5 = set(t[0] for t in candidates[:MAX_POSITIONS])

        # ═══ EXIT CHECKS (before buying) ═══

        # 1. Crash → liquidate all immediately
        if is_crash and positions:
            for pos in list(positions):
                    continue
                cash += proceeds
                trades.append({
                })
            positions.clear()
            continue

        # 2. Per-position exit checks
        for pos in list(positions):
                continue


            # Update peak

            sell_all = False

            # a) Hard stop-loss: -20% from buy
            if pl_pct <= STOP_LOSS_PCT:
                sell_all = True

            # b) Trailing stop: -12% from peak
                if drawdown <= TRAIL_STOP_PCT:
                    sell_all = True

            # c) Technical exit: RSI < 35 after 3+ days
            if not sell_all and days_held >= 3 and rsi_now < RSI_EXIT:
                sell_all = True

            # d) Take profit: +20% → sell half
            sell_half = False
                sell_half = True
                if half_shares > 0:
                    proceeds = half_shares * sell_price
                    cash += proceeds
                    trades.append({
                    })

            # e) Take profit final: +40% → sell rest
                sell_all = True

            # f) Fell out of top 5 for 5+ consecutive days
                    sell_all = True

            if sell_all:
                cash += proceeds
                trades.append({
                })
                positions.remove(pos)

        # ═══ BUY LOGIC ═══

        if not is_bullish:
            # Record missed trades
            for ticker, score, bpt, _ in candidates[:MAX_POSITIONS]:
                if ticker not in existing_tickers:
                    missed_trades.append({
                    })
            ) for p in positions)
            continue

        # Buy top picks
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

        # Record equity
        ) for p in positions)

    # Year-end close
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
