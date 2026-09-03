"""
WolfQuantEdge_variants.py — Phase 3 refinement, iteration 3: EXIT TIMING.

Prompted by the live dry-run (8082): the first 4 trades all ran green (+3% to +12.6% MFE) then
round-tripped to losses, giving back ~17pp on average. Root cause: trailing only ARMS at +14%
(trailing_stop_positive_offset), so modest peaks were never protected, and the break_ema50_4h
exit lags badly. These variants test EARLIER/ TIGHTER profit protection — but the verdict is the
5-year IS/OOS backtest, not 4 live trades (wide trailing won historically by riding big trends).

  WQE_Trail8 : arm trailing at +8%, trail 5% below peak.
  WQE_Trail5 : arm at +5%, trail 4%.
  WQE_Trail3 : arm at +3%, trail 2% (tightest native ratchet — protects small peaks, may cut trends).
  WQE_Ratchet: custom tiered profit-lock keyed on PEAK (max_rate), so the floor never loosens:
               peak>=3% -> breakeven, >=6% -> +2%, >=12% -> +6%; default -0.11 until first +3%.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open

from WolfQuantEdge import WolfQuantEdge


class WQE_Trail8(WolfQuantEdge):
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.08


class WQE_Trail5(WolfQuantEdge):
    trailing_stop_positive = 0.04
    trailing_stop_positive_offset = 0.05


class WQE_Trail3(WolfQuantEdge):
    # offset MUST be strictly > positive (freqtrade rejects equal): arm at +3%, trail 2% below peak
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03


class WQE_Ratchet(WolfQuantEdge):
    # Native trailing stays as a backstop; the custom ratchet locks a profit FLOOR based on the
    # peak reached, so a green trade can never round-trip into a loss once it has shown +3%.
    use_custom_stoploss = True

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        if not trade.open_rate or not trade.max_rate:
            return None
        peak = (trade.max_rate - trade.open_rate) / trade.open_rate
        if peak >= 0.12:
            floor = 0.06
        elif peak >= 0.06:
            floor = 0.02
        elif peak >= 0.03:
            floor = 0.0
        else:
            return None  # not yet +3%: fall back to the default -0.11 stop
        return stoploss_from_open(floor, current_profit,
                                  is_short=trade.is_short, leverage=trade.leverage)
