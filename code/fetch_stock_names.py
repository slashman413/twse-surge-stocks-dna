import json, os, glob, time, yfinance as yf

DATA_DIR = r'D:\twse-surge-stocks-dna\docs\yearly_backtests'

# Collect all unique tickers
all_ticks = set()
for f in sorted(glob.glob(os.path.join(DATA_DIR, '*_trades_v12.json'))):
    with open(f) as fh:
        d = json.load(fh)
    for t in d['trades']:
        all_ticks.add(t['ticker'])
all_ticks = sorted(all_ticks)
print(f'Unique tickers: {len(all_ticks)}')

# Existing names from signals
stock_names = {}
sig_file = os.path.join(DATA_DIR, 'signals_data.json')
if os.path.isfile(sig_file):
    with open(sig_file) as f:
        sig = json.load(f)
    for s in sig.get('signals', []):
        stock_names[s['ticker']] = s['name']

# Existing names from kline_data
kline_file = os.path.join(DATA_DIR, 'kline_data.json')
if os.path.isfile(kline_file):
    with open(kline_file) as f:
        kd = json.load(f)
    for t, v in kd.items():
        if t not in stock_names or not stock_names[t]:
            stock_names[t] = v.get('ticker', t)  # just code as fallback

missing = [c for c in all_ticks if c not in stock_names or not stock_names[c]]
print(f'To fetch: {len(missing)}')

# Try TWSE OpenAPI first (gives Chinese names)
try:
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        twse_rows = json.loads(r.read())
    for row in twse_rows:
        code = row.get("Code", "")
        if code in missing:
            stock_names[code] = row.get("Name", code)
    print(f"  Got {sum(1 for c in missing if stock_names.get(c))}/{len(missing)} from TWSE API")
except Exception as e:
    print(f"  TWSE API failed: {e}")

# Refresh missing list
missing = [c for c in all_ticks if c not in stock_names or not stock_names[c]]

for i, code in enumerate(missing):
    try:
        suf = '.TWO' if code.endswith('O') else '.TW'
        t = yf.Ticker(code + suf)
        info = t.info
        name = info.get('longName', info.get('shortName', ''))
        stock_names[code] = name or ''
        time.sleep(0.03)
    except:
        stock_names[code] = ''
    if (i+1) % 50 == 0:
        print(f'  [{i+1}/{len(missing)}]')

# Fill missing codes
for t in all_ticks:
    if t not in stock_names:
        stock_names[t] = ''

# Save
out_file = os.path.join(DATA_DIR, 'stock_names.json')
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(stock_names, f, ensure_ascii=False, indent=2)
print(f'Saved: {len(stock_names)} names')
with_name = sum(1 for v in stock_names.values() if v)
print(f'With name: {with_name}/{len(stock_names)}')
