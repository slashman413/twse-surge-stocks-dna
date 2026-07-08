#!/usr/bin/env python3
"""
CI daily signal updater — twse-surge-stocks-dna
================================================
Reads live_kline.json for historical closes, fetches TWSE prices,
computes proper market assessment (same logic as ci_scan.py),
updates ALL market fields + signals in signals_data.json.

Output:
  - docs/yearly_backtests/signals_data.json  — updated signals + market
"""
import json, ssl, sys, os
from datetime import date, datetime
from pathlib import Path
import urllib.request
import numpy as np
import pandas as pd
import yfinance as yf

CHARTS_DIR    = Path("docs/charts")
SIGNALS_DIR   = Path("docs/yearly_backtests")
SIGNALS_FILE  = SIGNALS_DIR / "signals_data.json"
LIVE_KLINE    = SIGNALS_DIR / "live_kline.json"
TODAY         = date.today().isoformat()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE


# ═══════════════════════════════════════════════════════════════
# Data fetching
# ═══════════════════════════════════════════════════════════════

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        return json.loads(r.read())


def fetch_prices():
    """Get today's closing prices from TWSE OpenAPI (fallback RWD)."""
    try:
        rows = fetch_json("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
        if not rows: raise ValueError("empty")
        prices = {}
        for row in rows:
            try:
                prices[row["Code"]] = float(row["ClosingPrice"].replace(",",""))
            except: pass
        return prices
    except Exception as e:
        print(f"  OpenAPI failed: {e}, trying RWD...")
    try:
        d = date.today().strftime("%Y%m%d")
        rwd = fetch_json(f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json&date={d}")
        rows = rwd.get("data", [])
        return {str(r[0]).strip(): float(str(r[7]).replace(",","")) for r in rows if len(r) >= 8}
    except Exception as e2:
        print(f"  RWD also failed: {e2}")
        return {}


# ═══════════════════════════════════════════════════════════════
# Fix 5: Historical close prices from live_kline.json (fresh scan data)
#         Fall back to docs/charts/*.json if not found
# ═══════════════════════════════════════════════════════════════

def load_live_kline_cache():
    """Load live_kline.json into a {ticker: [closes]} cache."""
    if not LIVE_KLINE.exists():
        return {}
    try:
        data = json.loads(LIVE_KLINE.read_text(encoding="utf-8"))
        cache = {}
        for ticker, entry in data.items():
            kline = entry.get("kline", [])
            closes = [r["c"] for r in kline if r.get("c") and r["c"] > 0]
            if closes:
                cache[ticker] = closes
        return cache
    except Exception:
        return {}


def load_closes(ticker, live_cache=None):
    """
    Primary: read close prices from live_kline.json (fresh scan data).
    Fallback: read from docs/charts/{ticker}.json (pre-generated).
    """
    # Try live_kline cache first (most recent scan data)
    if live_cache is not None and ticker in live_cache:
        return live_cache[ticker]

    # Fallback to chart files
    f = CHARTS_DIR / (ticker + ".json")
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return [r["c"] for r in data.get("stock", []) if r.get("c") and r["c"] > 0]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# Indicator helpers (same as ci_scan.py)
# ═══════════════════════════════════════════════════════════════

def safe_last(arr, default=0.0):
    if arr is None or (hasattr(arr, "empty") and arr.empty):
        return default
    vals = pd.Series(arr).dropna()
    return float(vals.iloc[-1]) if len(vals) > 0 else default


def macd_dif(close: pd.Series, fast=12, slow=26) -> pd.Series:
    return close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()


def macd_full(close: pd.Series, fast=12, slow=26, signal=9):
    dif = macd_dif(close, fast, slow)
    dea = dif.ewm(span=signal, adjust=False).mean()
    histogram = dif - dea
    return {"dif": dif, "dea": dea, "histogram": histogram}


def rsi(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def dmi(high: pd.Series, low: pd.Series, close: pd.Series, period=14):
    h = high.values; l = low.values; c = close.values
    n = len(h)
    up = np.zeros(n); down = np.zeros(n)
    for i in range(1, n):
        up_ = h[i] - h[i-1]
        down_ = l[i-1] - l[i]
        if up_ > 0 and up_ > down_: up[i] = up_
        if down_ > 0 and down_ > up_: down[i] = down_
    tr = np.maximum(h - l, np.abs(h - np.roll(c, 1)))
    tr = np.maximum(tr, np.abs(l - np.roll(c, 1)))
    tr[tr <= 0] = np.nan
    atr = pd.Series(tr).ewm(span=period, adjust=False).mean().values
    up_ema = pd.Series(up).ewm(span=period, adjust=False).mean().values
    down_ema = pd.Series(down).ewm(span=period, adjust=False).mean().values
    pdi = up_ema / np.maximum(atr, 1e-10) * 100
    mdi = down_ema / np.maximum(atr, 1e-10) * 100
    dx = np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-10) * 100
    adx = pd.Series(dx).ewm(span=period, adjust=False).mean().values
    return {"adx": pd.Series(adx), "+di": pd.Series(pdi), "-di": pd.Series(mdi)}


def wr(high, low, close, period=14) -> pd.Series:
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return (hh - close) / (hh - ll).replace(0, np.nan) * -100


# ═══════════════════════════════════════════════════════════════
# Fix 8: Proper market assessment (same logic as ci_scan.py)
# ═══════════════════════════════════════════════════════════════

def assess_market(taiex: pd.DataFrame) -> dict:
    close = taiex["Close"]
    n = len(close)

    # DIF210
    dif210 = macd_dif(close, fast=200, slow=209)
    dif210_now = safe_last(dif210, 0.0)

    # ADX300
    dm = dmi(taiex["High"], taiex["Low"], close, period=300)
    adx300 = safe_last(dm["adx"], 0.0)

    # W%R50
    wr50 = safe_last(wr(taiex["High"], taiex["Low"], close, period=50), -50.0)

    # RSI60
    rsi60_val = safe_last(rsi(close, 60), 50.0)

    # MACD四箭頭
    m = macd_full(close)
    dif_now = safe_last(m["dif"], 0.0)
    dif_prev = safe_last(m["dif"].shift(1), 0.0)
    hist_now = safe_last(m["histogram"], 0.0)
    hist_prev = safe_last(m["histogram"].shift(1), 0.0)

    score = 0
    arrows = 0
    reasons = []

    if dif210_now > 0:
        score += 25
        reasons.append(f"DIF210={dif210_now:.0f}>0")
    else:
        reasons.append(f"DIF210={dif210_now:.0f}<0")

    if dif_now > 0: arrows += 1
    if dif_now > dif_prev: arrows += 1
    if hist_now > 0: arrows += 1
    if hist_now > hist_prev: arrows += 1
    score += arrows * 8
    if arrows >= 3:
        score += 10
        reasons.append(f"MACD四箭頭={arrows}")

    if adx300 > 30:
        score += 15
        reasons.append(f"ADX300={adx300:.0f}")
    elif adx300 > 20:
        score += 5

    if wr50 > -50:
        score += 10
        reasons.append(f"W%R50={wr50:.0f}")

    if rsi60_val > 50:
        score += 10
        reasons.append(f"RSI60={rsi60_val:.0f}")
    if rsi60_val > 80:
        score -= 10
        reasons.append(f"RSI60過熱={rsi60_val:.0f}")

    market_bullish = score >= 40
    market_crash = dif210_now < -300 and rsi60_val < 35
    market_trend_up = dif_now > 0 and adx300 > 20

    return {
        "score": score,
        "arrows": arrows,
        "dif210": round(float(dif210_now), 1),
        "adx300": round(float(adx300), 1),
        "rsi60": round(float(rsi60_val), 1),
        "wr50": round(float(wr50), 1),
        "market_bullish": market_bullish,
        "market_crash": market_crash,
        "market_trend_up": market_trend_up,
        "reasons": reasons[:6],
        "taiex_close": safe_last(close, 0.0),
    }


# ═══════════════════════════════════════════════════════════════
# Signal update helpers
# ═══════════════════════════════════════════════════════════════

def rsi14_from_closes(closes):
    arr = np.array(closes[-30:], dtype=float)
    if len(arr) < 15: return 50.0
    d = np.diff(arr)
    ag = np.where(d>0,d,0.)[:14].mean()
    al = np.where(d<0,-d,0.)[:14].mean()
    for gi,li in zip(np.where(d>0,d,0.)[14:], np.where(d<0,-d,0.)[14:]):
        ag=(ag*13+gi)/14; al=(al*13+li)/14
    return round(100-100/(1+ag/al), 2) if al else 100.0


def dist_ma20_from_closes(closes):
    arr = np.array(closes[-20:], dtype=float)
    if len(arr) < 10: return 0.0
    ma = arr.mean()
    return round((arr[-1]-ma)/ma*100, 2) if ma else 0.0


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Fetching prices for {TODAY}...")
    prices = fetch_prices()
    if not prices:
        print("No price data — non-trading day?"); sys.exit(0)
    print(f"  Got {len(prices)} stocks")

    # Build live_kline close cache (Fix 5)
    print("  Loading live_kline.json cache...")
    live_cache = load_live_kline_cache()
    print(f"    Cached {len(live_cache)} stocks from live_kline.json")

    # Download ^TWII for market assessment (Fix 8)
    print("  Downloading ^TWII for market assessment...")
    try:
        twii = yf.download("^TWII", period="3y", auto_adjust=True, progress=False)
        if not twii.empty:
            twii.columns = [c[0] if isinstance(c, tuple) else c for c in twii.columns]
            market = assess_market(twii)
            print(f"    Market score={market['score']} bullish={market['market_bullish']} crash={market['market_crash']}")
            for r in market["reasons"]:
                print(f"      • {r}")
        else:
            print("    ^TWII download empty, using cached market data")
            market = None
    except Exception as e:
        print(f"    ^TWII download failed: {e}, using cached market data")
        market = None

    # Read existing signals
    signals_data = json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
    existing = signals_data.get("signals", [])

    # Update existing signals
    updated = []
    for sig in existing:
        ticker = sig.get("ticker", "")
        price  = prices.get(ticker)
        if price is None:
            updated.append(sig)
            continue

        closes = load_closes(ticker, live_cache)
        closes_with_today = closes + [price] if closes else [price]
        d20 = dist_ma20_from_closes(closes_with_today)
        r14 = rsi14_from_closes(closes_with_today)

        if d20 < -5 or r14 < 35:
            print(f"  EXIT {ticker}: dist_ma20={d20:.1f}% rsi14={r14:.1f}")
            continue

        sig = sig.copy()
        sig["close"]     = price
        sig["dist_ma20"] = d20
        sig["rsi14"]     = r14
        updated.append(sig)

    # Fix 2: Update ALL market fields (not just date + market_bullish)
    signals_data["date"]   = TODAY
    signals_data["signals"] = updated

    if market is not None:
        signals_data["market_bullish"]  = market["market_bullish"]
        signals_data["market_crash"]    = market["market_crash"]
        signals_data["market_trend_up"] = market["market_trend_up"]
        signals_data["market_score"]    = market["score"]
        signals_data["taiex_close"]     = market["taiex_close"]
        signals_data["reasons"]         = market["reasons"]
        signals_data["market_assessment"] = market

    # Write back
    SIGNALS_FILE.write_text(
        json.dumps(signals_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  Kept {len(updated)}/{len(existing)} signals | "
          f"market_score={signals_data.get('market_score', '?')} | "
          f"bullish={signals_data.get('market_bullish', '?')}")


if __name__ == "__main__":
    main()
