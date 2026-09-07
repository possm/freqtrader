from datetime import datetime
from typing import Optional
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import merge_informative_pair

from WolfTrend_EMA_hopt_tuned import WolfTrend_EMA_hopt_tuned

class WolfTrend_1h_Candidate(WolfTrend_EMA_hopt_tuned):
    """
    Final Candidate Strategy based on the early-entry breakthrough.
    - Timeframe: 1h (Kraken does not support 2h candles!)
    - Stoploss: 5%
    - Indicators: Quadrupled in length to maintain the same macro time window as 4h.
    - BTC Gate: Inherits the 4h BTC EMA200 uptrend gate.
    """
    
    timeframe = '1h'
    stoploss = -0.027
    
    EMA_FAST = 80       # 20 * 4
    EMA_SLOW = 284      # 71 * 4
    EMA_TREND = 420     # 105 * 4
    
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
