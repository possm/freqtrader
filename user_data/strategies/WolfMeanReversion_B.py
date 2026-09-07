from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfMeanReversion_B(IStrategy):
    """
    ITERATION B: Bigger wins — let winners run further.

    Goal: stop cutting wins at +1-3% via aggressive ROI ladder.
    Instead:
      - High ROI cap (8%) — only fires on big moves
      - BB middle exit raised to +2% profit minimum (let it grow more)
      - Trailing stop catches reversals after wins develop
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"

    # Loose ROI cap — only fires on big winners
    minimal_roi = {"0": 0.08, "120": 0.05, "240": 0.03}

    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.012      # 1.2% trail
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 50

    # Same timeout as base
    LOSS_TIMEOUT_CANDLES = 4
    LOSS_TIMEOUT_THRESHOLD = 0.0

    # CHANGED: BB middle exit fires at +2% profit (was +1%) — give wins room to grow
    BB_EXIT_MIN_PROFIT = 0.02

    MARKET_REGIME_PAIR = "BTC/EUR"
    MARKET_CRASH_CHECKS = [(1, -0.03), (4, -0.05), (24, -0.10)]

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 4},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.04},
        {"method": "MaxDrawdown", "lookback_period_candles": 672, "trade_limit": 8,
         "stop_duration_candles": 192, "max_allowed_drawdown": 0.08},
        {"method": "StoplossGuard", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 48, "only_per_pair": False},
    ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 30) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "bb_rsi_oversold_B")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()

        elapsed_seconds = (current_time - trade.open_date_utc).total_seconds()
        candles_elapsed = int(elapsed_seconds / (15 * 60))

        # 1. Take profit at BB middle return — but only with at least +2% profit
        if current_rate > last_candle["bb_middleband"] and current_profit > self.BB_EXIT_MIN_PROFIT:
            return "swing_target_reached"

        # 2. Original loss timeout
        if current_profit < self.LOSS_TIMEOUT_THRESHOLD and candles_elapsed >= self.LOSS_TIMEOUT_CANDLES:
            return "winst_is_verlies_timeout"

        return None

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        try:
            btc_df = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h")
            btc_now = float(btc_df["close"].iloc[-1])
            for hours, threshold in self.MARKET_CRASH_CHECKS:
                needed = hours + 1
                if len(btc_df) < needed:
                    continue
                btc_then = float(btc_df["close"].iloc[-needed])
                if btc_then <= 0:
                    continue
                change = (btc_now / btc_then) - 1.0
                if change < threshold:
                    return False
        except Exception:
            return True
        return True
