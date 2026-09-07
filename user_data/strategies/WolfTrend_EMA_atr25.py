from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA_atr25(IStrategy):
    """
    WolfTrend_EMA with an ATR trailing stop (Chandelier-style) replacing the
    fixed -12% hard stop. ATR_MULT x ATR(14) below the running peak; freqtrade
    only ratchets the stop UP, so it trails price.

    Same entry as WolfTrend_EMA (EMA20>EMA50 cross + price>EMA200 + ADX>20),
    plus the EMA-cross exit kept as a secondary (whichever fires first). Goal:
    cut the per-whipsaw loss in chop years (2022/2025) without delaying entries
    so the 2023 bull harvest is preserved.

    ATR_MULT = 2.5 (textbook Chandelier).
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 100.0}
    stoploss = -0.99               # catastrophe backstop; ATR custom_stoploss governs
    trailing_stop = False
    use_custom_stoploss = True
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    ADX_MIN = 20
    ATR_MULT = 2.5
    ATR_MIN_STOP = 0.02            # never tighter than 2%
    ATR_MAX_STOP = 0.30            # never wider than 30%

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = qtpylib.crossed_above(dataframe["ema20"], dataframe["ema50"])
        uptrend = dataframe["close"] > dataframe["ema200"]
        trending = dataframe["adx"] > self.ADX_MIN
        dataframe.loc[
            (cross_up & uptrend & trending & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "ema_atr25")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_down = qtpylib.crossed_below(dataframe["ema20"], dataframe["ema50"])
        dataframe.loc[cross_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_exit")
        return dataframe

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs) -> Optional[float]:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return None
        atr = df["atr"].iloc[-1]
        if atr is None or atr <= 0 or current_rate <= 0:
            return None
        stop_dist = (self.ATR_MULT * atr) / current_rate
        stop_dist = max(self.ATR_MIN_STOP, min(stop_dist, self.ATR_MAX_STOP))
        return -stop_dist
