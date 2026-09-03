from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA_hopt_ch20(IStrategy):
    """
    Hyperopt-tuned WolfTrend_EMA_hopt_tuned (8080) + true Chandelier exit.
    Same entry params as the live 8080 bot (EMA 20/71/105, ADX>15) but the
    fixed -2.4% stop is replaced by chandelier (peak high since entry minus
    N × ATR). The EMA cross exit is kept.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    trailing_stop = False
    use_custom_stoploss = True
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 350

    EMA_FAST = 20
    EMA_SLOW = 71
    EMA_TREND = 105
    ADX_MIN = 15
    ATR_MULT = 2.0
    ATR_MIN_STOP = 0.005
    ATR_MAX_STOP = 0.50

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"]  = ta.EMA(dataframe, timeperiod=self.EMA_FAST)
        dataframe["ema_slow"]  = ta.EMA(dataframe, timeperiod=self.EMA_SLOW)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.EMA_TREND)
        dataframe["adx"]       = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"]       = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
        uptrend = dataframe["close"] > dataframe["ema_trend"]
        trending = dataframe["adx"] > self.ADX_MIN
        dataframe.loc[
            (cross_up & uptrend & trending & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "hopt_ch20")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_down = qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])
        dataframe.loc[cross_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_exit")
        return dataframe

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs) -> Optional[float]:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0 or current_rate <= 0:
            return None
        atr = df["atr"].iloc[-1]
        if atr is None or atr <= 0:
            return None
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        df_since = df[df["date"] >= open_date]
        if df_since.empty:
            peak = current_rate
        else:
            peak = max(float(df_since["high"].max()), current_rate)
        stop_price = peak - self.ATR_MULT * atr
        stop_dist = (current_rate - stop_price) / current_rate
        stop_dist = max(self.ATR_MIN_STOP, min(stop_dist, self.ATR_MAX_STOP))
        return -stop_dist
