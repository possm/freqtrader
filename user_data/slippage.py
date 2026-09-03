import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = '/freqtrade/user_data/tradesv3.sqlite'
DATA_DIR = Path('/freqtrade/user_data/data/kraken')

db = sqlite3.connect(DB_PATH)
cur = db.cursor()
cur.execute('''
  SELECT id, pair, open_rate, close_rate, open_date, close_date, close_profit_abs
  FROM trades WHERE is_open=0 ORDER BY close_date DESC LIMIT 100
''')
trades = [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]
db.close()

print("\n=== FILL QUALITY ANALYSIS ===\n")
print(f"{'Pair':<12} {'Entry Slip':<12} {'Exit Slip':<12} {'Round-Trip':<12} {'Profit':<10}")
print("-" * 60)

pair_slips = {}
entry_slips_all = []
exit_slips_all = []

for trade in trades:
    pair = trade['pair']
    
    # Find feather file
    feather_file = None
    for f in DATA_DIR.glob(f"*{pair.replace('/', '_')}*15m*.feather"):
        feather_file = f
        break
    
    if not feather_file:
        continue
    
    try:
        df = pd.read_feather(feather_file)
        
        # Ensure date column
        if 'date' not in df.columns:
            continue
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.sort_values('date')
        
        # Entry
        entry_time = pd.to_datetime(trade['open_date'], utc=True)
        entry_cand = df[df['date'] <= entry_time].iloc[-1:] if len(df[df['date'] <= entry_time]) > 0 else None
        
        # Exit
        exit_time = pd.to_datetime(trade['close_date'], utc=True)
        exit_cand = df[df['date'] <= exit_time].iloc[-1:] if len(df[df['date'] <= exit_time]) > 0 else None
        
        entry_slip = None
        exit_slip = None
        
        if entry_cand is not None and len(entry_cand) > 0:
            c = entry_cand.iloc[0]
            mid = (c['high'] + c['low']) / 2
            entry_slip = ((trade['open_rate'] - mid) / mid) * 10000
            entry_slips_all.append(entry_slip)
        
        if exit_cand is not None and len(exit_cand) > 0:
            c = exit_cand.iloc[0]
            mid = (c['high'] + c['low']) / 2
            exit_slip = ((mid - trade['close_rate']) / mid) * 10000
            exit_slips_all.append(exit_slip)
        
        if entry_slip is not None and exit_slip is not None:
            rt = entry_slip + exit_slip
            print(f"{pair:<12} {entry_slip:>+10.1f} bp  {exit_slip:>+10.1f} bp  {rt:>+10.1f} bp  {trade['close_profit_abs']:>+8.2f} EUR")
            
            if pair not in pair_slips:
                pair_slips[pair] = []
            pair_slips[pair].append(rt)
    
    except Exception as e:
        pass

if pair_slips:
    print(f"\n=== SLIPPAGE SUMMARY ===\n")
    for pair in sorted(pair_slips.keys()):
        slips = pair_slips[pair]
        avg = sum(slips) / len(slips)
        print(f"{pair:<12} | {avg:>+7.1f} bps ({len(slips)} trades)")
    
    avg_rt = sum(sum(s) / len(s) for s in pair_slips.values()) / len(pair_slips)
    print(f"\nAverage round-trip: {avg_rt:>+7.1f} bps")
    print(f"Cost per 75 EUR trade: {avg_rt * 0.75:.2f} EUR (out of ~3 EUR avg profit)")
    print(f"\nUSDA conversion cost (round-trip): ~0.3-0.4% = 30-40 bps")
    print(f"Break-even if USDT liquidity improves fills by > {max(30, avg_rt):.0f} bps")
else:
    print("(no data available)")

