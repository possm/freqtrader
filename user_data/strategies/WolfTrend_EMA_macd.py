import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from WolfTrend_EMA import WolfTrend_EMA


class WolfTrend_EMA_macd(WolfTrend_EMA):
    """
    WolfTrend_EMA with an additional MACD entry filter.
    Only enters when MACD line > signal line (standard 12/26/9 settings).
    Avoids entering on the back side of a move or into congested price action.
    """

    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        macd, macdsignal, macdhist = ta.MACD(
            dataframe["close"], fastperiod=12, slowperiod=26, signalperiod=9
        )
        dataframe["macd"] = macd
        dataframe["macdsignal"] = macdsignal
        dataframe["macdhist"] = macdhist
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        cross_up = qtpylib.crossed_above(dataframe["ema20"], dataframe["ema50"])
        uptrend  = dataframe["close"] > dataframe["ema200"]
        trending = dataframe["adx"] > self.ADX_MIN
        macd_ok  = dataframe["macd"] > dataframe["macdsignal"]
        dataframe.loc[
            (cross_up & uptrend & trending & macd_ok & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "ema_cross_macd")
        return dataframe
