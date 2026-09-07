from datetime import datetime
from typing import Optional
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import merge_informative_pair

from WolfTrend_EMA_hopt_tuned import WolfTrend_EMA_hopt_tuned

class WolfScalp_1h(WolfTrend_EMA_hopt_tuned):
    """
    Swing variant on the 1h timeframe (highly reliable entries), but taking quick 1-5% profits.
    """
    
    timeframe = '1h'
    
    # Strict ROI to take profits quickly
    minimal_roi = {
        "0": 0.05,      # 5% profit instantly
        "720": 0.03,    # 3% profit after 12 hours
        "1440": 0.015,  # 1.5% profit after 24 hours
        "2880": 0.01    # 1% profit after 48 hours
    }
    
    # Use the 5% stoploss we found worked well for early entry
    stoploss = -0.05
    trailing_stop = False

    # Quadrupled lengths to match the 4h macro trend detection
    EMA_FAST = 80       
    EMA_SLOW = 284      
    EMA_TREND = 420     
    
    startup_candle_count = 450

    def informative_pairs(self):
        return [(f"BTC/{self.config['stake_currency']}", "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.fast_ema_length = self.EMA_FAST
        self.slow_ema_length = self.EMA_SLOW
        self.trend_ema_length = self.EMA_TREND
        
        dataframe = super().populate_indicators(dataframe, metadata)
        
        btc = self.dp.get_pair_dataframe(pair=f"BTC/{self.config['stake_currency']}", timeframe="4h")
        btc["btc_ema200"] = ta.EMA(btc, timeperiod=200)
        btc["btc_uptrend"] = (btc["close"] > btc["btc_ema200"]).astype(int)
        
        dataframe = merge_informative_pair(
            dataframe, btc[["date", "btc_uptrend"]], self.timeframe, "4h", ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe.loc[
            dataframe["btc_uptrend_4h"] != 1, 
            ["enter_long", "enter_tag"]
        ] = (0, None)
        return dataframe
