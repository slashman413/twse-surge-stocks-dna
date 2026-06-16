"""將 TAIEX (加權指數) 資料寫入 chart JSON 檔案中。

用途：提供大盤走勢參考（已從 dashboard 獨立）。
"""

from __future__ import annotations
import json, os, sys, time
import yfinance as yf
import pandas as pd

CHART_DIR = r"D:\twse-surge-stocks-dna\docs\charts"

t = time.time()
hist = yf.Ticker("^TWII").history(period="max")
hist.index = pd.to_datetime(hist.index).tz_localize(None)


def _r(v, nd=2):
    try:
        return round(float(v), nd)
    except Exception:
        return 0.0


taiex_rows = []
for dt, row in hist.iterrows():
    taiex_rows.append({
        "date": dt.strftime("%Y-%m-%d"),
        "close": _r(row["Close"]),
        "high": _r(row["High"]),
        "low": _r(row["Low"]),
        "open": _r(row["Open"]),
        "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
    })

print(f"TAIEX: {len(taiex_rows)} 筆", flush=True)

t0 = time.time()
charts = [f for f in os.listdir(CHART_DIR) if f.endswith(".json") and "_" in f]

for idx, fname in enumerate(charts):
    path = os.path.join(CHART_DIR, fname)
    with open(path) as f:
        data = json.load(f)
    data["taiex"] = taiex_rows
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    if (idx + 1) % 50 == 0:
        print(f"  {idx+1}/{len(charts)} ({time.time()-t0:.0f}s)", flush=True)

print(f"✅ TAIEX 資料已寫入 {len(charts)} 檔 chart JSON ({time.time()-t:.0f}s)", flush=True)
