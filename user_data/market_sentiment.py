import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path('/freqtrade/user_data/data/kraken')

def load_pair(pair, tf='1h'):
    f = DATA_DIR / f"{pair}-{tf}.feather"
    if not f.exists():
        return None
    df = pd.read_feather(f)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df.sort_values('date').reset_index(drop=True)

def analyze_pair(pair_name, df, period_start, period_end):
    """Comprehensive market analysis for a pair."""
    df = df[(df['date'] >= period_start) & (df['date'] <= period_end)].copy()
    if len(df) < 24:
        return None

    # Resample to daily for sentiment analysis
    df['day'] = df['date'].dt.date
    daily = df.groupby('day').agg(
        open=('open', 'first'),
        high=('high', 'max'),
        low=('low', 'min'),
        close=('close', 'last'),
        volume=('volume', 'sum'),
    ).reset_index()
    daily['return'] = daily['close'].pct_change() * 100

    # Total return
    total_return = (daily['close'].iloc[-1] - daily['close'].iloc[0]) / daily['close'].iloc[0] * 100

    # Volatility
    avg_daily_vol = daily['return'].std()

    # Up vs Down days
    up_days = (daily['return'] > 0).sum()
    down_days = (daily['return'] < 0).sum()
    big_up_days = (daily['return'] > 3).sum()
    big_down_days = (daily['return'] < -3).sum()

    # Max drawdown
    daily['cummax'] = daily['close'].cummax()
    daily['drawdown'] = (daily['close'] - daily['cummax']) / daily['cummax'] * 100
    max_dd = daily['drawdown'].min()

    # Trend strength: % of days where 7-day SMA is rising
    daily['sma7'] = daily['close'].rolling(7).mean()
    daily['sma_rising'] = daily['sma7'] > daily['sma7'].shift(1)
    pct_uptrend = daily['sma_rising'].sum() / len(daily.dropna(subset=['sma_rising'])) * 100

    # Choppy index: how often does daily return flip sign?
    daily['return_sign'] = np.sign(daily['return'])
    flips = (daily['return_sign'] != daily['return_sign'].shift(1)).sum()
    choppy_pct = flips / len(daily) * 100

    return {
        'pair': pair_name,
        'start_price': daily['close'].iloc[0],
        'end_price': daily['close'].iloc[-1],
        'total_return': total_return,
        'avg_daily_vol': avg_daily_vol,
        'up_days': up_days,
        'down_days': down_days,
        'big_up_days': big_up_days,
        'big_down_days': big_down_days,
        'max_drawdown': max_dd,
        'pct_uptrend_days': pct_uptrend,
        'flip_pct': choppy_pct,
        'days': len(daily),
    }

# Analyze key pairs
pairs = ['BTC_EUR', 'ETH_EUR', 'POL_EUR', 'AAVE_EUR']
period_start = pd.Timestamp('2026-02-14', tz='UTC')
period_end = pd.Timestamp('2026-05-16', tz='UTC')

print(f"\n{'='*80}")
print(f"MARKT SENTIMENT ANALYSE — {period_start.date()} tot {period_end.date()}")
print(f"{'='*80}\n")

results = []
for pair in pairs:
    df = load_pair(pair, '1h')
    if df is None:
        print(f"{pair}: geen data")
        continue
    r = analyze_pair(pair, df, period_start, period_end)
    if r: results.append(r)

print(f"{'Pair':<10} {'Start':>10} {'End':>10} {'Return':>10} {'Vol/d':>8} {'UpDays':>7} {'DnDays':>7} {'BigUp':>6} {'BigDn':>6} {'MaxDD':>8} {'%Up':>6} {'%Flip':>7}")
print('-' * 100)
for r in results:
    print(f"{r['pair']:<10} "
          f"{r['start_price']:>10.2f} {r['end_price']:>10.2f} "
          f"{r['total_return']:>+9.1f}% "
          f"{r['avg_daily_vol']:>7.2f}% "
          f"{r['up_days']:>7} {r['down_days']:>7} "
          f"{r['big_up_days']:>6} {r['big_down_days']:>6} "
          f"{r['max_drawdown']:>+7.1f}% "
          f"{r['pct_uptrend_days']:>5.0f}% "
          f"{r['flip_pct']:>6.0f}%")

# Maandelijkse breakdown voor BTC
print(f"\n\n{'='*80}")
print(f"BTC/EUR — MAANDELIJKSE BREAKDOWN")
print(f"{'='*80}\n")

btc = load_pair('BTC_EUR', '1h')
btc = btc[(btc['date'] >= period_start) & (btc['date'] <= period_end)].copy()
btc['month'] = btc['date'].dt.to_period('M')

print(f"{'Month':<10} {'Start':>10} {'End':>10} {'Return':>10} {'Vol':>8} {'High':>10} {'Low':>10} {'Range':>8}")
print('-' * 80)
for month, grp in btc.groupby('month'):
    start = grp['close'].iloc[0]
    end = grp['close'].iloc[-1]
    ret = (end - start) / start * 100
    vol = grp['close'].pct_change().std() * 100
    high = grp['high'].max()
    low = grp['low'].min()
    range_pct = (high - low) / low * 100
    print(f"{str(month):<10} {start:>10.2f} {end:>10.2f} {ret:>+9.1f}% {vol:>7.2f}% {high:>10.2f} {low:>10.2f} {range_pct:>7.1f}%")

# Fear & Greed indicators uit price action
print(f"\n\n{'='*80}")
print(f"AFGELEIDE SENTIMENT INDICATORS (BTC/EUR)")
print(f"{'='*80}\n")

btc['day'] = btc['date'].dt.date
btc_daily = btc.groupby('day').agg(close=('close', 'last'), volume=('volume', 'sum')).reset_index()
btc_daily['return'] = btc_daily['close'].pct_change() * 100

# Recent (laatste maand) vs eerder
recent = btc_daily.tail(30)
earlier = btc_daily.iloc[:-30]

print(f"Laatste 30 dagen vs eerdere 60+ dagen:")
print(f"  Volatility (avg daily move):  laatste={recent['return'].abs().mean():.2f}%  eerder={earlier['return'].abs().mean():.2f}%")
print(f"  Up/Down ratio:                 laatste={(recent['return']>0).sum()}/{(recent['return']<0).sum()}  eerder={(earlier['return']>0).sum()}/{(earlier['return']<0).sum()}")
print(f"  Avg daily volume (proxy):     laatste={recent['volume'].mean()/1e6:.1f}M  eerder={earlier['volume'].mean()/1e6:.1f}M")

# 30-day trailing volatility plot
btc_daily['vol_30d'] = btc_daily['return'].rolling(14).std()
print(f"\nTrailing 14-day volatility (BTC daily returns):")
samples = btc_daily.dropna().iloc[::7][-12:]   # weekly samples
for _, row in samples.iterrows():
    bar = '█' * int(row['vol_30d'] * 5)
    print(f"  {row['day']}  vol={row['vol_30d']:.2f}%  {bar}")

