from __future__ import annotations
import json, os, sys, math, time
import pandas as pd
import numpy as np
from indicators import macd, dmi, wr, rsi, n2

os.makedirs(CHART_DIR, exist_ok=True)

# Load signal stocks
with open(JSON_PATH) as f:
    data = json.load(f)

if not missing:
    sys.exit(0)

# Build signal lookup
buy_map, sell_map = {}, {}

df = pd.read_parquet(
    ADJUSTED_PATH,
)

def _r(val, nd=2):
    try:
        v = float(val)
        return round(v, nd) if not (np.isnan(v) or math.isnan(v)) else None
    except: return None

def _round(val, nd=2):
    try: return round(float(val), nd)
    except: return 0.0

t0 = time.time()
for idx, ticker in enumerate(missing_tickers):
    t1 = time.time()
    if sub.empty:
        continue


    m = macd(close, 12, 26, 9)
    d = dmi(high, low, close, 14)

    stock_rows = []
    for _, row in sub.iterrows():
        stock_rows.append({
        })

    # 0050
    taiex_rows = []
    if not tx.empty:
        for _, row in tx.iterrows():
            taiex_rows.append({
            })

    # P&L
    buys = buy_map.get(ticker, [])
    sells = sell_map.get(ticker, [])
    for d_str in sorted(set(buys) | set(sells)):
        if d_str in pm:
            p = pm[d_str]
            if d_str in buys and not holding:
                holding, ep, ed = True, p, d_str
            elif d_str in sells and holding:
                holding = False
    return_rate = round(total_pl/total_cost*100,2) if total_cost > 0 else 0.0

    chart_data = {
    }
    elapsed = time.time() - t1

total = time.time() - t0
