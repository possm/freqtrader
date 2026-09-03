import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = '/freqtrade/user_data/tradesv3.sqlite'
DATA_DIR = Path('/freqtrade/user_data/data/kraken')

db = sqlite3.connect(DB_PATH)
cur = db.cursor()
cur.execute('''
  SELECT pair, open_date, close_date, open_rate, close_rate, close_profit, close_profit_abs, exit_reason
  FROM trades WHERE is_open=0 ORDER BY open_date ASC
''')
trades = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
db.close()

# Helper to load OHLCV
def load_pair(pair, timeframe='15m'):
    for f in DATA_DIR.glob(f"*{pair.replace('/', '_')}*{timeframe}*.feather"):
        df = pd.read_feather(f)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        return df.sort_values('date').reset_index(drop=True)
    return None

print("\n" + "=" * 100)
print("LOSING TRADE ANALYSIS — looking for patterns in the bad entries")
print("=" * 100)

losers = [t for t in trades if t['close_profit_abs'] < 0]
winners = [t for t in trades if t['close_profit_abs'] > 0]

print(f"\nLosers: {len(losers)} | Winners: {len(winners)}")

# For each losing trade, analyze the entry and what happened after
print("\n" + "=" * 100)
print("PER-TRADE ANALYSIS (losing trades)")
print("=" * 100)

for t in losers:
    pair = t['pair']
    open_time = pd.to_datetime(t['open_date'], utc=True)
    close_time = pd.to_datetime(t['close_date'], utc=True)
    
    df = load_pair(pair, '15m')
    if df is None:
        print(f"\n{pair}: no data")
        continue
    
    # Get the entry candle and surrounding
    entry_idx = df[df['date'] <= open_time].index[-1] if len(df[df['date'] <= open_time]) > 0 else None
    if entry_idx is None:
        continue
    
    # Look at 4 candles before entry and trade duration
    pre_entry = df.iloc[max(0, entry_idx-4):entry_idx+1]
    
    # Find trade window (entry to exit)
    exit_idx = df[df['date'] <= close_time].index[-1] if len(df[df['date'] <= close_time]) > 0 else len(df)-1
    trade_window = df.iloc[entry_idx:exit_idx+1]
    
    if len(trade_window) == 0:
        continue
    
    # Calculate key metrics
    entry_price = t['open_rate']
    max_price = trade_window['high'].max()
    min_price = trade_window['low'].min()
    max_profit_pct = ((max_price - entry_price) / entry_price) * 100
    max_loss_pct = ((min_price - entry_price) / entry_price) * 100
    
    # Time to max price (did it go up at all before reversing?)
    max_idx = trade_window['high'].idxmax()
    time_to_max = (df.iloc[max_idx]['date'] - open_time).total_seconds() / 3600  # hours
    
    # Was entry on a green or red candle?
    entry_candle = df.iloc[entry_idx]
    candle_color = "GREEN" if entry_candle['close'] > entry_candle['open'] else "RED"
    candle_change = ((entry_candle['close'] - entry_candle['open']) / entry_candle['open']) * 100
    
    # Pre-entry trend (last 4 candles)
    pre_trend = ((entry_candle['close'] - pre_entry.iloc[0]['close']) / pre_entry.iloc[0]['close']) * 100
    
    duration_hrs = (close_time - open_time).total_seconds() / 3600
    
    print(f"\n{pair}  (P&L: {t['close_profit_abs']:+.2f} EUR, duration: {duration_hrs:.1f}h)")
    print(f"  Entry: {open_time}  @ {entry_price:.6f}")
    print(f"  Entry candle: {candle_color} ({candle_change:+.2f}%)")
    print(f"  Pre-entry 1h trend: {pre_trend:+.2f}%")
    print(f"  Max profit reached: {max_profit_pct:+.2f}% (after {time_to_max:.1f}h)")
    print(f"  Max loss reached:   {max_loss_pct:+.2f}%")
    print(f"  Final result: {t['close_profit']*100:+.2f}% via {t['exit_reason']}")
    
    # Flag patterns
    flags = []
    if max_profit_pct < 0.5:
        flags.append("⚠️  NEVER WENT UP")  # Bad entry, immediate reversal
    if time_to_max < 0.5 and max_profit_pct > 0:
        flags.append("⚠️  IMMEDIATE PEAK")  # Entered at top
    if candle_color == "GREEN" and candle_change > 2:
        flags.append("⚠️  CHASING GREEN CANDLE")  # Entered after a pump
    if pre_trend > 5:
        flags.append("⚠️  HOT MARKET")  # Entered after big move up
    if duration_hrs > 24:
        flags.append("⚠️  HELD TOO LONG")
    
    if flags:
        print(f"  Flags: {', '.join(flags)}")

print("\n" + "=" * 100)
print("COMPARISON: WINNERS' ENTRY CHARACTERISTICS")
print("=" * 100)

for t in winners[:5]:  # Sample 5 winners
    pair = t['pair']
    open_time = pd.to_datetime(t['open_date'], utc=True)
    
    df = load_pair(pair, '15m')
    if df is None:
        continue
    
    entry_idx = df[df['date'] <= open_time].index[-1] if len(df[df['date'] <= open_time]) > 0 else None
    if entry_idx is None:
        continue
    
    pre_entry = df.iloc[max(0, entry_idx-4):entry_idx+1]
    entry_candle = df.iloc[entry_idx]
    candle_color = "GREEN" if entry_candle['close'] > entry_candle['open'] else "RED"
    candle_change = ((entry_candle['close'] - entry_candle['open']) / entry_candle['open']) * 100
    pre_trend = ((entry_candle['close'] - pre_entry.iloc[0]['close']) / pre_entry.iloc[0]['close']) * 100
    
    print(f"\n{pair}  (P&L: {t['close_profit_abs']:+.2f} EUR, win via {t['exit_reason']})")
    print(f"  Entry candle: {candle_color} ({candle_change:+.2f}%)")
    print(f"  Pre-entry 1h trend: {pre_trend:+.2f}%")

# Now aggregate patterns
print("\n" + "=" * 100)
print("AGGREGATE STATISTICS — Losers vs Winners")
print("=" * 100)

def analyze_pre_trend(trades_list, label):
    pre_trends = []
    candle_pcts = []
    green_candles = 0
    red_candles = 0
    
    for t in trades_list:
        pair = t['pair']
        open_time = pd.to_datetime(t['open_date'], utc=True)
        df = load_pair(pair, '15m')
        if df is None:
            continue
        
        if len(df[df['date'] <= open_time]) > 0:
            entry_idx = df[df['date'] <= open_time].index[-1]
            if entry_idx < 4:
                continue
            pre_entry = df.iloc[entry_idx-4:entry_idx+1]
            entry_candle = df.iloc[entry_idx]
            
            pre_trend = ((entry_candle['close'] - pre_entry.iloc[0]['close']) / pre_entry.iloc[0]['close']) * 100
            candle_pct = ((entry_candle['close'] - entry_candle['open']) / entry_candle['open']) * 100
            
            pre_trends.append(pre_trend)
            candle_pcts.append(candle_pct)
            if candle_pct > 0:
                green_candles += 1
            else:
                red_candles += 1
    
    if pre_trends:
        print(f"\n{label}:")
        print(f"  Average 1h pre-entry trend: {sum(pre_trends)/len(pre_trends):+.2f}%")
        print(f"  Average entry candle change: {sum(candle_pcts)/len(candle_pcts):+.2f}%")
        print(f"  Green candle entries: {green_candles}/{green_candles+red_candles} ({green_candles/(green_candles+red_candles)*100:.0f}%)")

analyze_pre_trend(losers, "LOSERS")
analyze_pre_trend(winners, "WINNERS")

