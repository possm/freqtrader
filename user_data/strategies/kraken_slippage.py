"""
kraken_slippage.py — Phase 1.2 liquidity & slippage mixin.

WHY THIS EXISTS
---------------
We discover/backtest alpha on *Binance* OHLCV (deep history, thick books, clean prints)
but we *trade on Kraken*, whose EUR books are thinner: wider spreads, more slippage on
market orders, and real market impact on small-cap alts. A strategy that only looks good
on frictionless Binance fills can quietly die on Kraken. This mixin injects a strict,
reproducible mathematical penalty onto backtest fills so the equity curve we validate
already "pays the Kraken tax".

HOW IT WORKS
------------
Freqtrade calls `custom_entry_price` / `custom_exit_price` to decide the LIMIT price an
order is placed at, in backtest *and* live. We push that price ADVERSELY:

    entry (buy):  fill higher  -> proposed_rate * (1 + adverse)
    exit  (sell): fill lower   -> proposed_rate * (1 - adverse)

`adverse` (a one-way fraction) is the sum of three components, each grounded in a real
microstructure effect:

  1. SPREAD     half-spread from a per-pair map (KRAKEN_SPREAD_BPS), reflecting how tight
                each Kraken EUR book actually is (BTC ~1.5bps ... small-caps ~12bps).
  2. VOLATILITY SLIP_ATR_COEF * atr_pct * rand,  where atr_pct is the candle's ATR/close and
                `rand` is a *deterministic* draw in [SLIP_RAND_LO, SLIP_RAND_HI]. Slippage is
                worse when the market is moving fast — and varies trade-to-trade ("random
                but realistic") without breaking backtest reproducibility.
  3. IMPACT     SLIP_IMPACT_COEF * sqrt(participation), the classic square-root market-impact
                law, where participation = our stake / the bar's quote volume. Thinner bars
                (lower volume) cost more — i.e. slippage "scaled by the volume of the asset".

The total is capped at SLIP_MAX_FRAC for safety. Everything is a tunable class attribute.

IMPORTANT — only bites in BACKTEST/HYPEROPT
-------------------------------------------
In live/dry-run we must NOT distort our own order prices (we'd place bad limits and the
Phase-4 audit could no longer compare real fills against the model). So the penalty is gated
to RunMode.BACKTEST / HYPEROPT. In every other runmode these hooks return the proposed rate
unchanged, letting Freqtrade's normal order-book pricing take over.

REQUIREMENTS ON THE BACKTEST CONFIG
-----------------------------------
custom_*_price only takes effect for LIMIT orders, so the *backtest* config must use:
    "order_types": { "entry": "limit", "exit": "limit", ... }
The live Kraken config can stay on market orders; the limit-price offset here is precisely
how we emulate market-order drag inside the backtester. The fee in the backtest config
should also be set to a Kraken-realistic taker level (commission floor) — this mixin models
spread + slippage + impact ON TOP of that commission.

The spread map is module-level so the Phase-4 live audit script can import the exact same
numbers and flag divergence against one source of truth.
"""

from __future__ import annotations

import hashlib
import math
import os
from datetime import datetime
from typing import Optional

from freqtrade.enums import RunMode


# --- single source of truth: per-pair one-way (half) spread on Kraken EUR books, in bps -----
# Tiered by real book depth: majors are razor-tight, small-cap alts are wide. Keyed by BASE
# asset so it works regardless of EUR/USDT/USD quoting. Tune from the Phase-4 audit log.
KRAKEN_SPREAD_BPS: dict[str, float] = {
    "BTC": 1.5, "ETH": 2.0, "SOL": 3.0,
    "LINK": 4.0, "ADA": 4.0, "AAVE": 5.0, "NEAR": 5.0,
    "ARB": 6.0, "OP": 6.0, "POL": 6.0, "SUI": 7.0, "INJ": 7.0, "RENDER": 7.0,
    "FET": 8.0, "TIA": 8.0, "HBAR": 8.0,
    "STX": 10.0, "KAS": 12.0,
}
KRAKEN_SPREAD_DEFAULT_BPS: float = 12.0


def kraken_half_spread_frac(pair: str) -> float:
    """One-way spread cost (as a fraction, not bps) for a pair's base asset."""
    base = pair.split("/")[0].upper()
    return KRAKEN_SPREAD_BPS.get(base, KRAKEN_SPREAD_DEFAULT_BPS) / 10_000.0


class KrakenSlippageMixin:
    """
    Mix in BEFORE IStrategy:  `class MyStrat(KrakenSlippageMixin, IStrategy): ...`

    Fail-safe by construction: any error while computing the penalty returns the unmodified
    proposed_rate, so a data hiccup can never crash a backtest — it just means "no extra drag
    for that one fill".
    """

    # --- tunables (all one-way unless noted) ---------------------------------------------
    SLIP_ATR_COEF: float = 0.08          # volatility slippage = COEF * atr_pct * rand
    SLIP_IMPACT_COEF: float = 0.05       # impact = COEF * sqrt(participation)
    SLIP_RAND_LO: float = 0.5            # deterministic "random" multiplier range on the
    SLIP_RAND_HI: float = 1.5            #   volatility term (reproducible per pair+timestamp)
    SLIP_PARTICIPATION_CAP: float = 0.02  # cap our share of a bar's quote volume at 2%
    SLIP_MAX_FRAC: float = 0.015         # hard cap on total one-way adverse fraction (1.5%)
    SLIP_DEFAULT_ATR_PCT: float = 0.01   # fallback when ATR can't be read from the candle

    # Apply the penalty only while simulating. Flip to add dry-run if you want a pessimistic
    # paper-trade, but then the Phase-4 audit compares fills against distorted prices.
    SLIP_RUNMODES = (RunMode.BACKTEST, RunMode.HYPEROPT)

    # ------------------------------------------------------------------------------------
    def _slippage_active(self) -> bool:
        # A/B switch for verifying the model's impact: KRAKEN_SLIP_OFF=1 disables the penalty.
        if os.environ.get("KRAKEN_SLIP_OFF") == "1":
            return False
        try:
            return self.dp is not None and self.dp.runmode in self.SLIP_RUNMODES
        except Exception:
            return False

    def _unit_rng(self, pair: str, when: datetime) -> float:
        """Deterministic pseudo-random draw in [0,1) keyed by pair+timestamp (reproducible)."""
        key = f"{pair}|{when.isoformat()}".encode()
        digest = hashlib.blake2b(key, digest_size=8).digest()
        return (int.from_bytes(digest, "big") % 1_000_000) / 1_000_000.0

    def _nominal_stake(self) -> float:
        """Best-effort representative stake for the impact term."""
        stake = self.config.get("stake_amount", 0)
        if not isinstance(stake, (int, float)) or stake <= 0:  # 'unlimited' or unset
            wallet = float(self.config.get("dry_run_wallet", 1000) or 1000)
            slots = max(int(self.config.get("max_open_trades", 1) or 1), 1)
            return wallet / slots
        return float(stake)

    def _candle_vol_and_atr(self, pair: str) -> tuple[float, float]:
        """Return (atr_pct, bar_quote_volume) from the latest analyzed candle, with fallbacks."""
        atr_pct = self.SLIP_DEFAULT_ATR_PCT
        quote_vol = 0.0
        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if df is not None and len(df):
                c = df.iloc[-1]
                close = float(c.get("close", 0) or 0)
                if close > 0:
                    if "atr_pct" in c and c["atr_pct"] == c["atr_pct"]:        # not NaN
                        atr_pct = float(c["atr_pct"])
                    elif "atr" in c and c["atr"] == c["atr"]:
                        atr_pct = float(c["atr"]) / close
                    else:                                                       # high-low proxy
                        hi, lo = float(c.get("high", close)), float(c.get("low", close))
                        atr_pct = max((hi - lo) / close, 0.0)
                    quote_vol = float(c.get("volume", 0) or 0) * close
        except Exception:
            pass
        # keep atr_pct sane (0.05% .. 25%)
        atr_pct = min(max(atr_pct, 0.0005), 0.25)
        return atr_pct, quote_vol

    def kraken_adverse_fraction(self, pair: str, when: datetime) -> float:
        """The one-way adverse price fraction = spread + volatility-slip + market-impact."""
        spread = kraken_half_spread_frac(pair)

        atr_pct, quote_vol = self._candle_vol_and_atr(pair)
        rand = self.SLIP_RAND_LO + self._unit_rng(pair, when) * (self.SLIP_RAND_HI - self.SLIP_RAND_LO)
        vol_slip = self.SLIP_ATR_COEF * atr_pct * rand

        impact = 0.0
        if quote_vol > 0:
            participation = min(self._nominal_stake() / quote_vol, self.SLIP_PARTICIPATION_CAP)
            impact = self.SLIP_IMPACT_COEF * math.sqrt(participation)

        return min(spread + vol_slip + impact, self.SLIP_MAX_FRAC)

    # --- Freqtrade hooks ------------------------------------------------------------------
    def custom_entry_price(self, pair: str, trade, current_time: datetime,
                           proposed_rate: float, entry_tag: Optional[str] = None,
                           side: str = "long", **kwargs) -> float:
        if not self._slippage_active():
            return proposed_rate
        try:
            adv = self.kraken_adverse_fraction(pair, current_time)
            # buy fills worse = higher; a short entry (sell) fills worse = lower
            return proposed_rate * (1 - adv) if side == "short" else proposed_rate * (1 + adv)
        except Exception:
            return proposed_rate

    def custom_exit_price(self, pair: str, trade, current_time: datetime,
                          proposed_rate: float, current_profit: float = 0.0,
                          exit_tag: Optional[str] = None, **kwargs) -> float:
        if not self._slippage_active():
            return proposed_rate
        try:
            adv = self.kraken_adverse_fraction(pair, current_time)
            is_short = getattr(trade, "is_short", False)
            # closing a long = sell = fill lower; closing a short = buy = fill higher
            return proposed_rate * (1 + adv) if is_short else proposed_rate * (1 - adv)
        except Exception:
            return proposed_rate
