from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class WolfGrid(IStrategy):
    """
    Route 3: Grid-like dip buying.

    Niet een echte grid (FreqTrade supports geen native grids), maar
    een DIP-BUYER met vaste take-profit:
      Entry: prijs is X% gedaald vanaf recente 24h high
      Exit:  +Y% profit OF -SL stoploss

    Past bij choppy markets — vangt elke dip en verkoopt op rebound.
    Verliest in trending markets (kapt winners af bij eerste pop).

    Tuned voor choppy regime:
      Dip threshold: -3.5% van recent 24h high
      TP:            +2.5%
      SL:            -7% (wide — laat dip zich uitspelen)
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"

    minimal_roi = {"0": 0.025}     # Sell at +2.5% — pure grid-like

    stoploss = -0.07               # Wide — dip kan dieper gaan
    trailing_stop = False

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False

    startup_candle_count: int = 96   # 24h on 15m

    # Grid params
    DIP_THRESHOLD = -0.035          # buy if -3.5% from recent high
    LOOKBACK_CANDLES = 96           # 24h
    COOLDOWN_AFTER_TP = 4           # 1h cooldown after exit

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 4},  # 1h between grid trades on same pair
    ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Recent 24h high (excluding current candle)
        dataframe["recent_high"] = dataframe["high"].rolling(self.LOOKBACK_CANDLES).max().shift(1)
        dataframe["pct_from_high"] = (dataframe["close"] - dataframe["recent_high"]) / dataframe["recent_high"]
        # Volume average for noise filter
        dataframe["vol_avg"] = dataframe["volume"].rolling(48).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["pct_from_high"] <= self.DIP_THRESHOLD) &
                (dataframe["volume"] > dataframe["vol_avg"] * 0.5) &   # Avoid dead candles
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "grid_dip")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
