import sys, os
import subprocess

missing = [2008, 2011, 2021, 2022, 2023, 2024, 2025, 2026]
for y in missing:
    r = subprocess.run(
        capture_output=True, text=True, timeout=600
    )
    if r.stderr:
    print(flush=True)
