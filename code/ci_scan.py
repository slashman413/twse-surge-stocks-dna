"""
CI Daily Scan — yfinance-only, no local data dependency
=========================================================

Runs the TWSE scan in GitHub Actions using yfinance for all data.
Outputs:
  - docs/yearly_backtests/signals_data.json — live daily signals
  - docs/latest_scan.html — standalone scan report

Usage:
    python code/ci_scan.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd
import yfinance as yf

# ── Paths ──────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_DIR = os.path.join(REPO_ROOT, "docs", "yearly_backtests")
SIGNALS_FILE = os.path.join(SIGNALS_DIR, "signals_data.json")
KLINE_FILE   = os.path.join(SIGNALS_DIR, "kline_data.json")
HTML_FILE = os.path.join(REPO_ROOT, "docs", "latest_scan.html")
os.makedirs(SIGNALS_DIR, exist_ok=True)

# ── Watchlist ──────────────────────────────────────────────────
# TW50 + active stocks covering key sectors
WATCHLIST = [
    "2330", "2454", "2317", "2308", "2412",  # 權值電子
    "2881", "2882", "2886", "2891", "5880",  # 金融
    "2002", "1301", "1303", "1326",           # 傳產
    "3008", "3711", "8046", "2357", "2382",   # 高價電子
    "1101", "1216", "1402", "1504",           # 各類龍頭
    "2603", "3034", "3231", "2379", "2301", "2327",  # 電子中型
    "4904", "4938", "5347", "6239", "6269",
    "6446", "6669", "6732", "6742", "6770",
    "8016", "8299", "8454",
]

# ── Helpers ────────────────────────────────────────────────────


def safe_last(arr, default=0.0):
    """Get last non-NaN value from array-like."""
    if arr is None or (hasattr(arr, "empty") and arr.empty):
        return default
    vals = pd.Series(arr).dropna()
    return float(vals.iloc[-1]) if len(vals) > 0 else default


def macd_dif(close: pd.Series, fast=12, slow=26, signal=9) -> pd.Series:
    """Return MACD DIF line only."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow


def rsi(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def dmi(high: pd.Series, low: pd.Series, close: pd.Series, period=14):
    """Return ADX, +DI, -DI."""
    h = high.values
    l = low.values
    c = close.values
    n = len(h)
    up = np.zeros(n)
    down = np.zeros(n)
    for i in range(1, n):
        up[i] = h[i] - h[i - 1] if h[i] > h[i - 1] and (h[i] - h[i - 1]) > (l[i - 1] - l[i]) else 0
        down[i] = l[i - 1] - l[i] if l[i - 1] > l[i] and (l[i - 1] - l[i]) > (h[i] - h[i - 1]) else 0
    tr = np.maximum(h - l, np.abs(h - np.roll(c, 1)))
    tr = np.maximum(tr, np.abs(l - np.roll(c, 1)))
    tr[tr <= 0] = np.nan
    atr = pd.Series(tr).ewm(span=period, adjust=False).mean().values
    up_ema = pd.Series(up).ewm(span=period, adjust=False).mean().values
    down_ema = pd.Series(down).ewm(span=period, adjust=False).mean().values
    pdi = up_ema / atr * 100
    mdi = down_ema / atr * 100
    dx = np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-10) * 100
    adx = pd.Series(dx).ewm(span=period, adjust=False).mean().values
    return {"adx": pd.Series(adx), "+di": pd.Series(pdi), "-di": pd.Series(mdi)}


# ── Market Assessment ──────────────────────────────────────────


def assess_market(taiex: pd.DataFrame) -> dict:
    """Assess market state from ^TWII data.

    Returns market assessment dict with state, score, and reason.
    """
    close = taiex["Close"]
    n = len(close)

    # DIF210 (200, 209, 210)
    dif = macd_dif(close, fast=200, slow=209, signal=210)
    dif_now = safe_last(dif, 0.0)

    # ADX 300
    dm = dmi(taiex["High"], taiex["Low"], close, period=300)
    adx_now = safe_last(dm["adx"], 0.0)

    # W%R 50
    def wr50(high, low, close):
        hh = high.rolling(50).max()
        ll = low.rolling(50).min()
        wr = (hh - close) / (hh - ll).replace(0, np.nan) * -100
        return wr
    wr_val = safe_last(wr50(taiex["High"], taiex["Low"], close), -50.0)

    # RSI 60
    rsi60 = safe_last(rsi(close, 60), 50.0)

    # N2 (MACD 四箭頭)
    dif_s = macd_dif(close, fast=12, slow=26, signal=9)
    dif_prev = dif_s.iloc[-2] if n >= 2 else 0
    dif_pprev = dif_s.iloc[-3] if n >= 3 else 0

    # MACD 四箭頭: DIF > 0, DIF 向上, 柱狀體擴大
    macd_line = dif_s
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    hist_now = safe_last(histogram, 0.0)
    hist_prev = safe_last(histogram.iloc[:-1], 0.0) if n >= 2 else 0

    score = 0
    reasons = []

    # DIF210 > 0 (多頭基準)
    if dif_now > 0:
        score += 20
        reasons.append(f"DIF210={dif_now:.1f}>0")
    else:
        reasons.append(f"DIF210={dif_now:.1f}<0")

    # MACD 四箭頭
    arrows = 0
    if dif_now > 0:
        arrows += 1
    if n >= 2 and dif_now > dif_prev:
        arrows += 1
    if hist_now > 0:
        arrows += 1
    if hist_now > hist_prev:
        arrows += 1
    score += arrows * 10
    if arrows >= 3:
        score += 10
        reasons.append(f"MACD四箭頭={arrows}")

    # ADX 強度
    if adx_now > 30:
        score += 15
        reasons.append(f"ADX300={adx_now:.0f}>30")
    elif adx_now > 20:
        score += 5
        reasons.append(f"ADX300={adx_now:.0f}>20")

    # W%R 位置
    if wr_val > -50:
        score += 10
        reasons.append(f"W%R50={wr_val:.0f}>-50")

    # RSI 趨勢
    if rsi60 > 50:
        score += 10
        reasons.append(f"RSI60={rsi60:.0f}>50")

    if rsi60 > 80:
        score -= 10
        reasons.append(f"RSI60={rsi60:.0f}>80 過熱")

    # Determine state
    market_bullish = score >= 40
    market_crash = (dif_now < -500 and rsi60 < 30)
    market_trend_up = dif_now > 0 and adx_now > 20

    return {
        "score": score,
        "market_bullish": market_bullish,
        "market_crash": market_crash,
        "market_trend_up": market_trend_up,
        "reasons": reasons[:5],
        "taiex_close": safe_last(close, 0.0),
    }


# ── Stock Signal Evaluation ────────────────────────────────────


def evaluate_stock(ticker: str, df: pd.DataFrame, market: dict) -> dict | None:
    """Evaluate a single stock for buy/sell signals.

    Returns signal dict or None if data insufficient.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(close)

    if n < 200:
        return None

    # MACD setup
    dif = macd_dif(close)
    dif_now = safe_last(dif, 0.0)
    signal_line = dif.ewm(span=9, adjust=False).mean()
    hist_now = safe_last(dif - signal_line, 0.0)

    # DMI
    dm = dmi(high, low, close, period=14)
    adx = safe_last(dm["adx"], 0.0)
    pdi = safe_last(dm["+di"], 0.0)
    mdi = safe_last(dm["-di"], 0.0)

    # RSI
    rsi14 = safe_last(rsi(close, 14), 50.0)

    # W%R
    hh14 = high.rolling(14).max()
    ll14 = low.rolling(14).min()
    wr14 = safe_last((hh14 - close) / (hh14 - ll14).replace(0, np.nan) * -100, -50.0)

    # MA20 distance
    ma20 = close.rolling(20).mean()
    dist_ma20 = safe_last((close - ma20) / ma20 * 100, 0.0)

    # ── Buy signal conditions ──
    buy_score = 0
    buy_details = []

    # 1. MACD > 0 (DIF in positive territory)
    if dif_now > 0:
        buy_score += 15
        buy_details.append("MACD>0")

    # 2. ADX > 20 (trend strength)
    if adx > 20:
        buy_score += 10
        buy_details.append(f"ADX={adx:.0f}")

    # 3. +DI > -DI (bullish DMI)
    if pdi > mdi:
        buy_score += 10
        buy_details.append(f"+DI>{-mdi:.0f}")

    # 4. RSI 14 in 30-70 (not oversold/overbought)
    if 30 < rsi14 < 70:
        buy_score += 10
        buy_details.append(f"RSI={rsi14:.0f}")

    # 5. Near MA20 (pullback)
    if -3 < dist_ma20 < 2:
        buy_score += 15
        buy_details.append(f"MA20={dist_ma20:+.1f}%")

    # 6. WR not overbought
    if wr14 < -20:
        buy_score += 10
        buy_details.append(f"W%R={wr14:.0f}")

    # 7. Market bullish bonus
    if market.get("market_bullish") and market.get("market_trend_up"):
        buy_score += 20
        buy_details.append("大盤多頭")

    # ── Sell signal conditions ──
    sell_score = 0
    sell_details = []

    if dif_now < 0:
        sell_score += 15
        sell_details.append("MACD<0")
    if adx > 25 and mdi > pdi:
        sell_score += 15
        sell_details.append(f"ADX+{-mdi:.0f}>+{pdi:.0f}")
    if rsi14 > 75:
        sell_score += 10
        sell_details.append("RSI過熱")
    if wr14 > -20:
        sell_score += 10
        sell_details.append("W%R過熱")
    if dist_ma20 > 15:
        sell_score += 10
        sell_details.append("乖離過大")

    # Determine signal
    is_buy = buy_score >= 40
    is_sell = sell_score >= 30

    if is_buy and not is_sell:
        signal = "BUY"
        quality = min(buy_score, 100)
        bonus = sum(1 for _ in buy_details[:3])
    elif is_sell and not is_buy:
        signal = "SELL"
        quality = min(sell_score, 100)
        bonus = 0
    else:
        return None

    return {
        "ticker": ticker,
        "name": "",
        "date": str(df["Date"].iloc[-1].date()) if hasattr(df["Date"].iloc[-1], "date") else str(df.index[-1].date()),
        "score": round(buy_score if is_buy else -sell_score, 1),
        "close": round(float(close.iloc[-1]), 2),
        "dist_ma20": round(dist_ma20, 2),
        "rsi14": round(rsi14, 2),
        "quality": quality,
        "bonus": bonus,
        "signal": signal,
        "details": buy_details if is_buy else sell_details,
    }


# ── Name Lookup ────────────────────────────────────────────────


def fetch_names(tickers: list[str]) -> dict[str, str]:
    """Fetch Chinese stock names from yfinance."""
    names = {}
    for t in tickers:
        try:
            tk = yf.Ticker(f"{t}.TW")
            info = tk.info
            n = info.get("longName") or info.get("shortName") or t
            # Strip Taiwan stock suffix like "Co., Ltd."
            names[t] = str(n)
        except Exception:
            names[t] = t
    return names




# -- KLine Data Generation ------------------------------------------


def generate_kline_data(stocks_data: dict) -> None:
    """Generate kline_data.json for dashboard K-line charts from yfinance data."""
    import math

    def safe_round(v, d=2):
        try:
            f = float(v)
            return None if math.isnan(f) else round(f, d)
        except Exception:
            return None

    kline_out = {}
    for ticker, df in stocks_data.items():
        close = df["Close"]
        high  = df["High"]
        low   = df["Low"]
        vol   = df["Volume"]

        ma20     = close.rolling(20).mean()
        ma50     = close.rolling(50).mean()
        rsi14    = rsi(close, 14)
        rsi60    = rsi(close, 60)
        vol_ma20 = vol.rolling(20).mean()
        dm       = dmi(high, low, close, 14)
        dist_20  = (close - ma20) / ma20 * 100
        dist_50  = (close - ma50) / ma50 * 100

        kline = []
        for i in range(len(df)):
            try:
                d_raw = df["Date"].iloc[i]
                d = str(d_raw.date()) if hasattr(d_raw, "date") else str(d_raw)[:10]
                kline.append({
                    "d":        d,
                    "o":        safe_round(df["Open"].iloc[i]),
                    "h":        safe_round(high.iloc[i]),
                    "l":        safe_round(low.iloc[i]),
                    "c":        safe_round(close.iloc[i]),
                    "v":        int(vol.iloc[i]) if not math.isnan(float(vol.iloc[i])) else 0,
                    "ma20":     safe_round(ma20.iloc[i]),
                    "ma50":     safe_round(ma50.iloc[i]),
                    "rsi14":    safe_round(rsi14.iloc[i], 1),
                    "rsi60":    safe_round(rsi60.iloc[i], 1),
                    "adx":      safe_round(dm["adx"].iloc[i], 1),
                    "pdi":      safe_round(dm["+di"].iloc[i], 1),
                    "mdi":      safe_round(dm["-di"].iloc[i], 1),
                    "vol_ma20": int(vol_ma20.iloc[i]) if not math.isnan(float(vol_ma20.iloc[i])) else None,
                    "dist_ma20": safe_round(dist_20.iloc[i]),
                    "dist_ma50": safe_round(dist_50.iloc[i]),
                })
            except Exception:
                pass

        kline_out[ticker] = {
            "ticker":  ticker,
            "m_rsi4":  safe_round(rsi14.iloc[-1], 1) or 0,
            "m_adx1":  safe_round(dm["adx"].iloc[-1], 1) or 0,
            "kline":   kline,
        }

    with open(KLINE_FILE, "w", encoding="utf-8") as f:
        json.dump(kline_out, f, ensure_ascii=False, separators=(",", ":"))
    total_pts = sum(len(v["kline"]) for v in kline_out.values())
    print(f"\u2705 Saved kline_data.json: {len(kline_out)} stocks, {total_pts} data points")

# ── Main ───────────────────────────────────────────────────────


def main():
    today = date.today()
    print(f"🔍 TWSE Daily Scan — {today}")
    print(f"    Target: {SIGNALS_FILE}")

    # ── 1. Download market index ──
    print("\n📊 Downloading market index (^TWII)...")
    twii = yf.download(
        "^TWII",
        period="3y",
        auto_adjust=True,
        progress=False,
    )
    if twii.empty:
        print("❌ Failed to download ^TWII")
        sys.exit(1)

    twii.columns = [c[0] if isinstance(c, tuple) else c for c in twii.columns]
    twii = twii.reset_index()
    market = assess_market(twii)
    print(f"    Market score: {market['score']}")
    print(f"    Bullish: {market['market_bullish']}, Crash: {market['market_crash']}")
    for r in market["reasons"]:
        print(f"      • {r}")

    # ── 2. Download stock data ──
    print(f"\n📈 Downloading {len(WATCHLIST)} stocks from yfinance...")
    stocks_data = {}
    for ticker in WATCHLIST:
        try:
            df = yf.download(
                f"{ticker}.TW",
                period="1y",
                auto_adjust=True,
                progress=False,
            )
            if df.empty:
                continue
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.reset_index()
            stocks_data[ticker] = df
        except Exception:
            continue

    print(f"    Loaded {len(stocks_data)} stocks")

    # ── 2.5. Generate kline data ──
    generate_kline_data(stocks_data)

    # ── 3. Evaluate signals ──
    print("\n🔍 Evaluating signals...")
    signals = []
    for ticker, df in stocks_data.items():
        sig = evaluate_stock(ticker, df, market)
        if sig:
            signals.append(sig)

    # Sort by score descending
    signals.sort(key=lambda s: s["score"], reverse=True)

    # ── 4. Fetch names ──
    print("\n🏷️  Fetching stock names...")
    names = fetch_names([s["ticker"] for s in signals])
    for s in signals:
        s["name"] = names.get(s["ticker"], s["ticker"])

    # ── 5. Save signals_data.json ──
    output = {
        "date": today.isoformat(),
        "market_bullish": market["market_bullish"],
        "market_crash": market["market_crash"],
        "market_trend_up": market["market_trend_up"],
        "market_score": market["score"],
        "taiex_close": market["taiex_close"],
        "reasons": market["reasons"],
        "scanned_count": len(stocks_data),
        "signals": signals[:20],
    }

    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved {len(signals)} signals to {SIGNALS_FILE}")
    buy_count = sum(1 for s in signals if s["signal"] == "BUY")
    sell_count = sum(1 for s in signals if s["signal"] == "SELL")
    print(f"    BUY: {buy_count}, SELL: {sell_count}")

    # ── 6. Generate HTML report ──
    generate_html(output, names, today)

    print("\n✅ CI scan complete")


def generate_html(output: dict, names: dict[str, str], scan_date: date):
    """Generate standalone HTML scan report."""
    signals = output["signals"]
    market = {
        "score": output["market_score"],
        "bullish": output["market_bullish"],
        "crash": output["market_crash"],
        "trend_up": output["market_trend_up"],
        "taiex_close": output["taiex_close"],
        "reasons": output.get("reasons", []),
    }

    market_status = "🟢 多頭" if market["bullish"] else "🔴 空頭"
    market_color = "#22c55e" if market["bullish"] else "#ef4444"
    if market["crash"]:
        market_status = "💀 崩盤"
        market_color = "#dc2626"

    buy_rows = ""
    sell_rows = ""
    for s in signals:
        if s["signal"] == "BUY":
            color = "#22c55e"
            sig_label = "🟢 BUY"
            details_html = "<br>".join(f"✅ {d}" for d in s.get("details", [])[:3])
            buy_rows += f"""
            <tr>
                <td style="font-weight:bold;color:{color}">{s['ticker']}</td>
                <td>{names.get(s['ticker'], s['ticker'])}</td>
                <td>{s['close']:,.2f}</td>
                <td>{s['score']:.1f}</td>
                <td>{s['rsi14']:.0f}</td>
                <td>{s['dist_ma20']:+.2f}%</td>
                <td>{details_html}</td>
            </tr>"""
        else:
            color = "#ef4444"
            details_html = "<br>".join(f"⚠️ {d}" for d in s.get("details", [])[:3])
            sell_rows += f"""
            <tr>
                <td style="font-weight:bold;color:{color}">{s['ticker']}</td>
                <td>{names.get(s['ticker'], s['ticker'])}</td>
                <td>{s['close']:,.2f}</td>
                <td>{s['score']:.1f}</td>
                <td>{s['rsi14']:.0f}</td>
                <td>{s['dist_ma20']:+.2f}%</td>
                <td>{details_html}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TWSE 每日掃描 — {scan_date}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0f172a; color: #e2e8f0; line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .subtitle {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px; }}
  .market-card {{
    padding: 16px; border-radius: 12px; margin-bottom: 16px;
    border: 1px solid #334155; background: #1e293b;
  }}
  .market-state {{
    display: inline-block; padding: 6px 16px; border-radius: 20px;
    color: white; font-weight: 700; font-size: 1.1rem;
  }}
  table {{
    width: 100%; border-collapse: collapse; margin-top: 8px;
    background: #1e293b; border-radius: 12px; overflow: hidden;
  }}
  th {{ text-align: left; padding: 10px 12px; background: #334155; font-size: 0.8rem; text-transform: uppercase; color: #94a3b8; }}
  td {{ padding: 8px 12px; border-top: 1px solid #334155; font-size: 0.85rem; }}
  tr:hover {{ background: rgba(51,65,85,0.4); }}
  .section-title {{ font-size: 1.1rem; margin: 20px 0 4px; }}
  .footer {{ text-align: center; margin-top: 32px; padding: 16px; color: #475569; font-size: 0.75rem; }}
  .reasons {{ font-size: 0.85rem; color: #94a3b8; margin-top: 8px; }}
  .reasons li {{ margin-left: 16px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 TWSE 量化每日掃描</h1>
  <div class="subtitle">{scan_date} ｜ 掃描 {output.get('scanned_count', 0)} 檔</div>

  <div class="market-card">
    <span class="market-state" style="background:{market_color}">{market_status}</span>
    <span style="margin-left:12px;font-size:0.9rem;color:var(--text-dim);">
      加權指數: {market['taiex_close']:,.0f} ｜ score: {market['score']}
    </span>
    <ol class="reasons">
      {''.join(f'<li>{r}</li>' for r in market['reasons'])}
    </ol>
  </div>

  <h2 class="section-title" style="color:#22c55e">🟢 建議買進 ({len(buy_rows > '' and signals or [])}檔)</h2>
  <table>
    <tr><th>代號</th><th>名稱</th><th>收盤</th><th>評分</th><th>RSI14</th><th>乖離MA20</th><th>條件</th></tr>
    {buy_rows or '<tr><td colspan="7" style="text-align:center;color:#475569;padding:20px;">無符合條件的買進訊號</td></tr>'}
  </table>

  <h2 class="section-title" style="color:#ef4444;margin-top:24px;">🔴 建議賣出 ({len(sell_rows > '' and signals or [])}檔)</h2>
  <table>
    <tr><th>代號</th><th>名稱</th><th>收盤</th><th>評分</th><th>RSI14</th><th>乖離MA20</th><th>條件</th></tr>
    {sell_rows or '<tr><td colspan="7" style="text-align:center;color:#475569;padding:20px;">無符合條件的賣出訊號</td></tr>'}
  </table>

  <div class="footer">
    Generated by hermes-agent-deepseek-v4-flash · TWSE Quant Screener · {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
  </div>
</div>
</body>
</html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Saved HTML report to {HTML_FILE}")


if __name__ == "__main__":
    main()
