import ccxt
binance = ccxt.binance()
kraken = ccxt.kraken()
print("Binance taker:", binance.fees['trading']['taker'])
print("Binance maker:", binance.fees['trading']['maker'])
print("Kraken taker:", kraken.fees['trading']['taker'])
print("Kraken maker:", kraken.fees['trading']['maker'])
