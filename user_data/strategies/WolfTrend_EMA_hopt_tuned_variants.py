"""
WolfTrend_EMA_hopt_tuned_variants.py — profit-taking fix candidates for the LIVE 8080 bot.

Diagnosis (see /root/freqtrade-wolf/user_data/tradesv3_hopt_live.sqlite): the base strategy has
minimal_roi = {"0": 100.0}, trailing_stop = False, use_custom_stoploss = False, so its ONLY
exit paths are the -2.4% hard stop and the lagging 4h ema-cross-down. Result: 0 wins in 11
trades, all at ~-3.2%, while MFEs routinely ran +2% to +10%+ (HBAR peaked at +10.01%). The
existing _roi20/30/40/_ofs variants would not have helped either — their thresholds (20-40%)
are far above the actual MFE distribution.

These 4 candidates each inject a LOW-THRESHOLD profit-taker calibrated to the observed MFE
zone. Backtested across 4h windows vs the tuned base. The ema-cross-down exit signal is kept
in all of them as a legitimate trend-break backstop.

  WTE_roi_tiered : take 8% at any time, decay to 5% after 4h, 3% after 24h
  WTE_trail_low  : arm trailing at +4% peak, trail 2% below (native freqtrade trailing)
  WTE_chand5     : ATR chandelier via custom_stoploss — 5*ATR(14) below the run's peak
                   (volatility-adaptive, the mechanism that fixed WolfQuantEdge)
  WTE_combo      : chandelier + tiered ROI together
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import talib.abstract as ta

from freqtrade.persistence import Trade
from freqtrade.strategy import merge_informative_pair, stoploss_from_absolute

from WolfTrend_EMA_hopt_tuned import WolfTrend_EMA_hopt_tuned


class WTE_roi_tiered(WolfTrend_EMA_hopt_tuned):
    minimal_roi = {"0": 0.08, "240": 0.05, "1440": 0.03}


class WTE_trail_low(WolfTrend_EMA_hopt_tuned):
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True


class WTE_chand5(WolfTrend_EMA_hopt_tuned):
    use_custom_stoploss = True
    CHAND_N = 5.0

    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        if not trade.max_rate:
            return None
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or not len(df):
            return None
        atr = df.iloc[-1].get("atr")
        if atr is None or atr != atr or atr <= 0:
            return None
        chandelier_price = trade.max_rate - self.CHAND_N * float(atr)
        return stoploss_from_absolute(chandelier_price, current_rate,
                                      is_short=trade.is_short, leverage=trade.leverage)


class WTE_combo(WTE_chand5):
    minimal_roi = {"0": 0.08, "240": 0.05, "1440": 0.03}


# --- iteration 2: "cut only the highs" -----------------------------------------------------
# The earlier variants clipped too eagerly (+4-8%) and killed the whole edge because they cut
# +50%+ trend runners down to +5%. These variants only bite on FAT-TAIL winners, leaving the
# body of the distribution alone. Idea from the user: give up some 2024 upside to recoup some
# 2022 / 2025 / 2026 loss. Empirical question — depends on how much of profit is truly outlier.


class WTE_roi30(WolfTrend_EMA_hopt_tuned):
    """Cap any single trade at +30% profit (higher than any typical live MFE)."""
    minimal_roi = {"0": 0.30}


class WTE_roi50(WolfTrend_EMA_hopt_tuned):
    """Cap only the mega-runners at +50%."""
    minimal_roi = {"0": 0.50}


class WTE_chand10(WTE_chand5):
    """Wide chandelier: 10*ATR(14) below the peak — ~15% below peak at typical 4h ATR."""
    CHAND_N = 10.0


class WTE_arm15(WolfTrend_EMA_hopt_tuned):
    """Late-arming trailing: only kicks in once a trade has already run to +15%, then trails 5%."""
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.15
    trailing_only_offset_is_reached = True


# --- iteration 3: ENTRY-SIDE REGIME FILTERS ------------------------------------------------
# Cutting the exit failed because good-year & bad-year winners come from the same MFE
# distribution. The structurally-safe way to reduce bad-year trades is to STOP ENTERING them
# in the first place, gated on macro-trend or higher trend-strength conditions.


class WTE_btc200(WolfTrend_EMA_hopt_tuned):
    """Only enter when BTC is above its own 4h EMA200 (macro-uptrend gate)."""

    def informative_pairs(self):
        return [(f"BTC/{self.config['stake_currency']}", "4h")]

    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        btc = self.dp.get_pair_dataframe(
            pair=f"BTC/{self.config['stake_currency']}", timeframe="4h"
        )
        btc["btc_ema200"] = ta.EMA(btc, timeperiod=200)
        btc["btc_uptrend"] = (btc["close"] > btc["btc_ema200"]).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc[["date", "btc_uptrend"]], self.timeframe, "4h", ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe.loc[dataframe["btc_uptrend_4h"] != 1, ["enter_long", "enter_tag"]] = (0, None)
        return dataframe


class WTE_adx25(WolfTrend_EMA_hopt_tuned):
    """Raise ADX threshold from 15 to 25 — only trade genuinely-trending markets."""
    ADX_MIN = 25


class WTE_adx35(WolfTrend_EMA_hopt_tuned):
    """Even more selective: ADX >= 35."""
    ADX_MIN = 35


class WTE_btc_adx(WTE_btc200):
    """Both gates: BTC uptrend AND ADX>=25 (most selective — expect fewest trades)."""
    ADX_MIN = 25

class WTE_own200(WolfTrend_EMA_hopt_tuned):
    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe['own_ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe.loc[dataframe['close'] < dataframe['own_ema200'], ['enter_long', 'enter_tag']] = (0, None)
        return dataframe

class WTE_btc200_combo(WTE_btc200):
    use_custom_stoploss = True
    CHAND_N = 5.0
    minimal_roi = {"0": 0.20, "1440": 0.10, "2880": 0.05, "5760": 0.03}
    
    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        if not trade.max_rate:
            return None
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or not len(df):
            return None
        atr = df.iloc[-1].get("atr")
        if atr is None or atr != atr or atr <= 0:
            return None
        chandelier_price = trade.max_rate - self.CHAND_N * float(atr)
        from freqtrade.strategy import stoploss_from_absolute
        return stoploss_from_absolute(chandelier_price, current_rate, is_short=trade.is_short, leverage=trade.leverage)


class WTE_both200(WTE_btc200):
    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe['own_ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe.loc[dataframe['close'] < dataframe['own_ema200'], ['enter_long', 'enter_tag']] = (0, None)
        return dataframe
