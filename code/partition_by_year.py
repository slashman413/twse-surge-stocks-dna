import os, time, gc
import pyarrow.compute as pc
import pyarrow.parquet as pq

os.makedirs(DST, exist_ok=True)

from datetime import datetime

for year in range(2004, 2027):
    t0 = time.time()
    if os.path.exists(out):
        sz = os.path.getsize(out) / (1024*1024)
        continue

    # Use pq.read_table with row group filtering — pass actual timestamps
    start_ts = datetime(year, 1, 1)
    end_ts = datetime(year + 1, 1, 1) if year < 2026 else datetime(2027, 1, 1)

    table = pq.read_table(
        SRC,
        filters=[
        ]
    )
    n = len(table)
    if n == 0:
        continue

    sz = os.path.getsize(out) / (1024*1024)
    elapsed = time.time() - t0

    del table
    gc.collect()

