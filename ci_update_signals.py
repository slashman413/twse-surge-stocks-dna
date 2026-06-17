#!/usr/bin/env python3
"""
CI daily signal updater ? twse-surge-stocks-dna
Reads docs/charts/*.json, fetches TWSE prices, updates signals_data.json
Does NOT commit chart files (too many). Only commits signals_data.json.
"""
import json, ssl, sys
from datetime import date, datetime
from pathlib import Path
import urllib.request
import numpy as np

CHARTS_DIR  = Path("docs/charts")
SIGNALS_FILE = Path("docs/yearly_backtests/signals_data.json")
TODAY = date.today().isoformat()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        return json.loads(r.read())

def fetch_prices():
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

def rsi14(closes):
    arr = np.array(closes[-30:], dtype=float)
    if len(arr) < 15: return 50.0
    d = np.diff(arr)
    ag = np.where(d>0,d,0.)[:14].mean()
    al = np.where(d<0,-d,0.)[:14].mean()
    for gi,li in zip(np.where(d>0,d,0.)[14:], np.where(d<0,-d,0.)[14:]):
        ag=(ag*13+gi)/14; al=(al*13+li)/14
    return round(100-100/(1+ag/al), 2) if al else 100.0

def dist_ma20(closes):
    arr = np.array(closes[-20:], dtype=float)
    if len(arr) < 10: return 0.0
    ma = arr.mean()
    return round((arr[-1]-ma)/ma*100, 2) if ma else 0.0

def load_closes(ticker):
    f = CHARTS_DIR / (ticker + ".json")
    if not f.exists(): return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return [r["c"] for r in data.get("stock", []) if r.get("c") and r["c"] > 0]
    except: return []

def taiex_bullish():
    for f in sorted(CHARTS_DIR.glob("0050.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            closes = [r["c"] for r in data.get("taiex", [])[-100:] if r.get("c")]
            if len(closes) >= 60:
                return bool(closes[-1] > np.mean(closes[-60:]))
        except: pass
    return True

def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Fetching prices for {TODAY}...")
    prices = fetch_prices()
    if not prices:
        print("No price data ? non-trading day?"); sys.exit(0)
    print(f"  Got {len(prices)} stocks")

    signals_data = json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
    existing = signals_data.get("signals", [])

    # Update existing signals
    updated = []
    for sig in existing:
        ticker = sig.get("ticker","")
        price  = prices.get(ticker)
        if price is None:
            updated.append(sig)
            continue
        closes = load_closes(ticker)
        closes_with_today = closes + [price] if closes else [price]
        d20 = dist_ma20(closes_with_today)
        r14 = rsi14(closes_with_today)
        # Exit if price drops well below MA20
        if d20 < -5 or r14 < 35:
            print(f"  EXIT {ticker}: dist_ma20={d20:.1f}% rsi14={r14:.1f}")
            continue
        sig = sig.copy()
        sig["close"]     = price
        sig["dist_ma20"] = d20
        sig["rsi14"]     = r14
        updated.append(sig)

    signals_data["date"]          = TODAY
    signals_data["market_bullish"] = taiex_bullish()
    signals_data["signals"]       = updated
    SIGNALS_FILE.write_text(json.dumps(signals_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Kept {len(updated)}/{len(existing)} signals | market_bullish={signals_data['market_bullish']}")

if __name__ == "__main__":
    main()
