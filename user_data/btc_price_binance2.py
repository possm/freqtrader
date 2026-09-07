import ccxt
from datetime import datetime
binance = ccxt.binance()
ts = int(datetime(2021, 1, 1).timestamp() * 1000)
ohlcv = binance.fetch_ohlcv('BTC/USDT', '1d', since=ts, limit=1)
print(f"Jan 1 2021: {ohlcv[0][4]}")
