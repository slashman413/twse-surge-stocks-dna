import os, sys, time
import pandas as pd
import numpy as np
from data_loader import TWSEStockLoader, apply_backward_adjustment


year = 2024

# Method 1: old loader
t0 = time.time()
loader = TWSEStockLoader()

# Method 2: direct parquet read with predicate pushdown
t0 = time.time()

# Check they match
if not df2.empty:
