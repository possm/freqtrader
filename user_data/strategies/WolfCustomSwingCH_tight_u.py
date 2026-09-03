from datetime import datetime, timedelta, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfCustomSwingCH_tight_u(IStrategy):
    """
    WolfCustomSwingCH with tighter risk params for backtest comparison:
      - SL: -2% (from -5%)
      - Trailing arm: 1.5% (from 2.5%)
      - Trail: 0.5% (unchanged)
      - use_custom_stoploss disabled — static SL fires accurately at 15m resolution
    Everything else (entry signals, DCA, cooldown, protections) identical to WolfCustomSwingCH.
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"
    informative_timeframe = "1h"

    minimal_roi = {"0": 0.035}

    stoploss = -0.02
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 250

    KEEP_SIGNAL = 5
    BUY_SIGNALS_REQUIRED = 1

    STALE_EXIT_DAYS = 3

    DCA_TIME_HOURS = 12
    DCA_TRIGGER_PCT = -0.035

    MARKET_REGIME_PAIR = "BTC/USDT"
    MARKET_CRASH_CHECKS = [
        (1,  -0.03),
        (4,  -0.05),
        (24, -0.10),
    ]

    position_adjustment_enable = True
    max_entry_position_adjustment = 1

    protections = [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 8,
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 96,
            "trade_limit": 3,
            "stop_duration_candles": 96,
            "max_allowed_drawdown": 0.04,
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 672,
            "trade_limit": 8,
            "stop_duration_candles": 192,
            "max_allowed_drawdown": 0.08,
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 96,
            "trade_limit": 3,
            "stop_duration_candles": 48,
            "only_per_pair": False,
        },
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 672,
            "trade_limit": 6,
            "stop_duration_candles": 192,
            "only_per_pair": False,
        },
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, self.informative_timeframe) for pair in pairs]
        if (self.MARKET_REGIME_PAIR, self.informative_timeframe) not in informative:
            informative.append((self.MARKET_REGIME_PAIR, self.informative_timeframe))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        bb = qtpylib.bollinger_bands(dataframe["close"], window=20, stds=2)
        dataframe["bb_lower"] = bb["lower"]
        dataframe["bb_mid"] = bb["mid"]
        dataframe["bb_upper"] = bb["upper"]

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macd_cross_up"] = qtpylib.crossed_above(
            dataframe["macd"], dataframe["macdsignal"]
        )

        rsi_fired = (dataframe["rsi"] <= 25).astype(int)
        bb_fired = (dataframe["close"] <= dataframe["bb_lower"]).astype(int)
        macd_fired = dataframe["macd_cross_up"].astype(int)

        window = self.KEEP_SIGNAL
        dataframe["rsi_armed"] = rsi_fired.rolling(window, min_periods=1).max()
        dataframe["bb_armed"] = bb_fired.rolling(window, min_periods=1).max()
        dataframe["macd_armed"] = macd_fired.rolling(window, min_periods=1).max()

        informative = self.dp.get_pair_dataframe(
            pair=metadata["pair"], timeframe=self.informative_timeframe
        )
        informative["ema200"] = ta.EMA(informative, timeperiod=200)
        informative["ema_cross_up"] = qtpylib.crossed_above(
            informative["close"], informative["ema200"]
        ).astype(int)

        dataframe = merge_informative_pair(
            dataframe,
            informative,
            self.timeframe,
            self.informative_timeframe,
            ffill=True,
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_cross_col = f"ema_cross_up_{self.informative_timeframe}"

        signals_active = (
            dataframe["rsi_armed"].fillna(0).astype(int)
            + dataframe["bb_armed"].fillna(0).astype(int)
            + dataframe["macd_armed"].fillna(0).astype(int)
            + dataframe[ema_cross_col].fillna(0).astype(int)
        )

        conditions = (
            (signals_active >= self.BUY_SIGNALS_REQUIRED)
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[conditions, "enter_long"] = 1
        dataframe.loc[conditions, "enter_tag"] = "wolf_swing_v2_ch"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        if (ct - open_date) >= timedelta(days=self.STALE_EXIT_DAYS):
            return "stale_exit"
        return None

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> bool:
        try:
            btc_df = self.dp.get_pair_dataframe(
                pair=self.MARKET_REGIME_PAIR,
                timeframe=self.informative_timeframe,
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

    def adjust_trade_position(
        self,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: Optional[float],
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs,
    ) -> Optional[float]:
        if trade.nr_of_successful_entries >= 2:
            return None

        hours_open = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        if hours_open < self.DCA_TIME_HOURS:
            return None

        if current_profit > self.DCA_TRIGGER_PCT:
            return None

        filled_entries = trade.select_filled_orders(trade.entry_side)
        if not filled_entries:
            return None
        first_stake = filled_entries[0].cost
        return first_stake
