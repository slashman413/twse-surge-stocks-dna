import os, sys, time
from data_loader import TWSEStockLoader
from backtest import run_backtest

t0 = time.time()
loader = TWSEStockLoader()

tickers = [t for t in loader.list_available_tickers() if t.isdigit() and len(t) == 4]

# Test 1 stock
for t in tickers[:5]:
    t1 = time.time()
    r = run_backtest(t, 2024, 2024)

