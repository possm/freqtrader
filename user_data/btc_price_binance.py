import ccxt
from datetime import datetime

binance = ccxt.binance()
timestamp_5_years_ago = int(datetime(2021, 9, 4).timestamp() * 1000)

ohlcv = binance.fetch_ohlcv('BTC/USDT', '1d', since=timestamp_5_years_ago, limit=1)
price_5_years_ago_usdt = ohlcv[0][4]

ticker = binance.fetch_ticker('BTC/USDT')
current_price_usdt = ticker['last']

print(f"BTC Price 5 years ago (USDT): {price_5_years_ago_usdt}")
print(f"BTC Current Price (USDT): {current_price_usdt}")
