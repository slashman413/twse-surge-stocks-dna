# Test backtest speed
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import TWSEStockLoader
from backtest import run_backtest

loader = TWSEStockLoader()
tickers = [t for t in loader.list_available_tickers() if t.isdigit() and len(t) == 4]
print(f'Total stocks: {len(tickers)}', flush=True)

sample = tickers[:50]
t0 = time.time()
for i, t in enumerate(sample, 1):
    r = run_backtest(t, 2024, 2024)
    if i % 10 == 0:
        print(f'   {i}/{len(sample)} stocks, {time.time()-t0:.0f}s', flush=True)
print(f'50 stocks 2024: {time.time()-t0:.0f}s', flush=True)
