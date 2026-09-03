import sqlite3
from datetime import datetime, timedelta

DB_PATH = '/freqtrade/user_data/tradesv3.sqlite'
db = sqlite3.connect(DB_PATH)
cur = db.cursor()

# Get recent trades with open/close details
cur.execute('''
  SELECT pair, open_date, close_date, open_rate, close_rate, close_profit, close_profit_abs, exit_reason
  FROM trades WHERE is_open=0 ORDER BY open_date DESC LIMIT 30
''')
trades = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
db.close()

print("\n=== RECENT TRADES (showing losing trades in red) ===\n")
print(f"{'Pair':<12} {'Open Date':<20} {'Close Date':<20} {'Entry':<10} {'Exit':<10} {'Profit':<10} {'Exit Reason':<18} {'Duration':<12}")
print("-" * 130)

for t in reversed(trades):
    pair = t['pair']
    open_time = datetime.fromisoformat(t['open_date'].replace('Z', '+00:00'))
    close_time = datetime.fromisoformat(t['close_date'].replace('Z', '+00:00'))
    duration = close_time - open_time
    
    profit = t['close_profit_abs']
    profit_pct = t['close_profit']
    
    # Highlight losses
    marker = "❌" if profit < 0 else "✓ "
    exit_reason = t['exit_reason']
    
    print(f"{pair:<12} {t['open_date']:<20} {t['close_date']:<20} {t['open_rate']:<10.6f} {t['close_rate']:<10.6f} {profit:>+7.2f} EUR  {exit_reason:<18} {str(duration):<12}")

# Focus on the drawdown period
print("\n\n=== MAY 12-14 PROBLEM PERIOD (detailed) ===\n")
problem_trades = [t for t in trades if '2026-05-12' in t['open_date'] or '2026-05-13' in t['open_date'] or '2026-05-14' in t['open_date']]

print(f"{'Pair':<12} {'Open':<20} {'Close':<20} {'Open Price':<12} {'Close Price':<12} {'P&L':<10} {'Exit':<15}")
print("-" * 110)
for t in problem_trades:
    if t['close_profit_abs'] < 0:
        print(f"{t['pair']:<12} {t['open_date']:<20} {t['close_date']:<20} {t['open_rate']:<12.6f} {t['close_rate']:<12.6f} {t['close_profit_abs']:>+8.2f}  {t['exit_reason']:<15}")

# Calculate stats
losers = [t for t in trades if t['close_profit_abs'] < 0]
print(f"\n\nTotal losing trades: {len(losers)}/{len(trades)}")
print(f"Average loss per loser: {sum(t['close_profit_abs'] for t in losers) / len(losers):+.2f} EUR")
print(f"Win rate: {(len(trades) - len(losers)) / len(trades) * 100:.1f}%")

