#!/usr/bin/env python3

Usage: python run_yearly_backtest.py [--quick] [--year YYYY]
import os, sys, json, time


from data_loader import TWSEStockLoader
from backtest import run_backtest, generate_report
from datetime import date

os.makedirs(OUT_DIR, exist_ok=True)

loader = TWSEStockLoader()
tickers = loader.list_available_tickers()
tickers = [t for t in tickers if t.isdigit() and len(t) == 4]

years = list(range(2004, 2027))

yearly_results = []

for year in years:
    t0 = time.time()

    results = []
    for t in tickers:
        r = run_backtest(t, year, year)
        results.append(r)
        if (len(results) % 500) == 0:

    # Calculate yearly summary

    yearly_results.append({
    })

    # Save per-year report
    report = generate_report(results)
        f.write(report)


# Save summary JSON
summary = {
}
    json.dump(summary, f, ensure_ascii=False, indent=2)

