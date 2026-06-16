import json, os, sys
from datetime import datetime


completed_years = {}
for y in range(2004, 2027):
    if os.path.exists(pf):
        with open(pf) as f:
            d = json.load(f)
        completed_years[y] = len(dts)

# load previous state
prev = {}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        prev = json.load(f)

new_completed = []
for y, count in completed_years.items():
    prev_count = prev.get(str(y), 0)
    if prev_count > 0 and count > prev_count and count >= 240:
        new_completed.append((y, count))
    elif prev_count == 0 and count >= 240:
        new_completed.append((y, count))

# save state
    json.dump({str(k): v for k, v in completed_years.items()}, f)

if new_completed:
else:
    # also check if the latest year progress changed recently
    latest = max(completed_years.keys()) if completed_years else 0
    if latest:
        lc = completed_years[latest]
        lc_prev = prev.get(str(latest), 0)
        if lc != lc_prev and lc < 240:
        else:
    else:
