import json, os, glob
import pandas as pd

DATA_DIR = r'D:\twse-surge-stocks-dna\docs\yearly_backtests'
PARQUET = r'D:\TWSE-Data\Adjusted\adjusted_all.parquet'

# Get all trade tickers
all_tickers = set()
for fpath in sorted(glob.glob(os.path.join(DATA_DIR, '*_trades_v12.json'))):
    with open(fpath) as f:
        data = json.load(f)
    for t in data['trades']:
        all_tickers.add(t['ticker'])

print(f'Loading parquet for {len(all_tickers)} tickers...')

# Read in chunks filtering by ticker (more efficient)
df_chunks = []
reader = pd.read_parquet(PARQUET, columns=['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume'],
                          use_threads=True)
# Add date string once
df = reader
df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')

# Filter to only our tickers
df = df[df['Ticker'].isin(all_tickers)]
print(f'Filtered to {len(df):,} rows')

# Create dictionary per ticker for fast lookup
ticker_data = {}
for tk in all_tickers:
    sub = df[df['Ticker'] == tk].sort_values('Date')
    if len(sub) > 0:
        rows = []
        for _, r in sub.iterrows():
            rows.append({
                'd': r['DateStr'],
                'o': float(r['Open']),
                'h': float(r['High']),
                'l': float(r['Low']),
                'c': float(r['Close']),
                'v': int(r['Volume'])
            })
        ticker_data[tk] = rows

# Now generate per-year chart files
for fpath in sorted(glob.glob(os.path.join(DATA_DIR, '*_trades_v12.json'))):
    year = os.path.basename(fpath).split('_')[0]
    out_path = os.path.join(DATA_DIR, f'trade_charts_{year}.json')
    if os.path.isfile(out_path):
        continue  # skip already done
    
    print(f'Generating {year}...', end=' ', flush=True)
    
    with open(fpath) as f:
        data = json.load(f)
    trades = data['trades']
    if not trades:
        print('no trades')
        continue
    
    # Group by ticker, find date range
    tickers = {}
    for t in trades:
        tk = t['ticker']
        if tk not in tickers:
            tickers[tk] = {'buy_dates': [], 'sell_dates': []}
        tickers[tk]['buy_dates'].append(t['buy_date'])
        tickers[tk]['sell_dates'].append(t['sell_date'])
    
    out = {}
    for tk, info in tickers.items():
        if tk not in ticker_data:
            continue
        all_rows = ticker_data[tk]
        
        min_d = min(info['buy_dates'])
        max_d = max(info['sell_dates'])
        
        # Filter by date range
        filtered = [r for r in all_rows if min_d <= r['d'] <= max_d]
        if len(filtered) < 5:
            # Use tail
            filtered = [r for r in all_rows if r['d'] <= max_d][-200:]
        
        if len(filtered) > 0:
            out[tk] = {'ticker': tk, 'kline': filtered}
    
    if out:
        with open(out_path, 'w') as f:
            json.dump(out, f)
        print(f'{len(out)} stocks')
    else:
        print('no data')

print('Done')
