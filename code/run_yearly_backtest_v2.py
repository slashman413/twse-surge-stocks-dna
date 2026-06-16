import os, sys, time, json
import multiprocessing as mp
from data_loader import TWSEStockLoader
from backtest import run_backtest

def process_stock(args):
    ticker, year = args
    try:
        r = run_backtest(ticker, year, year)
        return {
        }
    except Exception as e:


loader = TWSEStockLoader()
tickers = sorted(t for t in loader.list_available_tickers() if t.isdigit() and len(t) == 4)

n_workers = max(1, mp.cpu_count() - 1)

all_yearly = []

for year in range(2004, 2027):
    t0 = time.time()
    
    args = [(t, year) for t in tickers]
    with mp.Pool(n_workers) as pool:
        results = list(pool.imap_unordered(process_stock, args, chunksize=50))
    
    
    yr_data = {
    }
    all_yearly.append(yr_data)

    json.dump(summary, f, ensure_ascii=False, indent=2)
