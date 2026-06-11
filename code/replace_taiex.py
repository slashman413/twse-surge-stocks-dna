"""Replace 0050 with real TAIEX (^TWII) in all chart JSON files."""
from __future__ import annotations
import json, os, sys, time
import yfinance as yf
import pandas as pd

CHART_DIR = "D:/twse-surge-stocks-dna/docs/charts"
charts = sorted(f for f in os.listdir(CHART_DIR) if f.endswith(".json"))

print(f"Loading ^TWII from yfinance...")
t = time.time()
twii = yf.Ticker("^TWII")
hist = twii.history(start="2004-01-01", end="2008-12-31")
hist.index = pd.to_datetime(hist.index).tz_localize(None)
print(f"Loaded {len(hist)} rows in {time.time()-t:.1f}s")

# Build price map
def _r(v, nd=2):
    try: return round(float(v), nd)
    except: return 0.0

taiex_rows = []
for dt, row in hist.iterrows():
    taiex_rows.append({
        "d": dt.strftime("%Y-%m-%d"),
        "o": _r(row["Open"]), "h": _r(row["High"]),
        "l": _r(row["Low"]), "c": _r(row["Close"]),
        "v": int(row["Volume"]),
    })
print(f"TAIEX rows: {len(taiex_rows)}")

t0 = time.time()
for idx, fname in enumerate(charts):
    path = os.path.join(CHART_DIR, fname)
    with open(path) as f:
        data = json.load(f)
    
    data["taiex"] = taiex_rows
    
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))
    
    if (idx + 1) % 50 == 0:
        print(f"[{idx+1}/{len(charts)}] updated")

print(f"Done! {len(charts)} charts updated in {time.time()-t0:.1f}s")
print(f"TAIEX data: {min(r['d'] for r in taiex_rows)} ~ {max(r['d'] for r in taiex_rows)}")
