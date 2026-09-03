import sqlite3
db = sqlite3.connect('/freqtrade/user_data/tradesv3.sqlite')
cur = db.cursor()
cur.execute('SELECT pair, open_rate, close_rate, close_profit_abs, close_profit FROM trades WHERE is_open=0 ORDER BY close_date DESC LIMIT 50')
trades = cur.fetchall()
db.close()

print("\n=== LAST 50 CLOSED TRADES ===\n")
print(f"{'Pair':<12} {'Open':<12} {'Close':<12} {'Profit EUR':<13} {'%':<8}")
print("-" * 60)
for pair, open_r, close_r, profit_abs, profit_pct in trades:
    print(f"{pair:<12} {open_r:<12.6f} {close_r:<12.6f} {profit_abs:>+12.2f} {profit_pct:>+7.2%}")

from collections import defaultdict
by_pair = defaultdict(lambda: {'count': 0, 'total': 0, 'pct': 0})
for pair, _, _, profit_abs, profit_pct in trades:
    by_pair[pair]['count'] += 1
    by_pair[pair]['total'] += profit_abs
    by_pair[pair]['pct'] += profit_pct

print(f"\n=== SUMMARY BY PAIR ===\n")
for pair in sorted(by_pair.keys()):
    stats = by_pair[pair]
    avg_pct = stats['pct'] / stats['count']
    print(f"{pair:<12} | {stats['count']:2} trades | {stats['total']:>+8.2f} EUR | Avg {avg_pct:>+7.2%}")
