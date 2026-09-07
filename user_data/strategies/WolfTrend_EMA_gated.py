from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA_gated(IStrategy):
    """
    Regime-gated EMA-crossover trend following.

    Same engine as WolfTrend_EMA (EMA20>EMA50 cross, price>EMA200, ADX>20,
    let winners run, exit on EMA20<EMA50 cross) BUT only fires when BTC is in
    a confirmed MACRO uptrend: BTC/USDT close > BTC/USDT 4h EMA200.

    Goal: keep the explosive bull-year harvest (2023 +55%) while skipping the
    choppy/down years (2022, 2025) where ungated trend bleeds via whipsaws.

    macro gate = BTC > EMA200(4h) ≈ 33-day trend. Standard, not cherry-picked.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 100.0}
    stoploss = -0.12
    trailing_stop = False
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    ADX_MIN = 20
    MARKET_REGIME_PAIR = "BTC/USDT"

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return [(self.MARKET_REGIME_PAIR, "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["btc_ema200"] = ta.EMA(btc_4h, timeperiod=200)
        btc_4h["btc_macro_up"] = (btc_4h["close"] > btc_4h["btc_ema200"]).astype(int)
        dataframe = dataframe.merge(
            btc_4h[["date", "btc_macro_up"]], on="date", how="left")
        dataframe["btc_macro_up"] = dataframe["btc_macro_up"].ffill().fillna(0).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = qtpylib.crossed_above(dataframe["ema20"], dataframe["ema50"])
        uptrend = dataframe["close"] > dataframe["ema200"]
        trending = dataframe["adx"] > self.ADX_MIN
        macro = dataframe["btc_macro_up"] == 1
        dataframe.loc[
            (cross_up & uptrend & trending & macro & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "ema_gated")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_down = qtpylib.crossed_below(dataframe["ema20"], dataframe["ema50"])
        dataframe.loc[cross_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_exit")
        return dataframe
