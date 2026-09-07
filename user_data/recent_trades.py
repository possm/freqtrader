import sqlite3
from datetime import datetime, timedelta

db = sqlite3.connect('/freqtrade/user_data/tradesv3.sqlite')
cur = db.cursor()
cur.execute('''
  SELECT pair, open_date, close_date, open_rate, close_rate, close_profit, close_profit_abs, exit_reason
  FROM trades WHERE is_open=0
  AND close_date >= datetime('now', '-3 days')
  ORDER BY close_date ASC
''')
trades = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
db.close()

print(f"\n=== LIVE TRADES LAST 3 DAYS (WolfCustomSwing) ===")
print(f"Total closed: {len(trades)}\n")
print(f"{'Pair':<10} {'Closed':<22} {'P&L':<10} {'P%':<8} {'Exit Reason':<20}")
print("-" * 75)

total_pnl = 0
losses = 0
loss_total = 0
wins = 0
win_total = 0
sl_count = 0

for t in trades:
    pnl = t['close_profit_abs']
    pct = t['close_profit'] * 100
    total_pnl += pnl
    if pnl < 0:
        losses += 1
        loss_total += pnl
        if 'stop_loss' in t['exit_reason']:
            sl_count += 1
    else:
        wins += 1
        win_total += pnl
    print(f"{t['pair']:<10} {t['close_date'][:19]:<22} {pnl:>+8.2f}  {pct:>+6.2f}%  {t['exit_reason']:<20}")

print(f"\n{'─'*75}")
print(f"TOTAL P&L:    {total_pnl:+.2f} EUR")
print(f"Wins:         {wins}  → +{win_total:.2f} EUR")
print(f"Losses:       {losses}  → {loss_total:.2f} EUR")
print(f"  of which stop_loss: {sl_count}")
