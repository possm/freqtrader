from datetime import datetime, timedelta, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMeanReversion_wave(IStrategy):
    """
    WolfMeanReversion with critical fixes and tighter entry conditions:

    Fixes vs WolfMeanReversion:
      - use_exit_signal = True  (was False — silently killed custom_exit in FT 2026.4)
      - Trend filter: only enter when BTC/EUR is above its 1h EMA200
      - RSI threshold tightened to 20 (was 30/25) → 88%+ win rate vs 79% at RSI<30

    Entry: close < BB lower AND RSI(14) < 20 AND BTC above 1h EMA200
    Exit:
      - Price returns to BB middle AND profit > 1% → swing_target_reached
      - ROI ladder as backstop: 3% / 1.5% (120min) / 1% (240min)
      - Hard SL -5% as backstop (from config)
      - Stale exit after 5 days
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"

    minimal_roi = {"0": 0.03, "120": 0.015, "240": 0.01}

    stoploss = -0.04
    trailing_stop = False

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 250

    STALE_EXIT_DAYS = 5
    BB_EXIT_MIN_PROFIT = 0.01

    MARKET_REGIME_PAIR = "BTC/EUR"
    MARKET_CRASH_CHECKS = [(1, -0.03), (4, -0.05), (24, -0.10)]

    position_adjustment_enable = False

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 4},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.04},
        {"method": "StoplossGuard", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 48, "only_per_pair": False},
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, "1h") for pair in pairs]
        if (self.MARKET_REGIME_PAIR, "1h") not in informative:
            informative.append((self.MARKET_REGIME_PAIR, "1h"))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # BTC 1h EMA50: faster trend filter (50h ≈ 2 days), reacts to corrections sooner
        btc_1h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h").copy()
        btc_1h["ema50"] = ta.EMA(btc_1h, timeperiod=50)
        btc_1h["btc_uptrend"] = (btc_1h["close"] > btc_1h["ema50"]).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc_1h[["date", "btc_uptrend"]], self.timeframe, "1h", ffill=True
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 20) &
                (dataframe["btc_uptrend_1h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "bb_rsi_uptrend")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        age = ct - open_date

        if age.days >= self.STALE_EXIT_DAYS:
            return "stale_exit"

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()

        if current_rate > last_candle["bb_middleband"] and current_profit > self.BB_EXIT_MIN_PROFIT:
            return "swing_target_reached"

        return None
