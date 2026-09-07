"""
WolfQuantEdge_variants.py — Phase 3 refinement, iteration 4: ATR CHANDELIER exit.

Iteration 3 proved that tightening the exit with fixed-% trailing is catastrophic (-51% to -93%):
this edge lives in a few multi-day runners, and clipping them with a fixed stop while ~55% of
trades still hit the hard stop is fatal. The ONE untested mechanism is a volatility-adaptive
CHANDELIER: trail the stop N*ATR(4h) below the highest price reached since entry. Unlike a fixed
%, it widens in volatile trends (so it can ride them) yet still protects sub-+14% peaks that the
base's +14%-armed trailing leaves totally exposed (the live-dry-run round-trip-to-loss problem).

To isolate the chandelier we DISABLE native trailing and the ema50 break signal, leaving:
chandelier custom_stoploss + loose ROI + hard -0.11 stop + stale exit. freqtrade ratchets a
custom stop upward only (never loosens), so the chandelier rises with max_rate as designed.

  WQE_Chand3 / 4 / 5 / 6 : trail 3 / 4 / 5 / 6 * ATR(4h) below the peak.

Verdict is the 5-year IS/OOS grid vs the base WolfQuantEdge (+16.6% / PF 1.04 / 24.6% DD), NOT
the handful of live trades that prompted this.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute

from WolfQuantEdge import WolfQuantEdge


class _WQE_Chandelier(WolfQuantEdge):
    """Shared chandelier logic; concrete variants set CHAND_N. Not run directly."""
    trailing_stop = False          # the chandelier IS the trail
    use_custom_stoploss = True
    CHAND_N = 3.0

    def populate_exit_trend(self, dataframe, metadata):
        # disable the ema50 break signal so the chandelier (and ROI/stop/stale) own the exit
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        if not trade.max_rate:
            return None
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or not len(df):
            return None
        atr = df.iloc[-1].get("atr_4h")
        if atr is None or atr != atr or atr <= 0:   # missing / NaN guard
            return None
        chandelier_price = trade.max_rate - self.CHAND_N * float(atr)
        return stoploss_from_absolute(chandelier_price, current_rate,
                                      is_short=trade.is_short, leverage=trade.leverage)


class WQE_Chand3(_WQE_Chandelier):
    CHAND_N = 3.0


class WQE_Chand4(_WQE_Chandelier):
    CHAND_N = 4.0


class WQE_Chand5(_WQE_Chandelier):
    CHAND_N = 5.0


class WQE_Chand6(_WQE_Chandelier):
    CHAND_N = 6.0


class WQE_Chand8(_WQE_Chandelier):
    CHAND_N = 8.0


class WQE_Chand10(_WQE_Chandelier):
    CHAND_N = 10.0


class WQE_NoTrail(WolfQuantEdge):
    """Control: no trailing, no chandelier, no ema50-break — only loose ROI + hard -0.11 stop +
    stale. If this matches Chand6, the win was just removing the laggy ema50 exit, not the
    chandelier; if Chand6 beats it, the ATR trail is doing real work."""
    trailing_stop = False
    use_custom_stoploss = False

    def populate_exit_trend(self, dataframe, metadata):
        return dataframe
