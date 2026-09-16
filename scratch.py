import ccxt
import pandas as pd
import numpy as np
import talib.abstract as ta

exchange = ccxt.bybit()
pairs = ['XLM/USDC', 'XRP/USDC', 'ADA/USDC', 'BTC/USDC', 'LINK/USDC', 'SUI/USDC', 'ETH/USDC', 'DOGE/USDC', 'TRX/USDC']

for pair in pairs:
    try:
        ohlcv = exchange.fetch_ohlcv(pair, '1d', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # calculate donchian_high
        df["donchian_high"] = df["high"].rolling(15).max().shift(1)
        # calculate ema_trend
        df["ema_trend"] = ta.EMA(df, timeperiod=35)
        # volume_mean20
        df["volume_mean20"] = df["volume"].rolling(20).mean()
        
        last = df.iloc[-1]
        
        close = last['close']
        donch = last['donchian_high']
        ema = last['ema_trend']
        vol = last['volume']
        vol20 = last['volume_mean20'] * 1.334
        
        dist_donch = (donch - close) / close * 100
        dist_ema = (ema - close) / close * 100
        
        print(f"--- {pair} ---")
        if close > donch:
            print(f"Donchian (Breakout): Met")
        else:
            print(f"Donchian (Breakout): {dist_donch:.2f}% away (Needs {donch:.4f})")
            
        if close > ema:
            print(f"EMA Trend: Met")
        else:
            print(f"EMA Trend: {dist_ema:.2f}% away (Needs {ema:.4f})")
            
        if vol > vol20:
            print(f"Volume: Met")
        else:
            dist_vol = (vol20 - vol) / vol * 100
            print(f"Volume: Needs {(vol20/vol):.2f}x current volume (Target: {vol20:.0f})")
            
    except Exception as e:
        print(f"Error for {pair}: {e}")

