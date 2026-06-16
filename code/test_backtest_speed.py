#!/usr/bin/env python3
import os, sys, time

from data_loader import TWSEStockLoader
from backtest import run_backtest

loader = TWSEStockLoader()
tickers = [t for t in loader.list_available_tickers() if t.isdigit() and len(t) == 4]

# Test with first 100 stocks for 2024
sample = tickers[:100]
t0 = time.time()
count = 0
for t in sample:
    r = run_backtest(t, 2024, 2024)
        count += 1
    if (len(tickers) - len(sample) + sample.index(t) + 1) % 20 == 0:
        elapsed = time.time() - t0
        done = sample.index(t) + 1
