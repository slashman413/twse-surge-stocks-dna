
Key changes from v9:
1. Relax bonus from >=2 to >=1 (more candidates)
2. Instead of buying AT breakout, buy on pullback near breakout level
3. Market trend filter: TAIEX > 60-day MA
4. Buy on pullback day when bpt dips to -3% to +1% of 20-day high

import os, sys, time, json, gc, math
import pandas as pd
import numpy as np
import yfinance as yf
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_CAPITAL = 1_000_000
MAX_POSITIONS = 10
POSITION_SIZE = INITIAL_CAPITAL // 20  # 50k per position
MIN_PRICE = 5
STOP_LOSS_PCT = -25
TRAIL_STOP_PCT = -15
TAKE_PROFIT_50 = 25
TAKE_PROFIT_ALL = 50
RSI_EXIT = 30


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

        # Crash: 6K <= 1 OR 9K <= 2
        crash = (not np.isnan(k6_arr[i]) and k6_arr[i] <= 1) or \
                (not np.isnan(k9_arr[i]) and k9_arr[i] <= 2)

        # Trend filter: TAIEX > 60-day MA
        trend_up = not np.isnan(ma60[i]) and close[i] > ma60[i]

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

    high20 = pd.Series(high).rolling(20).max().values
    low20 = pd.Series(low).rolling(20).min().values
    range_width = high20 - low20
    ma10 = pd.Series(close).rolling(10).mean().values
    vol_ma20 = pd.Series(volume).rolling(20).mean().values

    # Monthly indicators

    m_rsi4 = 50.0
    m_adx1 = 0.0
    if len(monthly) > 14:

    w_vr = 0.0
    if len(weekly) > 2:
        w_denom = w_bvs.replace(0, np.nan)
        if not w_denom.empty:
            w_vr = float(np.nan_to_num((100.0 * w_avs / w_denom).iloc[-1], nan=0.0))

    signals = {}
    price_lookup = {}  # date -> close (for sell price lookup)

    for i in range(100, n):
        if close[i] == 0:
            continue

        d4_val = float(d4_arr[i])
        adx_val = float(adx_arr[i])
        wr_val = float(wr_arr[i])
        rsi60_val = float(rsi60_arr[i])
        pdi_val = float(pdi_arr[i])
        mdi_val = float(mdi_arr[i])

        # Store close price for ALL dates (for sell/liquidation in trading loop)
        price_lookup[d] = float(close[i])

        # Bonus indicators (5 total, bonus>=1)
        bonus = 0
        if rsi60_val > 57: bonus += 1
        if adx_val > 25 and pdi_val > mdi_val: bonus += 1
        if not np.isnan(vol_ma20[i]) and vol_ma20[i] > 0 and volume[i] > vol_ma20[i] * 1.5: bonus += 1
        if m_adx1 > 30: bonus += 1
        if w_vr > 150: bonus += 1

        # Breakout % from 20-day high
        bpt = 0.0
        if not np.isnan(high20[i]) and range_width[i] > 0:
            bpt = (close[i] - high20[i]) / high20[i] * 100

        # ── BREAKOUT DETECTION: stock breaking above 20-day high ──
        d4_ok = d4_val >= 3
        adx_ok = adx_val > 20
        wr_ok = wr_val < -20
        bonus_ok = bonus >= 1
        breakout_ok = 0 <= bpt < 5
        vol_ok = volume[i] >= 1000

        if d4_ok and adx_ok and wr_ok and bonus_ok and breakout_ok and vol_ok:
            # Score: prefer stocks close to 10-MA (pullback candidates)
            dist_to_ma10 = (close[i] - ma10[i]) / ma10[i] * 100 if not np.isnan(ma10[i]) else 0
            score = round((bonus * 20) + adx_val - abs(dist_to_ma10) * 5, 1)
            signals[d] = {
            }

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

    # Pre-filter: only tickers with >= 100 rows (skip sparse tickers)
    valid_tickers = ticker_counts[ticker_counts >= 100].index

        result = compute_stock_signals(grp)
        if result:
            t, sigs, prices = result
            stock_sigs[t] = sigs
            if prices:
                price_lookup[t] = prices


    # Build per-date candidate list (buy_signal days only)
    date_candidates = {}
    for ticker, sigs in stock_sigs.items():
        for d, sig in sigs.items():
            if cp < MIN_PRICE:
                continue
            date_candidates.setdefault(d, []).append((
            ))

    for date in date_candidates:
        date_candidates[date].sort(key=lambda x: -x[1])

    all_dates = sorted(set(date_candidates.keys()) | set(mkt_signals.keys()))

    # ── Trading Simulation ──
    cash = INITIAL_CAPITAL
    positions = []
    trades = []
    missed_trades = []
    equity_curve = []

    for date in all_dates:
        mkt_sig = mkt_signals.get(date, {})
        candidates = date_candidates.get(date, [])
        top10 = set(t[0] for t in candidates[:MAX_POSITIONS])

        # ── Crash liquidate ──
        if is_crash and positions:
            for pos in list(positions):
                if sell_price <= 0:
                    continue
                cash += proceeds
                trades.append({
                })
            positions.clear()
            continue

        # ── Per-position exit ──
        for pos in list(positions):
            if sell_price <= 0:
                continue



            sell_all = False

            # Hard stop-loss
            if pl_pct <= STOP_LOSS_PCT:
                sell_all = True

            # Trailing stop
                if dd <= TRAIL_STOP_PCT:
                    sell_all = True

            # RSI exit
            if not sell_all and days_held >= 3 and rsi_now < RSI_EXIT:
                sell_all = True

            # Take profit half
                if half > 0:
                    proceeds = half * sell_price
                    cash += proceeds
                    trades.append({
                    })

            # Take profit rest
                sell_all = True

            # Fell below breakout zone for 5 days
                    sell_all = True

            if sell_all:
                cash += proceeds
                trades.append({
                })
                positions.remove(pos)

        # ── Only buy in bullish + trending market ──

        if not (is_bullish and trend_up):
            for ticker, score, bpt, _ in candidates[:MAX_POSITIONS]:
                if ticker not in existing_tickers:
                    missed_trades.append({
                    })
            ) for p in positions)
            continue

        # ── Buy ──
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
        ) for p in positions)

    # Year-end close
    for pos in list(positions):
        last_date = all_dates[-1]
        if sell_price <= 0:
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
