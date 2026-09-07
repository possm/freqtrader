from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair


class WolfCustomSwing_Hyper(IStrategy):
    """
    Hyperoptable variant of WolfCustomSwing.

    Parameters opened up:
      BUY:    rsi_threshold, bb_period, bb_stds,
              keep_signal_candles, signals_required, max_green_pct
      SELL:   trailing_arm
      ROI:    auto
      STOPLOSS: auto (-0.08 to -0.03)
      TRAILING: auto

    use_custom_stoploss DISABLED for clean stoploss optimization (the original's
    3-min hold logic masks SL tightening at 15-min backtest granularity).

    Run with:
      freqtrade hyperopt --strategy WolfCustomSwing_Hyper \\
        --hyperopt-loss ProfitDrawDownHyperOptLoss \\
        --spaces buy sell stoploss trailing roi \\
        --timerange 20260214-20260516 --epochs 200
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"
    informative_timeframe = "1h"

    # Defaults — hyperopt starting points
    minimal_roi = {"0": 0.08, "60": 0.06, "240": 0.045}
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    # ───── HYPEROPTABLE PARAMETERS ─────
    # BUY space — entry signal tuning
    rsi_threshold = IntParameter(15, 35, default=25, space="buy", optimize=True)
    bb_period = IntParameter(10, 30, default=20, space="buy", optimize=True)
    bb_stds = DecimalParameter(1.5, 3.0, default=2.0, decimals=1, space="buy", optimize=True)
    keep_signal_candles = IntParameter(1, 8, default=5, space="buy", optimize=True)
    signals_required = IntParameter(2, 4, default=3, space="buy", optimize=True)
    max_green_pct = DecimalParameter(0.001, 0.020, default=0.003, decimals=3,
                                     space="buy", optimize=True)

    # SELL space — trailing arm threshold
    trailing_arm = DecimalParameter(0.010, 0.050, default=0.025, decimals=3,
                                    space="sell", optimize=True)

    STALE_EXIT_DAYS = 7

    MARKET_REGIME_PAIR = "BTC/EUR"
    MARKET_CRASH_CHECKS = [(1, -0.03), (4, -0.05), (24, -0.10)]

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 8},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.04},
        {"method": "MaxDrawdown", "lookback_period_candles": 672, "trade_limit": 8,
         "stop_duration_candles": 192, "max_allowed_drawdown": 0.08},
        {"method": "StoplossGuard", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 48, "only_per_pair": False},
        {"method": "StoplossGuard", "lookback_period_candles": 672, "trade_limit": 6,
         "stop_duration_candles": 192, "only_per_pair": False},
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, self.informative_timeframe) for pair in pairs]
        if (self.MARKET_REGIME_PAIR, self.informative_timeframe) not in informative:
            informative.append((self.MARKET_REGIME_PAIR, self.informative_timeframe))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        bb = qtpylib.bollinger_bands(
            dataframe["close"],
            window=self.bb_period.value,
            stds=self.bb_stds.value,
        )
        dataframe["bb_lower"] = bb["lower"]
        dataframe["bb_mid"] = bb["mid"]
        dataframe["bb_upper"] = bb["upper"]

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macd_cross_up"] = qtpylib.crossed_above(
            dataframe["macd"], dataframe["macdsignal"]
        )

        rsi_fired = (dataframe["rsi"] <= self.rsi_threshold.value).astype(int)
        bb_fired = (dataframe["close"] <= dataframe["bb_lower"]).astype(int)
        macd_fired = dataframe["macd_cross_up"].astype(int)

        window = self.keep_signal_candles.value
        dataframe["rsi_armed"] = rsi_fired.rolling(window, min_periods=1).max()
        dataframe["bb_armed"] = bb_fired.rolling(window, min_periods=1).max()
        dataframe["macd_armed"] = macd_fired.rolling(window, min_periods=1).max()

        informative = self.dp.get_pair_dataframe(
            pair=metadata["pair"], timeframe=self.informative_timeframe
        )
        informative["ema200"] = ta.EMA(informative, timeperiod=200)

        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True,
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_col = f"ema200_{self.informative_timeframe}"

        ema_armed = (dataframe["close"] > dataframe[ema_col]).astype(int)
        signals_active = (
            dataframe["rsi_armed"].fillna(0).astype(int)
            + dataframe["bb_armed"].fillna(0).astype(int)
            + dataframe["macd_armed"].fillna(0).astype(int)
            + ema_armed
        )

        not_chasing = dataframe["close"] <= dataframe["open"] * (1 + self.max_green_pct.value)

        conditions = (
            (signals_active >= self.signals_required.value)
            & (dataframe["volume"] > 0)
            & not_chasing
        )

        dataframe.loc[conditions, "enter_long"] = 1
        dataframe.loc[conditions, "enter_tag"] = "wolf_hyper"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(days=self.STALE_EXIT_DAYS):
            return "stale_7d"
        return None

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        try:
            btc_df = self.dp.get_pair_dataframe(
                pair=self.MARKET_REGIME_PAIR, timeframe=self.informative_timeframe,
            )
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
