"""Yearly backtest v12 - Trend pullback + quality gate

Changes from v11:
  A) Remove top8 ranking churn (69% of exits were forced rotation)
  C) Bonus >= 2 required, max 2 daily entries, tighter pullback zone
"""

import os, sys, time, json, gc, math
import pandas as pd
import numpy as np
import yfinance as yf
from indicators import macd_4arrows, dmi, wr, rsi
from strategy import _safe_last

ADJ_DIR = "D:/TWSE-Data/Adjusted"
TEMP_DIR = os.path.join(ADJ_DIR, "_temp")
OUT_DIR = r"D:\twse-surge-stocks-dna\docs\yearly_backtests"
os.makedirs(OUT_DIR, exist_ok=True)
VERSION = "v12"

INITIAL_CAPITAL = 3_000_000
MAX_POSITIONS = 10
MAX_DAILY_ENTRIES = 2
POSITION_SIZE = INITIAL_CAPITAL // 10  # ~300k per position (10%)
MIN_PRICE = 10
MIN_VOLUME = 1000
STOP_LOSS_PCT = -15      # tighter stop
TRAIL_STOP_PCT = -15     # 放寬與硬停損一致
TAKE_PROFIT_50 = 20
RSI_EXIT = 35


def load_market_data(year):
    twii = yf.Ticker("^TWII")
    df = twii.history(start=f"{year-1}-01-01", end=f"{year+1}-01-01")
    if df.empty:
        return None
    df.index = pd.to_datetime(df.index.date)
    df["Date"] = df.index
    return df


def compute_market_signals(mkt, target_year):
    if mkt is None or len(mkt) < 100:
        return {}
    close = mkt["Close"].values.astype(np.float64)
    high = mkt["High"].values.astype(np.float64)
    low = mkt["Low"].values.astype(np.float64)
    dates = mkt["Date"].values

    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    dm = dmi(high_s, low_s, close_s, period=300)
    pdi_arr = np.nan_to_num(dm["plus_di"].values, nan=0)
    mdi_arr = np.nan_to_num(dm["minus_di"].values, nan=0)
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
        d = pd.Timestamp(dates[i]).strftime("%Y-%m-%d")
        dt = pd.Timestamp(dates[i])
        if dt.year != target_year:
            continue  # only emit signals for target year

        bullish = False
        if (not np.isnan(n2_arr[i]) and close[i] > n2_arr[i] and
            ((i > 0 and not np.isnan(rsi60_arr[i]) and rsi60_arr[i] > 55) or
             (not np.isnan(pdi_arr[i]) and not np.isnan(mdi_arr[i]) and pdi_arr[i] > mdi_arr[i]))):
            bullish = True

        crash = (not np.isnan(k6_arr[i]) and k6_arr[i] <= 1) or \
                (not np.isnan(k9_arr[i]) and k9_arr[i] <= 2)

        trend_up = not np.isnan(ma60[i]) and close[i] > ma60[i]

        signals[d] = {
            "bullish": bullish,
            "crash": crash,
            "trend_up": trend_up,
        }
    return signals


def fix_bad_data(close, high, low, volume, threshold=0.30):
    """Replace bad data points (single-day drop >threshold that recovers next day)."""
    n = len(close)
    ret = np.diff(close) / np.maximum(close[:-1], 1e-10)
    bad_mask = np.zeros(n, dtype=bool)
    for i in range(1, n - 1):
        if ret[i - 1] < -threshold and close[i] > 0:
            prev_val = close[i - 1]
            next_val = close[i + 1]
            if next_val > 0 and prev_val > 0:
                recovery = (next_val - prev_val) / prev_val
                if recovery > -0.10:
                    bad_mask[i] = True
    if bad_mask.any():
        close = close.copy()
        high = high.copy()
        low = low.copy()
        volume = volume.copy()
        for i in np.where(bad_mask)[0]:
            close[i] = close[i - 1]
            high[i] = max(high[i - 1], high[i + 1] if i + 1 < n else high[i - 1])
            low[i] = min(low[i - 1], low[i + 1] if i + 1 < n else low[i - 1])
            volume[i] = volume[i - 1]
    return close, high, low, volume


def compute_stock_signals(grp, target_year):
    """Screen stocks with original indicators using warmup data. Only emit signals for target_year."""
    grp = grp.reset_index(drop=True)
    close = grp["Adj_Close"].values.astype(np.float64)
    high = grp["Adj_High"].values.astype(np.float64)
    low = grp["Adj_Low"].values.astype(np.float64)
    volume = grp["Adj_Volume"].values.astype(np.float64)
    dates = grp["Date"].values
    n = len(close)

    if n < 200:
        return None

    close, high, low, volume = fix_bad_data(close, high, low, volume)
    close = np.nan_to_num(close, nan=0.0, posinf=0.0, neginf=0.0)
    high = np.nan_to_num(high, nan=0.0, posinf=0.0, neginf=0.0)
    low = np.nan_to_num(low, nan=0.0, posinf=0.0, neginf=0.0)
    volume = np.nan_to_num(volume, nan=0.0, posinf=0.0, neginf=0.0)

    close_s = pd.Series(close)
    high_s = pd.Series(high)
    low_s = pd.Series(low)

    m4 = macd_4arrows(close_s, fast=200, slow=209, signal=210)
    d4_arr = np.nan_to_num(m4["arrows_count"].values, nan=0)
    macd_line = m4.get("macd", pd.Series([np.nan] * n)).values

    dm = dmi(high_s, low_s, close_s, period=300)
    adx_arr = np.nan_to_num(dm["adx"].values, nan=0)
    pdi_arr = np.nan_to_num(dm["plus_di"].values, nan=0)
    mdi_arr = np.nan_to_num(dm["minus_di"].values, nan=0)

    rsi60_arr = np.nan_to_num(rsi(close_s, 60).values, nan=50)
    rsi14_arr = np.nan_to_num(rsi(close_s, 14).values, nan=50)
    wr_arr = np.nan_to_num(wr(high_s, low_s, close_s, 50).values, nan=0)
    wr14_arr = np.nan_to_num(wr(high_s, low_s, close_s, 14).values, nan=0)

    ma20 = pd.Series(close).rolling(20).mean().values
    ma50 = pd.Series(close).rolling(50).mean().values
    high20 = pd.Series(high).rolling(20).max().values
    low20 = pd.Series(low).rolling(20).min().values
    range20 = high20 - low20
    vol_ma20 = pd.Series(volume).rolling(20).mean().values

    daily = pd.DataFrame({"Date": pd.to_datetime(dates), "Close": close, "High": high, "Low": low, "Volume": volume})
    monthly = daily.resample("ME", on="Date").agg({"Close": "last", "High": "max", "Low": "min"}).dropna()
    weekly = daily.resample("W", on="Date").agg({"Close": "last", "High": "max", "Low": "min", "Volume": "sum"}).dropna()

    m_rsi4 = 50.0
    m_adx1 = 0.0
    m_wr3 = 50.0
    if len(monthly) > 14:
        m_rsi4 = float(_safe_last(rsi(monthly["Close"], 4), 50.0))
        m_dmi = dmi(monthly["High"], monthly["Low"], monthly["Close"], period=1)
        m_adx1 = float(_safe_last(m_dmi["plus_di"], 0.0))
        m_wr3 = float(_safe_last(wr(monthly["High"], monthly["Low"], monthly["Close"], 3), 50.0))

    w_vr = 0.0
    if len(weekly) > 2:
        w_up = weekly["Close"].diff() > 0
        w_down = weekly["Close"].diff() < 0
        w_avs = (weekly["Volume"] * w_up).rolling(2).sum()
        w_bvs = (weekly["Volume"] * w_down).rolling(2).sum()
        w_denom = w_bvs.replace(0, np.nan)
        if not w_denom.empty:
            w_vr = float(np.nan_to_num((100.0 * w_avs / w_denom).iloc[-1], nan=0.0))

    signals = {}
    price_lookup = {}
    ticker = str(grp["Ticker"].iloc[0]).zfill(4)

    for i in range(200, n):
        if close[i] == 0:
            continue

        d = pd.Timestamp(dates[i]).strftime("%Y-%m-%d")
        price_lookup[d] = float(close[i])

        if pd.Timestamp(dates[i]).year != target_year:
            continue

        d4_val = float(d4_arr[i])
        adx_val = float(adx_arr[i])
        pdi_val = float(pdi_arr[i])
        mdi_val = float(mdi_arr[i])
        wr_val = float(wr_arr[i])
        rsi60_val = float(rsi60_arr[i])
        rsi14_val = float(rsi14_arr[i])

        is_quality = False
        quality_score = 0

        d4_ok = d4_val >= 3
        adx_ok = adx_val > 20
        di_ok = pdi_val > mdi_val
        if d4_ok and adx_ok and di_ok:
            quality_score += 30

        monthly_bull = m_rsi4 > 70 and m_adx1 > 25
        if monthly_bull:
            quality_score += 25

        if wr_val < -20:
            quality_score += 15

        bonus = 0
        if rsi60_val > 57: bonus += 1
        if not np.isnan(vol_ma20[i]) and volume[i] > vol_ma20[i] * 1.3: bonus += 1
        if w_vr > 120: bonus += 1
        if m_adx1 > 30: bonus += 1
        quality_score += bonus * 5

        is_quality = quality_score >= 40 and bonus >= 2

        entry_signal = False
        entry_price = 0.0
        entry_score = 0

        if is_quality and volume[i] >= MIN_VOLUME and close[i] >= MIN_PRICE:
            if not np.isnan(ma20[i]) and ma20[i] > 0:
                dist_ma20 = (close[i] - ma20[i]) / ma20[i] * 100
                dist_ma50 = (close[i] - ma50[i]) / ma50[i] * 100 if not np.isnan(ma50[i]) else 0

                at_ma20 = -2 <= dist_ma20 <= 1
                above_ma50 = dist_ma50 > -3
                rsi_ok = 30 <= rsi14_val <= 60

                if at_ma20 and above_ma50 and rsi_ok:
                    entry_signal = True
                    entry_price = close[i]
                    entry_score = quality_score - abs(dist_ma20) * 3 + (m_rsi4 - 70) * 2

        if entry_signal:
            signals[d] = {
                "close": entry_price,
                "score": round(entry_score, 1),
                "dist_ma20": round(dist_ma20, 2),
                "rsi14": rsi14_val,
                "quality": quality_score,
                "bonus": bonus,
            }

    if not signals:
        return None
    return ticker, signals, price_lookup


def process_year(year):
    t0 = time.time()
    f = os.path.join(TEMP_DIR, f"{year}.parquet")
    if not os.path.exists(f):
        return None

    print(f"📂 載入 {year} 年資料...", flush=True)

    warmup_path = os.path.join(TEMP_DIR, f"{year-1}.parquet")
    warmup_df = None
    if os.path.exists(warmup_path):
        warmup_df = pd.read_parquet(warmup_path)
        warmup_df["Date"] = pd.to_datetime(warmup_df["Date"])
        warmup_df["Ticker"] = warmup_df["Ticker"].astype(str).str.zfill(4)
        for col in ["Adj_Close", "Adj_High", "Adj_Low"]:
            warmup_df = warmup_df[warmup_df[col].notna()]

    df = pd.read_parquet(f)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Ticker"] = df["Ticker"].astype(str).str.zfill(4)

    for col in ["Adj_Close", "Adj_High", "Adj_Low"]:
        df = df[df[col].notna()]

    if warmup_df is not None:
        df = pd.concat([warmup_df, df], ignore_index=True)
        print(f"  含 warmup {year-1}, 共 {len(df)} 筆", flush=True)

    df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)
    n_total = len(df)

    print(f"📊 載入大盤資料...", flush=True)
    mkt = load_market_data(year)
    mkt_signals = compute_market_signals(mkt, year)
    if not mkt_signals:
        return None

    print(f"📐 計算個股訊號...", flush=True)
    stock_sigs = {}
    price_lookup = {}

    ticker_counts = df["Ticker"].value_counts()
    valid_tickers = ticker_counts[ticker_counts >= 200].index

    for ticker, grp in df[df["Ticker"].isin(valid_tickers)].groupby("Ticker", sort=False):
        t_str = str(ticker).zfill(4)
        if t_str[:2] in ('00', '01', '02', '03', '04', '05', '06', '07', '08') or len(t_str) != 4:
            continue
        result = compute_stock_signals(grp, year)
        if result:
            t, sigs, prices = result
            stock_sigs[t] = sigs
            if prices:
                price_lookup[t] = prices

    print(f"   {len(stock_sigs)} 檔有訊號", flush=True)

    date_candidates = {}
    for ticker, sigs in stock_sigs.items():
        for d, sig in sigs.items():
            date_candidates.setdefault(d, []).append((
                ticker, sig["score"], sig["close"]
            ))

    for date in date_candidates:
        date_candidates[date].sort(key=lambda x: -x[1])

    all_dates = sorted(set(date_candidates.keys()) | set(mkt_signals.keys()))
    print(f"   {len(all_dates)} 個交易日", flush=True)

    # ── Trading ──
    cash = INITIAL_CAPITAL
    positions = []
    trades = []
    missed_trades = []
    equity_curve = []

    for date in all_dates:
        mkt_sig = mkt_signals.get(date, {})
        is_crash = mkt_sig.get("crash", False)
        is_bullish = mkt_sig.get("bullish", False)
        trend_up = mkt_sig.get("trend_up", False)
        candidates = date_candidates.get(date, [])

        # Crash liquidate (immediate)
        if is_crash and positions:
            for pos in list(positions):
                sp = price_lookup.get(pos["ticker"], {}).get(date, 0)
                if sp <= 0:
                    sp = price_lookup.get(pos["ticker"], {}).get(pos["buy_date"], pos["buy_price"])
                    if sp <= 0: sp = pos["buy_price"]
                cash += pos["shares"] * sp
                trades.append({
                    "ticker": pos["ticker"], "buy_date": pos["buy_date"],
                    "buy_price": round(pos["buy_price"], 2), "sell_date": date,
                    "sell_price": round(sp, 2), "shares": pos["shares"],
                    "pl": round(pos["shares"] * (sp - pos["buy_price"]), 2),
                    "pl_pct": round((sp - pos["buy_price"]) / pos["buy_price"] * 100, 2),
                    "sell_reason": "大盤崩跌清倉"
                })
            positions.clear()
            equity_curve.append({"date": date, "equity": round(cash, 2), "type": "crash"})
            continue

        for pos in list(positions):
            sp = price_lookup.get(pos["ticker"], {}).get(date, 0)
            if sp <= 0:
                sp = price_lookup.get(pos["ticker"], {}).get(pos["buy_date"], pos["buy_price"])
                if sp <= 0: sp = pos["buy_price"]

            pl_pct = (sp - pos["buy_price"]) / pos["buy_price"] * 100
            if sp > pos.get("peak", pos["buy_price"]):
                pos["peak"] = sp

            sell = False; reason = ""

            if pl_pct <= STOP_LOSS_PCT:
                sell = True; reason = f"停損({pl_pct:.0f}%)"
            elif "peak" in pos:
                dd = (sp - pos["peak"]) / pos["peak"] * 100
                if dd <= TRAIL_STOP_PCT:
                    sell = True; reason = f"移動停利({dd:.0f}%)"
            if not sell:
                days = (pd.Timestamp(date) - pd.Timestamp(pos["buy_date"])).days
                sig = stock_sigs.get(pos["ticker"], {}).get(date, {})
                rsi = sig.get("rsi14", 50) if isinstance(sig, dict) else 50
                if days >= 5 and rsi < RSI_EXIT:
                    sell = True; reason = f"RSI<{RSI_EXIT}"
            if not sell and pl_pct >= TAKE_PROFIT_50 and not pos.get("sold_half"):
                pos["sold_half"] = True
                half = pos["shares"] // 2
                if half > 0:
                    cash += half * sp
                    pos["shares"] -= half
                    trades.append({
                        "ticker": pos["ticker"], "buy_date": pos["buy_date"],
                        "buy_price": round(pos["buy_price"], 2), "sell_date": date,
                        "sell_price": round(sp, 2), "shares": half,
                        "pl": round(half * (sp - pos["buy_price"]), 2),
                        "pl_pct": round((sp - pos["buy_price"]) / pos["buy_price"] * 100, 2),
                        "sell_reason": "停利50%"
                    })

            if sell:
                cash += pos["shares"] * sp
                trades.append({
                    "ticker": pos["ticker"], "buy_date": pos["buy_date"],
                    "buy_price": round(pos["buy_price"], 2), "sell_date": date,
                    "sell_price": round(sp, 2), "shares": pos["shares"],
                    "pl": round(pos["shares"] * (sp - pos["buy_price"]), 2),
                    "pl_pct": round((sp - pos["buy_price"]) / pos["buy_price"] * 100, 2),
                    "sell_reason": reason
                })
                positions.remove(pos)

        existing = {p["ticker"] for p in positions}
        if not (is_bullish and trend_up):
            for t, sc, _ in candidates[:MAX_POSITIONS]:
                if t not in existing:
                    missed_trades.append({"date": date, "ticker": t, "reason": "大盤非多頭", "score": sc})
            pv = sum(p["shares"] * (price_lookup.get(p["ticker"], {}).get(date, p["buy_price"]) or p["buy_price"]) for p in positions)
            equity_curve.append({"date": date, "equity": round(cash + pv, 2), "type": "hold"})
            continue

        slots = min(MAX_POSITIONS - len(positions), MAX_DAILY_ENTRIES)
        for ticker, score, cp in candidates:
            if slots <= 0: break
            if ticker in existing: continue
            if cp <= 0: continue
            shares = math.floor(POSITION_SIZE / cp)
            cost = shares * cp
            if cost <= 0 or cost > cash: continue
            cash -= cost
            positions.append({"ticker": ticker, "shares": shares, "buy_price": cp, "buy_date": date, "peak": cp})
            slots -= 1

        pv = sum(p["shares"] * (price_lookup.get(p["ticker"], {}).get(date, p["buy_price"]) or p["buy_price"]) for p in positions)
        equity_curve.append({"date": date, "equity": round(cash + pv, 2), "type": "daily"})

    for pos in list(positions):
        ld = all_dates[-1]
        sp = price_lookup.get(pos["ticker"], {}).get(ld, 0)
        if sp <= 0:
            sp = price_lookup.get(pos["ticker"], {}).get(pos["buy_date"], pos["buy_price"])
            if sp <= 0: sp = pos["buy_price"]
        cash += pos["shares"] * sp
        trades.append({
            "ticker": pos["ticker"], "buy_date": pos["buy_date"],
            "buy_price": round(pos["buy_price"], 2), "sell_date": ld + " (年終)",
            "sell_price": round(sp, 2), "shares": pos["shares"],
            "pl": round(pos["shares"] * (sp - pos["buy_price"]), 2),
            "pl_pct": round((sp - pos["buy_price"]) / pos["buy_price"] * 100, 2),
            "sell_reason": "年終結算"
        })
    positions.clear()

    final_equity = cash
    total_return_pct = round((final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2)

    summary = {
        "year": year,
        "stocks_with_signals": len(set(t["ticker"] for t in trades)) if trades else 0,
        "trade_count": len(trades),
        "total_pl": round(final_equity - INITIAL_CAPITAL, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": total_return_pct,
        "trade_win_rate": round(len([t for t in trades if t["pl"] > 0]) / len(trades) * 100, 1) if trades else 0,
        "missed_trades": len(missed_trades),
        "elapsed_s": round(time.time() - t0),
        "n_rows": n_total
    }

    if trades:
        output = {"trades": trades, "equity_curve": equity_curve, "missed_trades": missed_trades}
        with open(os.path.join(OUT_DIR, f"{year}_trades_{VERSION}.json"), "w") as fout:
            json.dump(output, fout, indent=2)

    print(f"📅 {year}: {summary['stocks_with_signals']} stocks, {len(trades)} trades, "
          f"Return={total_return_pct:+.2f}%, Equity={final_equity:+.0f}, "
          f"missed={len(missed_trades)} ({summary['elapsed_s']}s)", flush=True)

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
                print(f"  ✓ {r['year']} done", flush=True)

    all_summary.sort(key=lambda s: s["year"])
    with open(os.path.join(OUT_DIR, f"summary_{VERSION}.json"), "w") as f:
        json.dump(all_summary, f, indent=2)

    print("\n📊 v12 趨勢拉回買+品質門檻 回測摘要")
    print(f"{'Year':>6} {'Stocks':>8} {'Trades':>8} {'Return%':>10} {'Equity':>12} {'WinRate':>8} {'Missed':>8}")
    for s in all_summary:
        print(f"{s['year']:>6} {s['stocks_with_signals']:>8} {s['trade_count']:>8} "
              f"{s['total_return_pct']:>+9.2f}% {s['final_equity']:>10,.0f} {s['trade_win_rate']:>6.1f}% {s['missed_trades']:>6}")

    pos_years = len([s for s in all_summary if s["total_return_pct"] > 0])
    best = max(all_summary, key=lambda s: s["total_return_pct"])
    worst = min(all_summary, key=lambda s: s["total_return_pct"])
    avg = sum(s["total_return_pct"] for s in all_summary) / len(all_summary)

    print(f"\n{'='*60}")
    print(f"策略: 加分≥2 + 每日2筆 + 無排名輪動 + 停損-15%/移動停利-15%/RSI<35出場")
    print(f"初始資金: 1,000,000 | 持倉上限: 10檔 | 個股下限: NT$10 | 日量: ≥1000")
    print(f"{'='*60}")
    print(f"年均報酬率: {avg:>+10.2f}%")
    print(f"最佳年份:   {best['year']:>4} ({best['total_return_pct']:>+.2f}%)")
    print(f"最差年份:   {worst['year']:>4} ({worst['total_return_pct']:>+.2f}%)")
    print(f"正報酬年數: {pos_years}/{len(all_summary)}")
    print(f"{'='*60}")
    print(f"✅ v12 done!")


if __name__ == "__main__":
    main()
