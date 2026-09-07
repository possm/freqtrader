from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfCustomSwing_wider_trail_u(IStrategy):
    """
    OPTION 2: Wider trailing stop (1.5% instead of 0.8%) on top of no_chase filter.
    Lets winners run further before stopping out.
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"
    informative_timeframe = "1h"

    minimal_roi = {"0": 0.08, "60": 0.06, "240": 0.045}

    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.015          # CHANGED: 0.008 → 0.015 (wider)
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    use_custom_stoploss = True

    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 250

    KEEP_SIGNAL = 5
    BUY_SIGNALS_REQUIRED = 3
    MAX_GREEN_PCT = 0.003

    SL_THRESHOLD = -0.05
    SL_HOLD_SECONDS = 180
    TRAILING_ARM = 0.025

    STALE_EXIT_DAYS = 7
    DCA_TIME_HOURS = 12
    DCA_TRIGGER_PCT = -0.035

    MARKET_REGIME_PAIR = "BTC/USDT"
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

    def populate_indicators(self, dataframe, metadata):
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bb = qtpylib.bollinger_bands(dataframe["close"], window=20, stds=2)
        dataframe["bb_lower"] = bb["lower"]
        dataframe["bb_mid"] = bb["mid"]
        dataframe["bb_upper"] = bb["upper"]
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macd_cross_up"] = qtpylib.crossed_above(dataframe["macd"], dataframe["macdsignal"])

        rsi_fired = (dataframe["rsi"] <= 25).astype(int)
        bb_fired = (dataframe["close"] <= dataframe["bb_lower"]).astype(int)
        macd_fired = dataframe["macd_cross_up"].astype(int)

        window = self.KEEP_SIGNAL
        dataframe["rsi_armed"] = rsi_fired.rolling(window, min_periods=1).max()
        dataframe["bb_armed"] = bb_fired.rolling(window, min_periods=1).max()
        dataframe["macd_armed"] = macd_fired.rolling(window, min_periods=1).max()

        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        informative["ema200"] = ta.EMA(informative, timeperiod=200)
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        ema_col = f"ema200_{self.informative_timeframe}"
        ema_armed = (dataframe["close"] > dataframe[ema_col]).astype(int)
        signals_active = (
            dataframe["rsi_armed"].fillna(0).astype(int)
            + dataframe["bb_armed"].fillna(0).astype(int)
            + dataframe["macd_armed"].fillna(0).astype(int)
            + ema_armed
        )
        not_chasing = dataframe["close"] <= dataframe["open"] * (1 + self.MAX_GREEN_PCT)
        conditions = (signals_active >= self.BUY_SIGNALS_REQUIRED) & (dataframe["volume"] > 0) & not_chasing
        dataframe.loc[conditions, "enter_long"] = 1
        dataframe.loc[conditions, "enter_tag"] = "wolf_wider_trail"
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        return dataframe

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_profit > self.SL_THRESHOLD:
            was_loosened = trade.get_custom_data("sl_loosened", False)
            if was_loosened:
                trade.set_custom_data("sl_breach_at", None)
                trade.set_custom_data("sl_loosened", False)
                if current_profit < self.TRAILING_ARM:
                    return self.SL_THRESHOLD
            return None
        breach_at = trade.get_custom_data("sl_breach_at", None)
        if breach_at is None:
            trade.set_custom_data("sl_breach_at", int(current_time.timestamp()))
            trade.set_custom_data("sl_loosened", True)
            return -0.99
        elapsed = current_time.timestamp() - breach_at
        if elapsed < self.SL_HOLD_SECONDS:
            return -0.99
        trade.set_custom_data("sl_loosened", False)
        return self.SL_THRESHOLD

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(days=self.STALE_EXIT_DAYS):
            return "stale_7d"
        return None

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs):
        try:
            btc_df = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe=self.informative_timeframe)
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
