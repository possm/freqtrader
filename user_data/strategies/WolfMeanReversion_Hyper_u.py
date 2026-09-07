from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class WolfMeanReversion_Hyper_u(IStrategy):
    """
    Hyperoptable variant of WolfMeanReversion_AB.

    Parameters opened up for optimization:
      BUY space:    rsi_threshold, bb_period, bb_stds
      SELL space:   loss_timeout_candles, loss_timeout_threshold,
                    bb_exit_min_profit
      STOPLOSS:     stoploss (-0.10 to -0.02)
      TRAILING:     trailing_stop_positive, trailing_stop_positive_offset
      ROI:          auto-explored by hyperopt

    Run with:
      freqtrade hyperopt --strategy WolfMeanReversion_Hyper \\
        --hyperopt-loss SharpeHyperOptLossDaily \\
        --spaces buy sell stoploss trailing roi \\
        --timerange 20260214-20260516 --epochs 200
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"

    # Defaults — these become starting points for hyperopt
    minimal_roi = {"0": 0.08, "120": 0.05, "240": 0.03}
    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 50

    # ───── HYPEROPTABLE PARAMETERS ─────
    # Buy space — entry conditions
    rsi_threshold = IntParameter(15, 40, default=30, space="buy", optimize=True)
    bb_period = IntParameter(10, 30, default=20, space="buy", optimize=True)
    bb_stds = DecimalParameter(1.5, 3.0, default=2.0, decimals=1, space="buy", optimize=True)

    # Sell space — exit timing
    loss_timeout_candles = IntParameter(1, 8, default=2, space="sell", optimize=True)
    loss_timeout_threshold = DecimalParameter(-0.03, -0.005, default=-0.015, decimals=3,
                                              space="sell", optimize=True)
    bb_exit_min_profit = DecimalParameter(0.005, 0.030, default=0.020, decimals=3,
                                          space="sell", optimize=True)

    MARKET_REGIME_PAIR = "BTC/USDT"
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
        # Bollinger Bands — bb_period and bb_stds come from hyperopt
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe),
            window=self.bb_period.value,
            stds=self.bb_stds.value,
        )
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < self.rsi_threshold.value) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "bb_rsi_hyper")
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

        if current_rate > last_candle["bb_middleband"] and current_profit > self.bb_exit_min_profit.value:
            return "swing_target_reached"

        if current_profit < self.loss_timeout_threshold.value and candles_elapsed >= self.loss_timeout_candles.value:
            return "loss_timeout"

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
