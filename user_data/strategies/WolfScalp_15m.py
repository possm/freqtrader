from datetime import datetime
from typing import Optional
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import merge_informative_pair

from WolfTrend_EMA_hopt_tuned import WolfTrend_EMA_hopt_tuned

class WolfScalp_15m(WolfTrend_EMA_hopt_tuned):
    """
    Scalping / Short-Swing variant of the Wolf strategy.
    Focuses on quick 1-5% profits with shorter holding durations.
    """
    
    timeframe = '15m'
    
    # Strict ROI to take profits between 1% and 5% quickly
    minimal_roi = {
        "0": 0.05,      # 5% profit instantly
        "60": 0.03,     # 3% profit after 1 hour (4 candles)
        "180": 0.015,   # 1.5% profit after 3 hours (12 candles)
        "360": 0.01     # 1% profit after 6 hours (24 candles)
    }
    
    # Tighter stoploss for scalping
    stoploss = -0.03
    
    # Disable trailing stop to let the strict ROI take the profits
    trailing_stop = False

    # Original EMA lengths (applied to 15m now, so they react very fast!)
    EMA_FAST = 20
    EMA_SLOW = 71
    EMA_TREND = 105
    
    startup_candle_count = 200

    def informative_pairs(self):
        # Keep the 4h BTC macro trend to ensure we only scalp during macro bull regimes
        return [(f"BTC/{self.config['stake_currency']}", "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.fast_ema_length = self.EMA_FAST
        self.slow_ema_length = self.EMA_SLOW
        self.trend_ema_length = self.EMA_TREND
        
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # BTC macro uptrend gate
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
