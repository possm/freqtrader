from datetime import datetime
from typing import Optional

import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class WolfDCA(IStrategy):
    """
    Route 1: Dollar Cost Averaging.

    Strategy: koop BTC/EUR en ETH/EUR elke maandag 00:00 UTC.
    Geen exits — alle posities worden force-closed aan einde backtest
    (toont de werkelijke buy-and-hold performance).

    Only fires on BTC/EUR and ETH/EUR to avoid spreading thin across alts.
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"

    # No selling during backtest — force-exit at end shows true HODL P&L
    minimal_roi = {"0": 99}
    stoploss = -0.99

    trailing_stop = False
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False

    startup_candle_count: int = 1

    # Only DCA into these
    DCA_PAIRS = ["BTC/EUR", "ETH/EUR"]

    protections = []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dt = pd.to_datetime(dataframe["date"])
        dataframe["weekday"] = dt.dt.dayofweek
        dataframe["hour"] = dt.dt.hour
        dataframe["minute"] = dt.dt.minute
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if metadata["pair"] not in self.DCA_PAIRS:
            return dataframe

        # Monday 00:00 UTC candle
        monday_open = (
            (dataframe["weekday"] == 0) &
            (dataframe["hour"] == 0) &
            (dataframe["minute"] == 0) &
            (dataframe["volume"] > 0)
        )
        dataframe.loc[monday_open, ["enter_long", "enter_tag"]] = (1, "dca_weekly")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
