import os, sys, time
import pandas as pd
import numpy as np

year = 2024

# Method: read yearly merged parquet directly
t0 = time.time()
df = pd.read_parquet(p)

# Read adjusted from adjusted_all.parquet with ticker filter
t0 = time.time()
# Filter after load

# Read adjusted with predicate pushdown
t0 = time.time()
