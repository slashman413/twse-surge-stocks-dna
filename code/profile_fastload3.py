import os, sys, time
import pyarrow.parquet as pq
import pandas as pd

year = 2024

# Use pyarrow to read with row group filtering
t0 = time.time()

# Read metadata to understand row groups
t0 = time.time()
meta = pf.metadata

# Read first row group to check
t0 = time.time()

# Try reading specific columns with filter
t0 = time.time()
t2 = t2.to_pandas()

# Filter
t0 = time.time()
