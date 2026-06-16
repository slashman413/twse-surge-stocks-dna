import os, sys, time
from data_loader import TWSEStockLoader
from backtest import run_backtest

loader = TWSEStockLoader()
tickers = [t for t in loader.list_available_tickers() if t.isdigit() and len(t) == 4]

sample = tickers[:50]
t0 = time.time()
for i, t in enumerate(sample, 1):
    r = run_backtest(t, 2024, 2024)
    if i % 10 == 0:
