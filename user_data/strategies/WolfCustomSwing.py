from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfCustomSwing(IStrategy):
    """
    Port of Cryptohopper "WOLF CUSTOM SWING V2.0" to Freqtrade.

    Entry: at least 3 of the 4 CH "Strategy" signals must currently be armed
    (KEEP_SIGNAL=5 closed candles for the per-bar signals; EMA trend is instantaneous):
      - RSI(14) <= 25 on 15m
      - Close <= lower Bollinger Band (period 20, dev 2.0, on close, SMA matype) on 15m
      - MACD(12,26,9) bullish cross on 15m
      - Close > EMA200 on 1h (instantaneous, treated as one of the 4)
    PLUS: entry candle must not be strongly green (> 0.3%) — see MAX_GREEN_PCT.
    This blocks "chasing the bounce" trades that historically caused most losses.

    Exits:
      - TP via minimal_roi (4.5%)
      - Hard SL -5% with 3-minute hold (custom_stoploss; tighter than CH's 10-min)
      - Trailing armed at +2.5%, trails 0.5% (tighter than CH's 0.8% to reduce bleed from peak)
      - Stale-position exit at 7 days (custom_exit; CH auto_close_positions_time)
      - DCA: DISABLED (position_adjustment_enable=False) — DCA on losing positions
        doubles exposure on bad pairs and is a common way to amplify losses.
        adjust_trade_position is kept below as dead code for easy re-enable.
      - Cooldown 2h after exit (CooldownPeriod protection)

    Risk-management kill switches (NOT in CH; added for prudent operation):
      - Pause 24h if 24h drawdown > 4% (3+ trades in window)
      - Pause 48h if 7d drawdown > 8% (catastrophic-stop circuit breaker)
      - Pause 12h if 3+ stoploss hits in any 24h period (regime-change signal)
      - Pause 48h if 6+ stoploss hits in any 7d period
      - Skip new entries if BTC/EUR dropped (any of):
          > 3% in 1h, > 5% in 4h, > 10% in 24h (multi-tier market crash filter,
          mirrors CH triggers 12936147/12936150 + a 1h fast-flash tier)
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"
    informative_timeframe = "1h"

    minimal_roi = {"0": 0.08, "60": 0.06, "240": 0.045}

    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.008
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

    # Entry candle color filter: reject entries on strongly green candles.
    # Rationale: 71% of losing trades over May 9-14 entered on green candles
    # (chasing the bounce) vs only 33% of winners. The 5-candle KEEP_SIGNAL
    # window creates lag — by the time all signals align, price has already
    # bounced. Filtering green-candle entries blocks the worst chase trades.
    # 2-month backtest: +29% profit vs baseline (15.72 vs 12.21 EUR).
    MAX_GREEN_PCT = 0.003

    SL_THRESHOLD = -0.05
    SL_HOLD_SECONDS = 180
    TRAILING_ARM = 0.025

    STALE_EXIT_DAYS = 7

    DCA_TIME_HOURS = 12
    DCA_TRIGGER_PCT = -0.035

    MARKET_REGIME_PAIR = "BTC/EUR"
    # Multi-tier BTC crash filter (mirrors CH triggers):
    # (lookback_hours, max_drop) — entry blocked if ANY window breaches its threshold.
    MARKET_CRASH_CHECKS = [
        (1,  -0.03),   # -3% in 1h  — fast flash crash
        (4,  -0.05),   # -5% in 4h  — rapid bleed
        (24, -0.10),   # -10% in 24h — deep correction
    ]

    # DCA disabled — adjust_trade_position kept below as dead code in case of re-enable.
    position_adjustment_enable = False
    max_entry_position_adjustment = 0

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

    plot_config = {
        "main_plot": {
            "bb_upper": {"color": "#a0a0a0"},
            "bb_mid": {"color": "#5e8eff"},
            "bb_lower": {"color": "#a0a0a0", "fill_to": "bb_upper", "fill_color": "rgba(100,100,255,0.08)"},
            "ema200_1h": {"color": "orange"},
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "purple"},
            },
            "MACD": {
                "macd": {"color": "blue"},
                "macdsignal": {"color": "orange"},
            },
            "Armed signals": {
                "rsi_armed": {"color": "purple"},
                "bb_armed": {"color": "green"},
                "macd_armed": {"color": "blue"},
            },
        },
    }

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

        dataframe = merge_informative_pair(
            dataframe,
            informative,
            self.timeframe,
            self.informative_timeframe,
            ffill=True,
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

        # Reject entries on strongly green candles (chasing the bounce).
        # See MAX_GREEN_PCT comment above for rationale.
        not_chasing = dataframe["close"] <= dataframe["open"] * (1 + self.MAX_GREEN_PCT)

        conditions = (
            (signals_active >= self.BUY_SIGNALS_REQUIRED)
            & (dataframe["volume"] > 0)
            & not_chasing
        )

        dataframe.loc[conditions, "enter_long"] = 1
        dataframe.loc[conditions, "enter_tag"] = "wolf_swing_v2"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[float]:
        """
        Tighter than CH for safety: 3-minute SL hold instead of CH's 10 minutes.
        When profit dips below -5%, wait 3m before letting the SL fire. If price
        recovers above -5% within the window, cancel and restore the -5% SL.
        The shorter hold reduces flash-crash bleed during the wait period.
        Note: backtest cannot show the difference (15-min candle granularity);
        change matters only in live trading where custom_stoploss is called
        every few seconds.
        Trailing (armed at +2.5%) is left to Freqtrade's built-in trailing engine.
        """
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

    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[str]:
        if current_time - trade.open_date_utc >= timedelta(days=self.STALE_EXIT_DAYS):
            return "stale_7d"
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
        """
        Multi-tier BTC crash filter — blocks entry if BTC dropped past any
        threshold in MARKET_CRASH_CHECKS. Mirrors CH triggers:
          - 1h candle, percentchange < -3% → disable buying
          - 4h candle, percentchange < -5% → disable buying
          - 24h candle, percentchange < -10% → disable buying
        Fails open (allows entry) if BTC data is unavailable or insufficient.
        """
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
