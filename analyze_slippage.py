#!/usr/bin/env python3
"""
Analyze slippage on closed trades by comparing fill prices to OHLCV candles.
"""
import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Database path (will be mounted into Docker)
DB_PATH = '/freqtrade/user_data/tradesv3.sqlite'
DATA_DIR = Path('/freqtrade/user_data/data/kraken')

# Connect to trades DB
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
cursor = db.cursor()

cursor.execute("""
  SELECT
    trade_id, pair, stake_amount, amount,
    open_rate, close_rate,
    open_date, close_date,
    close_profit, close_profit_abs
  FROM trades
  WHERE is_open = 0
  ORDER BY close_date DESC
  LIMIT 50
""")

trades = [dict(row) for row in cursor.fetchall()]
db.close()

if not trades:
    print("No closed trades found.")
    exit(0)

# Load OHLCV data for each pair and compute slippage
results = []

for trade in trades:
    pair = trade['pair']
    # Convert ISO timestamps to datetime
    try:
        open_time = pd.to_datetime(trade['open_date']).tz_convert('UTC')
        close_time = pd.to_datetime(trade['close_date']).tz_convert('UTC')
    except:
        open_time = pd.to_datetime(trade['open_date'])
        close_time = pd.to_datetime(trade['close_date'])

    # Look for feather file
    feather_file = DATA_DIR / f"{pair.replace('/', '_')}-15m.feather"

    if not feather_file.exists():
        # Try without underscores or other naming conventions
        for f in DATA_DIR.glob(f"*{pair.split('/')[0]}*{pair.split('/')[1]}*15m*"):
            feather_file = f
            break

    entry_slippage_bps = None
    exit_slippage_bps = None
    entry_mid = None
    exit_mid = None

    if feather_file.exists():
        try:
            df = pd.read_feather(feather_file)
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize('UTC', ambiguous='NaT')

            # Find candles closest to entry and exit times
            entry_candle = df[df['date'] <= open_time].iloc[-1:] if len(df[df['date'] <= open_time]) > 0 else None
            exit_candle = df[df['date'] <= close_time].iloc[-1:] if len(df[df['date'] <= close_time]) > 0 else None

            if entry_candle is not None and len(entry_candle) > 0:
                candle = entry_candle.iloc[0]
                entry_mid = (candle['high'] + candle['low']) / 2
                entry_slippage_bps = ((trade['open_rate'] - entry_mid) / entry_mid) * 10000

            if exit_candle is not None and len(exit_candle) > 0:
                candle = exit_candle.iloc[0]
                exit_mid = (candle['high'] + candle['low']) / 2
                exit_slippage_bps = ((exit_mid - trade['close_rate']) / exit_mid) * 10000

        except Exception as e:
            pass

    results.append({
        'pair': pair,
        'open_date': trade['open_date'],
        'close_date': trade['close_date'],
        'open_rate': trade['open_rate'],
        'close_rate': trade['close_rate'],
        'entry_slippage_bps': round(entry_slippage_bps, 2) if entry_slippage_bps else None,
        'exit_slippage_bps': round(exit_slippage_bps, 2) if exit_slippage_bps else None,
        'close_profit': round(trade['close_profit'], 4),
        'close_profit_abs': round(trade['close_profit_abs'], 2),
    })

# Summary stats
print(json.dumps(results, indent=2, default=str))

# Aggregate by pair
pair_stats = {}
for r in results:
    pair = r['pair']
    if pair not in pair_stats:
        pair_stats[pair] = {'entry_slips': [], 'exit_slips': [], 'count': 0}
    if r['entry_slippage_bps'] is not None:
        pair_stats[pair]['entry_slips'].append(r['entry_slippage_bps'])
    if r['exit_slippage_bps'] is not None:
        pair_stats[pair]['exit_slips'].append(r['exit_slippage_bps'])
    pair_stats[pair]['count'] += 1

print("\n\n=== SLIPPAGE BY PAIR ===")
for pair in sorted(pair_stats.keys()):
    stats = pair_stats[pair]
    entry_avg = sum(stats['entry_slips']) / len(stats['entry_slips']) if stats['entry_slips'] else None
    exit_avg = sum(stats['exit_slips']) / len(stats['exit_slips']) if stats['exit_slips'] else None
    print(f"{pair:12} | Trades: {stats['count']:2} | Entry: {entry_avg:6.1f} bps | Exit: {exit_avg:6.1f} bps")
