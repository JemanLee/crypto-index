"""
Fetches EETH & BNMR pre/regular/post-market prices from Yahoo Finance
and writes stocks.json to the repo root.
Run by GitHub Actions — no external packages needed (stdlib only).
"""
import json
import urllib.request
from datetime import datetime, timezone

SYMBOLS = ['EETH', 'BMNR']
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json,*/*',
    'Referer': 'https://finance.yahoo.com',
}

def fetch_symbol(sym):
    url = (
        f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
        '?interval=1m&range=1d&includePrePost=true'
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def last_price_in(timestamps, closes, start, end):
    """Return last non-null close price within [start, end) timestamp window."""
    pts = [c for t, c in zip(timestamps, closes) if start <= t < end and c is not None]
    return round(pts[-1], 4) if pts else None

def pct_change(price, prev_close):
    if price is None or not prev_close:
        return None
    return round((price - prev_close) / prev_close * 100, 2)

def detect_state(timestamps, tp):
    """Determine current market state from latest data timestamp."""
    if not timestamps:
        return 'CLOSED'
    last_ts = max(timestamps)
    if tp['pre']['start'] <= last_ts < tp['pre']['end']:
        return 'PRE'
    if tp['regular']['start'] <= last_ts < tp['regular']['end']:
        return 'REG'
    if tp['post']['start'] <= last_ts < tp['post']['end']:
        return 'POST'
    return 'CLOSED'

def parse_symbol(data):
    result_data = data['chart']['result'][0]
    meta       = result_data['meta']
    timestamps = result_data.get('timestamp', [])
    closes     = result_data['indicators']['quote'][0].get('close', [])
    tp         = meta['currentTradingPeriod']
    prev_close = meta.get('chartPreviousClose')

    reg  = meta.get('regularMarketPrice')
    pre  = last_price_in(timestamps, closes, tp['pre']['start'],     tp['pre']['end'])
    post = last_price_in(timestamps, closes, tp['post']['start'],    tp['post']['end'])

    return {
        'reg':     reg,
        'regChg':  pct_change(reg, prev_close),
        'pre':     pre,
        'preChg':  pct_change(pre, prev_close),
        'post':    post,
        'postChg': pct_change(post, prev_close),
        'prev':    prev_close,
        'state':   detect_state(timestamps, tp),
    }

if __name__ == '__main__':
    result = {
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'stocks': {}
    }
    for sym in SYMBOLS:
        try:
            data = fetch_symbol(sym)
            result['stocks'][sym] = parse_symbol(data)
            print(f'{sym}: {result["stocks"][sym]}')
        except Exception as e:
            print(f'{sym} ERROR: {e}')

    with open('stocks.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('stocks.json saved.')

