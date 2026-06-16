import os, sys, json, time
import yfinance as yf
import numpy as np
import pandas as pd


def get_twii_data(year):
    try:
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index.date)
        df = df.sort_index()
        ma20 = pd.Series(close).rolling(20).mean().values
        ma60 = pd.Series(close).rolling(60).mean().values

        rows = []
        for i in range(len(dates)):
            dt = dates[i]
            if not dt.startswith(str(year)):
                continue
            rows.append({
            })
        return rows
    except Exception as e:
        return None

def main():
    years = list(range(2004, 2027))
    for y in years:
        rows = get_twii_data(y)
        if rows and len(rows) > 10:
                json.dump(rows, f)
        else:
        time.sleep(2)

    main()
