"""
WolfQuantEdge — a regime-gated volatility-expansion breakout strategy.

PROVENANCE (why this strategy looks the way it does)
----------------------------------------------------
This is NOT another hand-tuned indicator stack. Every structural choice below traces to the
forward-return study in user_data/scripts/discover_signals.py, which measured the edge of
candidate signals on 2021-2026 Binance data *net of the Kraken execution tax* modelled in
kraken_slippage.py. The headline results (pooled over 17 pairs):

    signal                         regime   hold    gross%   NET%(after Kraken)   n      t
    Keltner-upper + ATR-expansion  trend    4-8d    +2.3..2.9  +1.16 .. +1.75    7160  13-15   <-- core edge
    Donchian-20 breakout           trend    4-8d    +1.4..1.7  +0.32 .. +0.60    5510   7-9
    z-score dip (<-2)              TREND    8d      +1.60      +0.37             7716   9.5    <-- DCA rationale
    z-score dip (<-2)              range    *       negative   -2.9 (!)          ...           <-- never buy chop
    VWAP-dev / volume-imbalance    *        *       ~0         net <= 0                         (dropped)

Conclusions baked into the code:
  1. The only edge that comfortably clears the Kraken tax is a VOLATILITY-EXPANSION BREAKOUT
     confirmed by an ATR expansion, and ONLY while the market is in a directional (trend)
     regime — measured by the Kaufman Efficiency Ratio. -> primary entry.
  2. Mean-reversion dips are profitable ONLY as pullbacks *inside* an established uptrend, and
     are catastrophic in chop. We therefore do not trade dips as standalone entries; we use
     them to scale INTO an existing winning-regime position. -> non-linear DCA.
  3. Edge grows with holding time (peaks at 4-8 days), so we let winners run: loose, time-
     decaying ROI + a trailing stop, and we exit on a genuine trend break, not on noise.

EXECUTION CONTEXT
-----------------
Base timeframe 1h (entry timing); the breakout/regime structure is computed on a 4h
informative and merged down, plus a BTC 4h uptrend filter. Spot, long-only. Inherits
KrakenSlippageMixin so backtests already pay realistic Kraken spread+slippage+impact (the
mixin only bites in backtest/hyperopt; live/dry-run use real order-book pricing).

REQUIRES in the BACKTEST config: "order_types": {entry/exit: "limit"} and a Kraken-realistic
"fee" (0.0026) — that is how the limit-price slippage from the mixin actually moves fills.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, merge_informative_pair, stoploss_from_absolute

from kraken_slippage import KrakenSlippageMixin


def kaufman_er(close, n: int = 10):
    """Kaufman Efficiency Ratio: |net move| / |path length| over n bars. ~1 trend, ~0 chop."""
    change = (close - close.shift(n)).abs()
    path = close.diff().abs().rolling(n).sum()
    return change / path.replace(0, np.nan)


class WolfQuantEdge_30m2h(KrakenSlippageMixin, IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "30m"
    inf_tf = "2h"                       # informative timeframe carrying the structural edge

    can_short = False                   # spot
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 320     # enough 1h history to warm up 4h ema50/donchian/ER

    # --- exits: let winners run (edge peaks at 4-8 day holds), cut trend breaks -------------
    # ROI in MINUTES. Loose early, decays so we still bank smaller gains on stale winners.
    minimal_roi = {
        "0": 0.25,        # don't pre-empt a fresh breakout's run
        "2880": 0.12,     # after 2 days, accept 12%
        "5760": 0.06,     # after 4 days, 6%
        "8640": 0.03,     # after 6 days, 3%
    }
    stoploss = -0.11      # 4h vol is large; a tight SL just donates to noise
    # Phase-3 RESULT (iter-4/5): the native fixed trailing + the lagging ema50-break exit were the
    # main drag. Dropping the ema50 exit and instead trailing with an ATR "chandelier" (N*ATR(4h)
    # below the highest price since entry) lifted the 5-yr result +16.6% -> +69.5% AND cut max
    # drawdown 24.6% -> 18.3% (Calmar 0.66 -> 3.73), robustly across every window (flat in N=6..10,
    # not outlier-driven). The chandelier is implemented in custom_stoploss() below.
    trailing_stop = False
    use_custom_stoploss = True
    CHAND_N = 8.0         # trail 8 * ATR(4h) below the run's peak (volatility-adaptive)

    # --- non-linear DCA (Phase-2 "advanced order management") -------------------------------
    # Phase-3 RESULT: DCA is net-HARMFUL here. Across every window, disabling it both raised
    # return and CUT max drawdown (~3pp) — it was just averaging into failed breakouts. We keep
    # the (fully-working, documented) implementation below but DISABLE it by default. Flip to
    # True to re-enable; the WQE_DCAon variant re-confirms it underperforms on the current base.
    position_adjustment_enable = False
    max_entry_position_adjustment = 3            # up to 3 safety orders after the initial fill
    DCA_BASE_DEV = 0.045                          # 1st safety order triggers ~ -4.5% (pre vol-scale)
    DCA_DEV_FACTOR = 1.6                          # price spacing widens exponentially: 1, 1.6, 2.56x
    DCA_SIZE_FACTOR = 1.45                         # stake grows exponentially: 1, 1.45, 2.10x
    DCA_ATR_REF = 0.03                             # 4h atr_pct baseline; wider spacing when vol > ref

    STALE_EXIT_DAYS = 24                           # free capital from positions going nowhere

    # protections: avoid re-arming the same 4h setup every hour, and back off after stop runs
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 6},
        {"method": "StoplossGuard", "lookback_period_candles": 72, "trade_limit": 4,
         "stop_duration_candles": 24, "only_per_pair": False},
        {"method": "MaxDrawdown", "lookback_period_candles": 288, "trade_limit": 10,
         "stop_duration_candles": 48, "max_allowed_drawdown": 0.20},
    ]

    plot_config = {
        "main_plot": {
            "kelt_up_2h": {"color": "#d18b2c"},
            "ema20": {"color": "#5e8eff"},
        },
        "subplots": {
            "regime (4h ER)": {"er_2h": {"color": "purple"}},
            "filters": {
                "kelt_bo_2h": {"color": "green", "type": "bar"},
                "btc_up_2h": {"color": "teal", "type": "bar"},
            },
        },
    }

    @property
    def regime_pair(self) -> str:
        """BTC quoted in whatever we stake (BTC/USDT in backtest, BTC/EUR live)."""
        return f"BTC/{self.config['stake_currency']}"

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        info = [(p, self.inf_tf) for p in pairs]
        if (self.regime_pair, self.inf_tf) not in info:
            info.append((self.regime_pair, self.inf_tf))
        return info

    # --- 4h structural indicators (computed on the informative dataframe) -------------------
    def _indicators_2h(self, inf: DataFrame) -> DataFrame:
        inf["atr"] = ta.ATR(inf, timeperiod=14)
        inf["atr_pct"] = inf["atr"] / inf["close"]
        inf["ema20"] = ta.EMA(inf, timeperiod=20)
        inf["ema50"] = ta.EMA(inf, timeperiod=50)
        inf["er"] = kaufman_er(inf["close"], 10)
        inf["regime_trend"] = (inf["er"] > 0.45).astype(int)
        inf["kelt_up"] = inf["ema20"] + 2.0 * inf["atr"]
        inf["atr_expand"] = (inf["atr"] > inf["atr"].rolling(20).mean()).astype(int)
        # z-score of price vs rolling mean — used by the DCA dip logic, not as an entry
        m = inf["close"].rolling(50).mean()
        sd = inf["close"].rolling(50).std()
        inf["zscore"] = (inf["close"] - m) / sd.replace(0, np.nan)
        # CORE breakout: close clears the upper Keltner band while ATR is expanding, in trend
        inf["kelt_bo"] = (
            (inf["close"] > inf["kelt_up"]) & (inf["atr_expand"] == 1) & (inf["regime_trend"] == 1)
        ).astype(int)
        return inf

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # base 1h: atr_pct is required by the slippage mixin; ema20 is the fine entry trigger
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)

        # this pair's 4h structure
        inf = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.inf_tf)
        inf = self._indicators_2h(inf)
        dataframe = merge_informative_pair(dataframe, inf, self.timeframe, self.inf_tf, ffill=True)

        # BTC 4h regime filter (pass only the flags to avoid *_2h column collisions)
        btc = self.dp.get_pair_dataframe(pair=self.regime_pair, timeframe=self.inf_tf)
        btc["ema50"] = ta.EMA(btc, timeperiod=50)
        btc["btc_up"] = (btc["close"] > btc["ema50"]).astype(int)
        # stricter macro gate: BTC above a *rising* 4h ema50 (used by refinement variants to try
        # to avoid the chop/whipsaw years). Rising = ema50 higher than 6 bars (1 day) ago.
        btc["btc_up_strict"] = (
            (btc["close"] > btc["ema50"]) & (btc["ema50"] > btc["ema50"].shift(6))
        ).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc[["date", "btc_up", "btc_up_strict"]],
            self.timeframe, self.inf_tf, ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Phase-3 RESULT (iter-2): gating on the stricter macro filter (BTC above a *rising* 4h
        # ema50) weakly dominates the plain btc_up gate — better full return AND lower drawdown —
        # by skipping breakouts while BTC's macro trend is flat/down (the chop/whipsaw losses).
        dataframe.loc[
            (
                (dataframe["kelt_bo_2h"] == 1) &          # 4h volatility-expansion breakout, in trend
                (dataframe["btc_up_strict_2h"] == 1) &    # BTC above a RISING 4h ema50 (macro gate)
                (dataframe["close"] > dataframe["ema20"]) &   # 1h momentum confirm (entry timing)
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "kelt_bo_macro")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Phase-3 RESULT (iter-4/5): the ema50-break signal exited trends far too early (it lags a
        # 4h ema50 cross) and was the single biggest drag. Removed; the exit is now owned by the
        # ATR chandelier (custom_stoploss) + ROI + the -11% hard stop + the stale-exit timer.
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        """ATR chandelier: trail the stop CHAND_N * ATR(4h) below the highest price reached since
        entry. Volatility-adaptive (wide in volatile trends so it rides them) yet it protects the
        modest peaks the old +14%-armed trailing left exposed. freqtrade only ratchets a custom
        stop upward, so as max_rate rises the floor rises with it and never loosens; below the
        first meaningful peak the static -0.11 stop governs."""
        if not trade.max_rate:
            return None
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or not len(df):
            return None
        atr = df.iloc[-1].get("atr_2h")
        if atr is None or atr != atr or atr <= 0:        # missing / NaN guard
            return None
        chandelier_price = trade.max_rate - self.CHAND_N * float(atr)
        return stoploss_from_absolute(chandelier_price, current_rate,
                                      is_short=trade.is_short, leverage=trade.leverage)

    # --- helper: latest merged 4h fields off the analyzed dataframe -------------------------
    def _last_2h(self, pair: str):
        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if df is not None and len(df):
                return df.iloc[-1]
        except Exception:
            pass
        return None

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        # free capital from positions that have gone nowhere for too long (floating-loss bottleneck)
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        now = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        if (now - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"
        return None

    # --- non-linear, volatility-scaled DCA --------------------------------------------------
    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float,
                              current_profit: float, min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:
        """
        Add to a losing position ONLY when the data says dips are buyable: still in a 4h trend
        regime with BTC up. Each successive safety order is spaced exponentially FURTHER away
        (DCA_DEV_FACTOR) and is exponentially LARGER (DCA_SIZE_FACTOR), and the trigger distance
        widens with 4h volatility (DCA_ATR_REF) so we don't average down into a fast knife.
        """
        count = trade.nr_of_successful_entries           # 1 after the initial fill
        if count < 1 or count > self.max_entry_position_adjustment:
            return None

        last = self._last_2h(trade.pair)
        if last is None:
            return None
        # dips are only buyable inside an uptrend (discovery: range dips are -2.9% net)
        if int(last.get("regime_trend_2h", 0)) != 1 or int(last.get("btc_up_2h", 0)) != 1:
            return None

        # volatility-scaled, exponentially-widening trigger distance for this safety order
        atr_pct = float(last.get("atr_pct_2h", self.DCA_ATR_REF) or self.DCA_ATR_REF)
        vol_scale = max(atr_pct / self.DCA_ATR_REF, 1.0)
        trigger = self.DCA_BASE_DEV * vol_scale * (self.DCA_DEV_FACTOR ** (count - 1))
        if current_profit > -trigger:
            return None

        # exponentially increasing stake, anchored to the initial order's stake
        try:
            first_stake = trade.orders[0].stake_amount or trade.stake_amount
        except Exception:
            first_stake = trade.stake_amount
        add = first_stake * (self.DCA_SIZE_FACTOR ** (count - 1))

        if min_stake is not None:
            add = max(add, min_stake)
        add = min(add, max_stake)
        if add <= 0:
            return None
        return add
