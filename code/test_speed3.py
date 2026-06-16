import os, sys, time
from backtest import run_backtest

# Test a few different stocks
for t, y in tests:
    t1 = time.time()
    r = run_backtest(t, y, y)
