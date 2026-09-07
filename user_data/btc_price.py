import ccxt
kraken = ccxt.kraken()
ohlcv = kraken.fetch_ohlcv('BTC/EUR', '1d', limit=720)
print(f"Earliest data: {ohlcv[0][0]}, {ohlcv[0][4]}")
