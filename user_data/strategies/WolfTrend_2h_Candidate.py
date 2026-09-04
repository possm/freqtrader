from datetime import datetime
from typing import Optional
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import merge_informative_pair

from WolfTrend_EMA_hopt_tuned import WolfTrend_EMA_hopt_tuned

class WolfTrend_2h_Candidate(WolfTrend_EMA_hopt_tuned):
    """
    Final Candidate Strategy based on the 2h early-entry breakthrough.
    - Timeframe: 2h (steps in earlier than the 4h baseline)
    - Stoploss: 5% (more breathing room than baseline 2.4%)
    - Indicators: Doubled in length to maintain the same macro time window as 4h.
    - BTC Gate: Inherits the 4h BTC EMA200 uptrend gate.
    """
    
    timeframe = '2h'
    stoploss = -0.05
    
    EMA_FAST = 40       # 20 * 2
    EMA_SLOW = 142      # 71 * 2
    EMA_TREND = 210     # 105 * 2
    
    startup_candle_count = 850

    def informative_pairs(self):
        # We always want the 4h BTC trend filter, regardless of our 2h timeframe
        return [(f"BTC/{self.config['stake_currency']}", "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Override the defaults in the parent class with our doubled periods
        # before the parent method calculates them.
        self.fast_ema_length = self.EMA_FAST
        self.slow_ema_length = self.EMA_SLOW
        self.trend_ema_length = self.EMA_TREND
        
        # Call parent's indicator logic
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # Add BTC macro uptrend gate (on 4h resolution)
        btc = self.dp.get_pair_dataframe(pair=f"BTC/{self.config['stake_currency']}", timeframe="4h")
        btc["btc_ema200"] = ta.EMA(btc, timeperiod=200)
        btc["btc_uptrend"] = (btc["close"] > btc["btc_ema200"]).astype(int)
        
        dataframe = merge_informative_pair(
            dataframe, btc[["date", "btc_uptrend"]], self.timeframe, "4h", ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Call parent's entry logic
        dataframe = super().populate_entry_trend(dataframe, metadata)
        
        # Gate the entries with the BTC uptrend
        dataframe.loc[
            dataframe["btc_uptrend_4h"] != 1, 
            ["enter_long", "enter_tag"]
        ] = (0, None)
        
        return dataframe
