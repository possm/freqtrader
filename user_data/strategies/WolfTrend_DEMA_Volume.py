from datetime import datetime, timezone
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
from WolfTrend_EMA_hopt_tuned_variants import WTE_btc200

class WolfTrend_DEMA_Volume(WTE_btc200):
    """
    Inherits the BTC macro gate from WTE_btc200, but uses DEMA for faster entry
    and a Volume Surge filter to avoid fakeouts. Exits use the original EMA cross.
    """
    
    # We can use the same timeperiods as the base strategy, or configure them.
    DEMA_FAST = 20
    DEMA_SLOW = 71
    VOLUME_WINDOW = 24
    VOLUME_MULTIPLIER = 1.5

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # First let the parent (which includes WTE_btc200 and base) do its thing
        # This will calculate ema_fast, ema_slow, ema_trend, adx, and btc_uptrend
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # Add DEMA for fast entry
        dataframe["dema_fast"] = ta.DEMA(dataframe, timeperiod=self.DEMA_FAST)
        dataframe["dema_slow"] = ta.DEMA(dataframe, timeperiod=self.DEMA_SLOW)
        
        # Add Volume filter
        dataframe['volume_mean_24'] = dataframe['volume'].rolling(window=self.VOLUME_WINDOW).mean()
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # We override the base entry logic, but keep the BTC gate logic
        # DEMA cross instead of EMA cross
        cross_up = qtpylib.crossed_above(dataframe["dema_fast"], dataframe["dema_slow"])
        uptrend = dataframe["close"] > dataframe["ema_trend"]
        trending = dataframe["adx"] > self.ADX_MIN
        
        # Volume surge condition
        volume_surge = dataframe["volume"] > (dataframe['volume_mean_24'] * self.VOLUME_MULTIPLIER)
        
        # Base condition
        dataframe.loc[
            (cross_up & uptrend & trending & volume_surge),
            ["enter_long", "enter_tag"]
        ] = (1, "dema_vol_surge")
        
        # Apply the BTC macro gate from WTE_btc200
        if "btc_uptrend_4h" in dataframe.columns:
            dataframe.loc[dataframe["btc_uptrend_4h"] != 1, ["enter_long", "enter_tag"]] = (0, None)
            
        return dataframe
