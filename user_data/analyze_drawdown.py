import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = '/freqtrade/user_data/tradesv3.sqlite'
db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# Get ALL closed trades, ordered by close date
cur.execute('''
  SELECT id, pair, open_date, close_date, open_rate, close_rate, close_profit, close_profit_abs, exit_reason
  FROM trades WHERE is_open=0 ORDER BY close_date ASC
''')
all_trades = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
db.close()

print(f"\n=== TOTAL TRADES: {len(all_trades)} ===\n")

# Analyze drawdown windows
print("=== CHECKING 24H DRAWDOWN WINDOW (3+ trades > 4% drawdown) ===\n")

for i in range(len(all_trades)):
    trade = all_trades[i]
    close_time = datetime.fromisoformat(trade['close_date'].replace('Z', '+00:00'))
    
    # Look back 24h (96 * 15min candles = 24h)
    window_start = close_time - timedelta(hours=24)
    
    # Find trades in this 24h window
    window_trades = [t for t in all_trades 
                     if datetime.fromisoformat(t['close_date'].replace('Z', '+00:00')) >= window_start 
                     and datetime.fromisoformat(t['close_date'].replace('Z', '+00:00')) <= close_time]
    
    if len(window_trades) >= 3:
        drawdown = sum(t['close_profit_abs'] for t in window_trades)
        drawdown_pct = (drawdown / (len(window_trades) * 75)) if len(window_trades) > 0 else 0
        
        if drawdown_pct < -0.04:  # > 4% drawdown
            print(f"TRIGGERED at {close_time}")
            print(f"  Window: {window_start} to {close_time}")
            print(f"  Trades in window: {len(window_trades)}")
            print(f"  Total loss: {drawdown:+.2f} EUR ({drawdown_pct:+.2%})")
            for t in window_trades[-3:]:
                print(f"    {t['pair']:10} | {t['close_date']:19} | {t['close_profit_abs']:+7.2f} EUR | {t['exit_reason']}")
            print()

print("\n=== CHECKING 7D DRAWDOWN WINDOW (8+ trades > 8% drawdown) ===\n")

for i in range(len(all_trades)):
    trade = all_trades[i]
    close_time = datetime.fromisoformat(trade['close_date'].replace('Z', '+00:00'))
    
    window_start = close_time - timedelta(days=7)
    
    window_trades = [t for t in all_trades 
                     if datetime.fromisoformat(t['close_date'].replace('Z', '+00:00')) >= window_start 
                     and datetime.fromisoformat(t['close_date'].replace('Z', '+00:00')) <= close_time]
    
    if len(window_trades) >= 8:
        drawdown = sum(t['close_profit_abs'] for t in window_trades)
        drawdown_pct = (drawdown / (len(window_trades) * 75)) if len(window_trades) > 0 else 0
        
        if drawdown_pct < -0.08:  # > 8% drawdown
            print(f"TRIGGERED at {close_time}")
            print(f"  Window: {window_start} to {close_time}")
            print(f"  Trades in window: {len(window_trades)}")
            print(f"  Total loss: {drawdown:+.2f} EUR ({drawdown_pct:+.2%})")
            for t in window_trades:
                print(f"    {t['pair']:10} | {t['close_date']:19} | {t['close_profit_abs']:+7.2f} EUR | {t['exit_reason']}")
            print()

print("\n=== RECENT TRADES (last 30) ===\n")
recent = all_trades[-30:] if len(all_trades) >= 30 else all_trades
for t in recent:
    print(f"{t['pair']:10} | {t['close_date']:19} | {t['close_profit_abs']:+7.2f} EUR | {t['exit_reason']}")

# Check stoploss guard triggers
print("\n=== CHECKING 24H STOPLOSS GUARD (3+ stoploss hits) ===\n")

stoploss_trades = [t for t in all_trades if 'stoploss' in t['exit_reason'].lower()]
print(f"Total stoploss trades: {len(stoploss_trades)}\n")

for i in range(len(stoploss_trades)):
    trade = stoploss_trades[i]
    close_time = datetime.fromisoformat(trade['close_date'].replace('Z', '+00:00'))
    window_start = close_time - timedelta(hours=24)
    
    window_sl = [t for t in stoploss_trades 
                 if datetime.fromisoformat(t['close_date'].replace('Z', '+00:00')) >= window_start 
                 and datetime.fromisoformat(t['close_date'].replace('Z', '+00:00')) <= close_time]
    
    if len(window_sl) >= 3:
        print(f"TRIGGERED at {close_time}: {len(window_sl)} SL hits in 24h")
        for t in window_sl:
            print(f"  {t['pair']:10} | {t['close_date']:19} | {t['close_profit_abs']:+7.2f} EUR")
        print()

