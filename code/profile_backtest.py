import os, sys, time
from data_loader import TWSEStockLoader
from backtest import run_backtest

# Profile the key steps
from data_loader import TWSEStockLoader, apply_backward_adjustment
from strategy import BigStockBuySignalV2, BigStockSellSignalV2
import pandas as pd
import numpy as np

loader = TWSEStockLoader()

year = 2024

# Time data loading
t0 = time.time()

# Time resampling
t0 = time.time()
weekly = loader.resample_weekly(df)
monthly = loader.resample_monthly(df)

# Time indicator computation for one sample
from indicators import macd, dmi, wr, rsi, k6k9, vr

t0 = time.time()

# MACD DIF210
m = macd(close, fast=200, slow=209, signal=210)

t0 = time.time()
d = dmi(high, low, close, period=300)

t0 = time.time()
w = wr(high, low, close, 50)

t0 = time.time()
r = rsi(close, 60)

# Weekly indicators
t0 = time.time()
w_vr2 = vr(w_close, w_vol)

# Monthly indicators - K6K9
t0 = time.time()
mk = k6k9(m_high, m_low, m_close, m_open)

t0 = time.time()
m_rsi4 = rsi(m_close, 4)

t0 = time.time()
r = run_backtest(ticker, year, year)
