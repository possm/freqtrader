from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_DonchianBTC(IStrategy):
    """
    Classic Turtle-style trend following on 4h.
    Philosophy OPPOSITE of mean reversion: cut losses fast, let winners run.

    Entry (breakout):
      - close breaks above the previous 20-period Donchian high (new 20-bar high)
      - close > EMA200 (long-term uptrend confirmed)
      - ADX > 20 (market is actually trending, not chopping)
    Exit (trend over):
      - close breaks below the previous 10-period Donchian low
    Risk:
      - wide -12% hard stop (trend trades need room; the Donchian-low exit
        normally fires first)
      - NO minimal_roi cap — winners ride until trend breaks
      - NO trailing stop — Donchian-low IS the trailing mechanism
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    # ROI effectively disabled — let trends run.
    minimal_roi = {"0": 100.0}
    stoploss = -0.12
    trailing_stop = False
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    DONCHIAN_ENTRY = 20
    DONCHIAN_EXIT = 10
    ADX_MIN = 20

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    MARKET_REGIME_PAIR = "BTC/USDT"

    def informative_pairs(self):
        return [(self.MARKET_REGIME_PAIR, "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        # Donchian channels (use prior candle's extreme so we don't peek)
        dataframe["dc_upper"] = dataframe["high"].rolling(self.DONCHIAN_ENTRY).max()
        dataframe["dc_lower"] = dataframe["low"].rolling(self.DONCHIAN_EXIT).min()

        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["btc_ema200"] = ta.EMA(btc_4h, timeperiod=200)
        btc_4h["btc_up"] = (btc_4h["close"] > btc_4h["btc_ema200"]).astype(int)
        dataframe = dataframe.merge(
            btc_4h[["date", "btc_up"]], on="date", how="left")
        dataframe["btc_up"] = dataframe["btc_up"].ffill().fillna(0).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        breakout = dataframe["close"] > dataframe["dc_upper"].shift(1)
        uptrend = dataframe["close"] > dataframe["ema200"]
        trending = dataframe["adx"] > self.ADX_MIN
        dataframe.loc[
            (breakout & uptrend & trending & (dataframe["btc_up"] == 1) & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "donchian_btc")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when price breaks the 10-period low (trend reversal)
        dataframe.loc[
            (dataframe["close"] < dataframe["dc_lower"].shift(1)),
            ["exit_long", "exit_tag"]
        ] = (1, "donchian_exit")
        return dataframe
