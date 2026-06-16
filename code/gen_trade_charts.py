import json, os, glob, sys
import pandas as pd

DATA_DIR = r'D:\twse-surge-stocks-dna\docs\yearly_backtests'
PARQUET = r'D:\TWSE-Data\Adjusted\adjusted_all.parquet'

print('Loading parquet (date, ticker, OHLCV)...')
df = pd.read_parquet(PARQUET, columns=['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume'])
# Date is datetime64[ms] - convert to string for safe filtering
df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')

# Process each year's trades
for fpath in sorted(glob.glob(os.path.join(DATA_DIR, '*_trades_v12.json'))):
    year = os.path.basename(fpath).split('_')[0]
    print(f'Processing {year}...', end=' ', flush=True)
    
    with open(fpath) as f:
        data = json.load(f)
    trades = data['trades']
    if not trades:
        print('no trades')
        continue
    
    # For each unique ticker, find the date range needed
    tickers = {}
    for t in trades:
        tk = t['ticker']
        if tk not in tickers:
            tickers[tk] = {'buy_dates': [], 'sell_dates': []}
        tickers[tk]['buy_dates'].append(t['buy_date'])
        tickers[tk]['sell_dates'].append(t['sell_date'])
    
    # Get all unique (ticker, start, end) slices
    out = {}
    for tk, info in tickers.items():
        min_d = min(info['buy_dates'])
        max_d = max(info['sell_dates'])
        
        # Look up by ticker string filter for speed
        sub = df[df['Ticker'] == tk].copy()
        if len(sub) == 0:
            continue
        sub = sub[(sub['DateStr'] >= min_d) & (sub['DateStr'] <= max_d)]
        if len(sub) < 5:
            sub = df[df['Ticker'] == tk].tail(200)
        if len(sub) == 0:
            continue
        
        sub = sub.sort_values('Date')
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
        out[tk] = {'ticker': tk, 'kline': rows}
    
    if out:
        out_path = os.path.join(DATA_DIR, f'trade_charts_{year}.json')
        with open(out_path, 'w') as f:
            json.dump(out, f)
    else:
        print('no data')

print('Done')
