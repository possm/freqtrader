"""
tests/test_wolfbreakout_hvrspb.py — Rigorous Unit Test Suite for WolfBreakout_HVRSPB
===================================================================================
Validates:
1. Parkinson (1980) Continuous Volatility Variance & PVR Ratio:
   - Closed-form hand-calculated verification on exact known values
   - Zero-division safety on flat candles (H == L)
   - Sanitization of zero/negative low prices and inverted candles
   - Volatility expansion detection (quiet consolidation -> surge)
2. Cross-Asset Relative Strength (RS vs BTC):
   - 24h rolling return excess calculation ($RS = R_{asset} - R_{BTC}$)
   - Synthetic BTC informative pair merge logic
   - Benchmark-neutral fallback when BTC data is missing or empty
3. Dual-Band Donchian & Keltner Channels:
   - Strict .shift(1) lookahead bias prevention on Donchian
   - Donchian ordering (high >= mid >= low)
   - Keltner channel properties and ATR calculation
4. Entry Signal Generation:
   - Full alignment of all breakout conditions triggers enter_long == 1
   - Combinatorial suppression (individual condition failure tests)
5. Exit Signal Generation & Dynamic Risk:
   - Donchian midline trend invalidation in populate_exit_trend
   - custom_exit fast invalidation after 4 candles
   - custom_exit stale trade reclaimer after 14 days
   - custom_stoploss two-tier asymmetric trailing stop (+3.5% BE lock, +8% runner)
6. Edge Cases & Data Hygiene:
   - Empty dataframe, None input, missing columns
   - Fifty consecutive flat candles (zero variance)
   - Startup warmup NaNs do not trigger premature signals
7. Freqtrade API Conformance & Maker Order Types:
   - INTERFACE_VERSION == 3, timeframe == '1h'
   - informative_pairs returns [('BTC/EUR', '1h'), ('BTC/USDT', '1h')]
   - Maker fee limit order types
   - Hyperopt parameter definitions across buy, sell, stoploss, and trailing spaces
"""
from __future__ import annotations

import math
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

# Add strategy directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRAT_DIR = PROJECT_ROOT / "user_data" / "strategies"
if str(STRAT_DIR) not in sys.path:
    sys.path.insert(0, str(STRAT_DIR))

from WolfBreakout_HVRSPB import WolfBreakout_HVRSPB


# =============================================================================
# SYNTHETIC TEST FIXTURES & MOCKS
# =============================================================================

class MockDataProvider:
    """Mock Freqtrade DataProvider for isolating informative pairs and analyzed dataframes."""

    def __init__(self, btc_df: pd.DataFrame | None = None, analyzed_df: pd.DataFrame | None = None):
        self.btc_df = btc_df
        self.analyzed_df = analyzed_df
        self.runmode = "backtest"

    def get_pair_dataframe(self, pair: str, timeframe: str) -> pd.DataFrame:
        if "BTC" in pair and self.btc_df is not None:
            return self.btc_df.copy()
        return pd.DataFrame()

    def get_analyzed_dataframe(self, pair: str, timeframe: str) -> tuple[pd.DataFrame, datetime]:
        if self.analyzed_df is not None:
            return self.analyzed_df.copy(), datetime.now(timezone.utc)
        return pd.DataFrame(), datetime.now(timezone.utc)

    def current_whitelist(self) -> list[str]:
        return ["FET/EUR", "NEAR/EUR", "BTC/EUR", "BTC/USDT"]


def generate_synthetic_ohlcv(
    n_bars: int = 260,
    base_price: float = 100.0,
    volatility: float = 0.015,
    seed: int = 42,
    start_date: str = "2026-01-01 00:00:00"
) -> pd.DataFrame:
    """
    Generates deterministic, mathematically consistent OHLCV data.
    Guarantees High >= max(Open, Close) and Low <= min(Open, Close).
    """
    rng = np.random.default_rng(seed)
    dt_index = pd.date_range(start=start_date, periods=n_bars, freq="1h", tz="UTC")

    returns = rng.normal(loc=0.0005, scale=volatility, size=n_bars)
    prices = base_price * np.exp(np.cumsum(returns))

    opens = prices * (1.0 + rng.normal(0, 0.002, size=n_bars))
    closes = prices * (1.0 + rng.normal(0, 0.002, size=n_bars))
    highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0, 0.005, size=n_bars)))
    lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0, 0.005, size=n_bars)))
    volumes = rng.uniform(500.0, 5000.0, size=n_bars)

    df = pd.DataFrame({
        "date": dt_index,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })
    return df


def generate_synthetic_btc(
    n_bars: int = 260,
    base_price: float = 65000.0,
    return_24h_pct: float = 0.02,
    is_bullish: bool = True,
    start_date: str = "2026-01-01 00:00:00"
) -> pd.DataFrame:
    """Generates synthetic BTC informative pair data with deterministic 24h return."""
    dt_index = pd.date_range(start=start_date, periods=n_bars, freq="1h", tz="UTC")
    # Linear price path so 24h return is predictable
    hourly_drift = (1.0 + return_24h_pct) ** (1.0 / 24.0) - 1.0
    prices = base_price * ((1.0 + hourly_drift) ** np.arange(n_bars))

    highs = prices * 1.005
    lows = prices * 0.995
    volumes = np.full(n_bars, 1000.0)

    if not is_bullish:
        # Downward path
        prices = base_price * (0.999 ** np.arange(n_bars))
        highs = prices * 1.002
        lows = prices * 0.998

    df = pd.DataFrame({
        "date": dt_index,
        "open": prices,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes,
    })
    return df


class MockTrade:
    """Mock Freqtrade Trade object for testing custom_stoploss and custom_exit."""

    def __init__(
        self,
        pair: str = "FET/EUR",
        open_rate: float = 100.0,
        open_date_utc: datetime | None = None,
        is_short: bool = False,
        leverage: float = 1.0,
        max_rate: float = 100.0,
    ):
        self.pair = pair
        self.open_rate = open_rate
        self.open_date_utc = open_date_utc or datetime.now(timezone.utc) - timedelta(hours=5)
        self.is_short = is_short
        self.leverage = leverage
        self.max_rate = max_rate
        self.orders = []
        self.stake_amount = 100.0
        self.nr_of_successful_buys = 1
        self.nr_of_successful_entries = 1


# =============================================================================
# 1. PARKINSON VOLATILITY RATIO (PVR) TESTS
# =============================================================================

class TestParkinsonVolatility(unittest.TestCase):
    """Verifies Parkinson (1980) continuous range-based variance and PVR."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_parkinson_variance_hand_calculated(self):
        """
        Closed-form verification:
        For H = 110, L = 100:
          ratio = 1.10
          ln(1.10) = 0.0953101798
          (ln(1.10))^2 = 0.00908403037
          4 * ln(2) = 2.77258872224
          expected_variance = 0.00908403037 / 2.77258872224 = 0.00327637138
        """
        high = 110.0
        low = 100.0
        expected_var = (math.log(high / low) ** 2) / (4.0 * math.log(2.0))

        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=25, freq="1h", tz="UTC"),
            "open": np.full(25, 100.0),
            "high": np.full(25, high),
            "low": np.full(25, low),
            "close": np.full(25, 105.0),
            "volume": np.full(25, 1000.0),
        })

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        calculated_vol = analyzed["parkinson_20"].iloc[-1]
        self.assertAlmostEqual(calculated_vol, math.sqrt(expected_var), places=6)

    def test_parkinson_flat_candle_zero_variance(self):
        """A flat candle (H == L) must yield variance = 0.0 without ZeroDivisionError."""
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=30, freq="1h", tz="UTC"),
            "open": np.full(30, 50.0),
            "high": np.full(30, 50.0),
            "low": np.full(30, 50.0),
            "close": np.full(30, 50.0),
            "volume": np.full(30, 100.0),
        })
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        # After 20 bars, parkinson_20 should be 0.0
        self.assertEqual(analyzed["parkinson_20"].iloc[-1], 0.0)
        # PVR should evaluate cleanly to 0.0 without crash
        self.assertFalse(np.isnan(analyzed["pvr"].iloc[-1]))
        self.assertEqual(analyzed["pvr"].iloc[-1], 0.0)

    def test_parkinson_zero_or_negative_low_sanitization(self):
        """Glitch data with low <= 0 must be clipped safely without crash."""
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=25, freq="1h", tz="UTC"),
            "open": np.full(25, 10.0),
            "high": np.full(25, 12.0),
            "low": np.array([0.0] * 5 + [-5.0] * 5 + [10.0] * 15),
            "close": np.full(25, 11.0),
            "volume": np.full(25, 500.0),
        })
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        self.assertFalse(analyzed["parkinson_20"].isna().all())
        self.assertTrue(np.all(np.isfinite(analyzed["parkinson_20"].dropna())))

    def test_pvr_volatility_expansion_surge(self):
        """PVR must surge above 1.15 when 25 quiet bars are followed by 20 explosive bars."""
        n_quiet = 40
        n_explosive = 20
        total = n_quiet + n_explosive

        # Quiet period: 0.2% range
        quiet_high = np.full(n_quiet, 100.2)
        quiet_low = np.full(n_quiet, 100.0)

        # Explosive period: 5.0% range
        exp_high = np.full(n_explosive, 105.0)
        exp_low = np.full(n_explosive, 100.0)

        highs = np.concatenate([quiet_high, exp_high])
        lows = np.concatenate([quiet_low, exp_low])
        closes = (highs + lows) / 2.0

        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=total, freq="1h", tz="UTC"),
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(total, 1000.0),
        })

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        last_pvr = analyzed["pvr"].iloc[-1]
        self.assertGreater(last_pvr, 1.15, f"Expected PVR > 1.15 on expansion, got {last_pvr}")


# =============================================================================
# 2. RELATIVE STRENGTH (RS vs BTC) TESTS
# =============================================================================

class TestRelativeStrength(unittest.TestCase):
    """Verifies Cross-Asset Relative Strength calculation against BTC."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})

    def test_relative_strength_altcoin_outperforming(self):
        """
        When Altcoin 24h return is +10% and BTC 24h return is +2%,
        RS = 0.10 - 0.02 = +0.08 (exceeds default 0.025 threshold).
        """
        n_bars = 60
        # BTC: flat for first 36 bars at 60000, then rises to 61200 (+2% in last 24h)
        btc_closes = np.full(n_bars, 60000.0)
        btc_closes[36:] = 60000.0 * (1.0 + 0.02 * np.linspace(0, 1, 24))
        btc_df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": btc_closes,
            "high": btc_closes * 1.002,
            "low": btc_closes * 0.998,
            "close": btc_closes,
            "volume": np.full(n_bars, 1000.0),
        })

        # Altcoin: flat for first 36 bars at 100, then rises to 110 (+10% in last 24h)
        alt_closes = np.full(n_bars, 100.0)
        alt_closes[36:] = 100.0 * (1.0 + 0.10 * np.linspace(0, 1, 24))
        alt_df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": alt_closes,
            "high": alt_closes * 1.005,
            "low": alt_closes * 0.995,
            "close": alt_closes,
            "volume": np.full(n_bars, 2000.0),
        })

        self.strategy.dp = MockDataProvider(btc_df=btc_df)
        analyzed = self.strategy.populate_indicators(alt_df.copy(), {"pair": "FET/EUR"})

        last_rs = analyzed["rs_btc"].iloc[-1]
        expected_rs = 0.10 - 0.02  # 0.08
        self.assertAlmostEqual(last_rs, expected_rs, places=3)
        self.assertGreater(last_rs, self.strategy.rs_threshold.value)

    def test_relative_strength_altcoin_underperforming(self):
        """When Altcoin lags BTC, RS should be negative."""
        n_bars = 60
        btc_closes = np.full(n_bars, 60000.0)
        btc_closes[36:] = 60000.0 * (1.0 + 0.08 * np.linspace(0, 1, 24))  # +8% BTC
        btc_df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": btc_closes,
            "high": btc_closes * 1.001,
            "low": btc_closes * 0.999,
            "close": btc_closes,
            "volume": np.full(n_bars, 1000.0),
        })

        alt_closes = np.full(n_bars, 100.0)
        alt_closes[36:] = 100.0 * (1.0 + 0.01 * np.linspace(0, 1, 24))  # +1% Alt
        alt_df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": alt_closes,
            "high": alt_closes * 1.001,
            "low": alt_closes * 0.999,
            "close": alt_closes,
            "volume": np.full(n_bars, 1000.0),
        })

        self.strategy.dp = MockDataProvider(btc_df=btc_df)
        analyzed = self.strategy.populate_indicators(alt_df.copy(), {"pair": "FET/EUR"})

        last_rs = analyzed["rs_btc"].iloc[-1]
        self.assertLess(last_rs, 0.0)

    def test_relative_strength_missing_informative_pair_fallback(self):
        """When BTC informative pair is missing, fallback to benchmark-neutral (R_BTC = 0.0)."""
        df = generate_synthetic_ohlcv(n_bars=60)
        # Empty mock data provider (no BTC data)
        self.strategy.dp = MockDataProvider(btc_df=None)

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        # Should not raise exception
        self.assertIn("rs_btc", analyzed.columns)
        self.assertIn("btc_return_24h_clean", analyzed.columns)
        self.assertEqual(analyzed["btc_return_24h_clean"].iloc[-1], 0.0)
        # RS should equal asset return
        expected_rs = analyzed["asset_return_24h"].iloc[-1]
        self.assertAlmostEqual(analyzed["rs_btc"].iloc[-1], expected_rs, places=5)


# =============================================================================
# 3. DONCHIAN & KELTNER CHANNEL TESTS
# =============================================================================

class TestDonchianAndKeltnerChannels(unittest.TestCase):
    """Verifies lookahead bias prevention and channel envelope boundaries."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_donchian_shift1_strictly_prevents_lookahead(self):
        """
        Verify that changing the current candle's high does NOT change donchian_high
        for the current candle.
        """
        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed1 = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        original_donchian_high = analyzed1["donchian_high"].iloc[-1]

        # Mutate the last candle's high drastically
        df_mutated = df.copy()
        df_mutated.loc[df_mutated.index[-1], "high"] = 999999.0

        analyzed2 = self.strategy.populate_indicators(df_mutated.copy(), {"pair": "FET/EUR"})
        mutated_donchian_high = analyzed2["donchian_high"].iloc[-1]

        self.assertEqual(
            original_donchian_high,
            mutated_donchian_high,
            "Lookahead bias detected! donchian_high changed when current bar high was mutated."
        )

    def test_donchian_channel_ordering(self):
        """Verify donchian_high >= donchian_mid >= donchian_low and mid is exact midpoint."""
        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        valid = analyzed.dropna(subset=["donchian_high", "donchian_low", "donchian_mid"])

        self.assertTrue((valid["donchian_high"] >= valid["donchian_mid"]).all())
        self.assertTrue((valid["donchian_mid"] >= valid["donchian_low"]).all())
        expected_mid = (valid["donchian_high"] + valid["donchian_low"]) / 2.0
        assert_series_equal(valid["donchian_mid"], expected_mid, check_names=False)

    def test_keltner_channel_envelope_properties(self):
        """Verify Keltner Upper = EMA + mult * ATR and atr_pct is computed."""
        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        valid = analyzed.dropna(subset=["keltner_upper", "keltner_basis", "atr"])

        expected_upper = valid["keltner_basis"] + self.strategy.keltner_mult.value * valid["atr"]
        assert_series_equal(valid["keltner_upper"], expected_upper, check_names=False)
        self.assertTrue("atr_pct" in analyzed.columns)
        self.assertTrue((valid["atr_pct"] > 0).all())


# =============================================================================
# 4. ENTRY SIGNAL GENERATION TESTS
# =============================================================================

class TestEntrySignals(unittest.TestCase):
    """Verifies entry breakout signal triggers and combinatorial suppression."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def _create_aligned_breakout_df(self) -> pd.DataFrame:
        """Helper to create a DataFrame where candle -1 meets all 7 breakout criteria."""
        n_bars = 60
        df = generate_synthetic_ohlcv(n_bars=n_bars, base_price=100.0, volatility=0.005)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})

        # Force all indicators on candle -1 to strictly satisfy the entry rules
        analyzed.loc[analyzed.index[-1], "donchian_high"] = 100.0
        analyzed.loc[analyzed.index[-1], "keltner_upper"] = 101.0
        analyzed.loc[analyzed.index[-1], "close"] = 105.0  # Above both channels
        analyzed.loc[analyzed.index[-1], "pvr"] = 1.25     # > 1.15 threshold
        analyzed.loc[analyzed.index[-1], "rs_btc"] = 0.040 # > 0.025 threshold
        analyzed.loc[analyzed.index[-1], "volume_mean"] = 1000.0
        analyzed.loc[analyzed.index[-1], "volume"] = 1500.0 # > 1.2 * 1000
        analyzed.loc[analyzed.index[-1], "btc_uptrend_clean"] = 1

        return analyzed

    def test_entry_triggers_when_all_conditions_satisfied(self):
        """All 7 conditions met -> enter_long == 1 and enter_tag == 'hvrspb_breakout'."""
        df = self._create_aligned_breakout_df()
        entry_df = self.strategy.populate_entry_trend(df.copy(), {"pair": "FET/EUR"})

        self.assertEqual(entry_df["enter_long"].iloc[-1], 1)
        self.assertEqual(entry_df["enter_tag"].iloc[-1], "hvrspb_breakout")

    def test_entry_suppressed_when_close_below_donchian_high(self):
        """Condition 1 fails: close <= donchian_high -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "close"] = 99.0  # below donchian_high (100.0)
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)

    def test_entry_suppressed_when_close_below_keltner_upper(self):
        """Condition 2 fails: close <= keltner_upper -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "close"] = 100.5  # above donchian_high (100.0) but below keltner_upper (101.0)
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)

    def test_entry_suppressed_when_pvr_insufficient(self):
        """Condition 3 fails: pvr <= 1.15 -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "pvr"] = 1.10  # below 1.15
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)

    def test_entry_suppressed_when_rs_insufficient(self):
        """Condition 4 fails: rs_btc <= 0.025 -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "rs_btc"] = 0.020  # below 0.025
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)

    def test_entry_suppressed_when_volume_insufficient(self):
        """Condition 5 fails: volume <= 1.2 * volume_mean -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "volume"] = 1100.0  # below 1.2 * 1000.0 = 1200.0
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)

    def test_entry_suppressed_on_zero_volume(self):
        """Condition 7 fails: volume == 0 -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "volume"] = 0.0
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)

    def test_entry_suppressed_when_btc_in_downtrend(self):
        """BTC macro filter fails: btc_uptrend == 0 -> enter_long == 0."""
        df = self._create_aligned_breakout_df()
        df.loc[df.index[-1], "btc_uptrend_clean"] = 0
        entry_df = self.strategy.populate_entry_trend(df, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].iloc[-1], 0)


# =============================================================================
# 5. EXIT SIGNALS & DYNAMIC RISK TESTS
# =============================================================================

class TestExitSignalsAndRisk(unittest.TestCase):
    """Verifies exit signal generation, custom_exit fast invalidation, and custom_stoploss."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_populate_exit_trend_preserves_grace_period(self):
        """
        Verify populate_exit_trend does NOT trigger an exit on Donchian Midline break.
        Time-gated midline invalidation is strictly delegated to custom_exit to preserve
        the 4-candle grace period for breakout retest absorption.
        """
        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        analyzed.loc[analyzed.index[-1], "donchian_mid"] = 100.0
        analyzed.loc[analyzed.index[-1], "close"] = 98.0  # below donchian_mid
        analyzed.loc[analyzed.index[-1], "volume"] = 1000.0

        exit_df = self.strategy.populate_exit_trend(analyzed, {"pair": "FET/EUR"})
        self.assertEqual(
            exit_df["exit_long"].iloc[-1],
            0,
            "populate_exit_trend must not fire exit_long=1 on midline breach; "
            "it would prematurely kill trades during the 4-candle grace period."
        )
        self.assertIsNone(exit_df["exit_tag"].iloc[-1])

    def test_4_candle_grace_period_respected_before_midline_exit(self):
        """
        Comprehensive validation of the 4-candle invalidation grace period:
        1. Candles 1 to 3.9 (duration < 4h): Both custom_exit and populate_exit_trend
           return NO exit signal, allowing position to absorb normal retest volatility.
        2. Candle 4+ (duration >= 4h):
           - Below midline -> returns fast_invalidation_mid.
           - Loss < -1.5% -> returns fast_invalidation_loss.
           - Above midline and profit > -1.5% -> returns None.
        """
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [trade_open_time + timedelta(hours=5)],
            "donchian_mid": [100.0],
            "close": [97.0],
            "volume": [1000.0],
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # 1. During grace period (1h, 2h, 3h, 3.9h)
        for hours in [1.0, 2.0, 3.0, 3.9]:
            check_time = trade_open_time + timedelta(hours=hours)
            # custom_exit must be None
            res = self.strategy.custom_exit(
                pair="FET/EUR",
                trade=trade,
                current_time=check_time,
                current_rate=97.0,  # below donchian_mid
                current_profit=-0.01,
            )
            self.assertIsNone(res, f"Premature custom_exit triggered at {hours}h during grace period!")

            # populate_exit_trend must not emit exit_long
            exit_df = self.strategy.populate_exit_trend(df_analyzed.copy(), {"pair": "FET/EUR"})
            self.assertEqual(
                exit_df["exit_long"].iloc[-1],
                0,
                f"populate_exit_trend emitted exit_long=1 at {hours}h during grace period!"
            )

        # 2. Expiration of grace period (at exactly 4.0h and 5.0h)
        t_4h = trade_open_time + timedelta(hours=4.0)
        res_4h = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_4h,
            current_rate=97.0,  # below donchian_mid
            current_profit=-0.01,
        )
        self.assertEqual(res_4h, "fast_invalidation_mid")

        t_5h = trade_open_time + timedelta(hours=5.0)
        res_5h = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_5h,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertEqual(res_5h, "fast_invalidation_mid")

        # Adverse loss invalidation after 4h
        res_loss = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_5h,
            current_rate=102.0,  # above midline
            current_profit=-0.02,  # < -1.5%
        )
        self.assertEqual(res_loss, "fast_invalidation_loss")

        # Healthy trade after 4h: no exit
        res_ok = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_5h,
            current_rate=102.0,
            current_profit=0.01,
        )
        self.assertIsNone(res_ok)

    def test_exit_donchian_mid_parameter_governs_midline_exit(self):
        """Verify exit_donchian_mid boolean parameter actively gates midline exit."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        current_time = trade_open_time + timedelta(hours=5.0)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [current_time],
            "donchian_mid": [100.0],
            "close": [97.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # When disabled: midline exit must NOT trigger
        self.strategy.exit_donchian_mid.value = False
        res_disabled = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertIsNone(res_disabled)

        # When enabled: midline exit triggers
        self.strategy.exit_donchian_mid.value = True
        res_enabled = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertEqual(res_enabled, "fast_invalidation_mid")

    def test_invalidation_candles_parameter_governs_grace_duration(self):
        """Verify invalidation_candles dynamically controls the grace period length."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [trade_open_time + timedelta(hours=10)],
            "donchian_mid": [100.0],
            "close": [97.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # Set invalidation candles to 6 hours
        self.strategy.invalidation_candles.value = 6

        # At 4.5h (would have triggered under default 4h, but protected under 6h)
        t_4_5h = trade_open_time + timedelta(hours=4, minutes=30)
        res_protected = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_4_5h,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertIsNone(res_protected)

        # At 6.5h (expired under 6h threshold)
        t_6_5h = trade_open_time + timedelta(hours=6, minutes=30)
        res_expired = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_6_5h,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertEqual(res_expired, "fast_invalidation_mid")

    def test_no_exit_when_trend_healthy(self):
        """Close safely above Donchian Midline -> exit_long == 0."""
        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        analyzed.loc[analyzed.index[-1], "donchian_mid"] = 100.0
        analyzed.loc[analyzed.index[-1], "close"] = 105.0  # above donchian_mid

        exit_df = self.strategy.populate_exit_trend(analyzed, {"pair": "FET/EUR"})
        self.assertEqual(exit_df["exit_long"].iloc[-1], 0)

    def test_custom_exit_fast_invalidation_after_4_candles(self):
        """
        After 4 candles (hours), if current_rate < donchian_mid,
        custom_exit immediately liquidates position.
        """
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        current_time = datetime(2026, 1, 1, 14, 30, tzinfo=timezone.utc)  # 4.5h elapsed
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        # Analyzed dataframe where donchian_mid is 100.0
        df_analyzed = pd.DataFrame({
            "date": [current_time],
            "donchian_mid": [100.0],
            "close": [97.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        result = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=97.0,  # below donchian_mid
            current_profit=-0.03,
        )
        self.assertEqual(result, "fast_invalidation_mid")

    def test_custom_exit_no_invalidation_before_4_candles(self):
        """Before 4 candles elapsed, trade is given initial breathing room."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        current_time = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # only 2h elapsed
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [current_time],
            "donchian_mid": [100.0],
            "close": [98.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        result = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=98.0,
            current_profit=-0.02,
        )
        self.assertIsNone(result)

    def test_custom_exit_fast_invalidation_adverse_loss(self):
        """After 4 candles, if current_profit < -1.5%, triggers fast_invalidation_loss."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        current_time = datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)  # 5h elapsed
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)
        self.strategy.dp = MockDataProvider()

        result = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=98.0,
            current_profit=-0.02,  # -2.0% loss
        )
        self.assertEqual(result, "fast_invalidation_loss")

    def test_custom_exit_stale_trade(self):
        """Trade open for 15 days triggers stale_exit."""
        trade_open_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)  # 15 days elapsed
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)
        self.strategy.dp = MockDataProvider()

        result = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=101.0,
            current_profit=0.01,
        )
        self.assertEqual(result, "stale_exit")

    def test_custom_stoploss_below_breakeven_threshold(self):
        """Profit < +3.5%: returns None (default hard stoploss governs)."""
        trade = MockTrade(open_rate=100.0)
        now = datetime.now(timezone.utc)
        sl = self.strategy.custom_stoploss(
            pair="FET/EUR",
            trade=trade,
            current_time=now,
            current_rate=102.0,
            current_profit=0.02,  # 2.0% profit
        )
        self.assertIsNone(sl)

    def test_custom_stoploss_breakeven_lock(self):
        """Profit >= +3.5%: locks stop at +0.8% above open price."""
        trade = MockTrade(open_rate=100.0)
        now = datetime.now(timezone.utc)
        # Entry = 100, current = 103.5 (+3.5% profit)
        # Lock at +0.8% = 100.8
        # Relative distance from current = (100.8 - 103.5) / 103.5 = -2.7 / 103.5 = -0.0260869...
        sl = self.strategy.custom_stoploss(
            pair="FET/EUR",
            trade=trade,
            current_time=now,
            current_rate=103.5,
            current_profit=0.035,
        )
        self.assertIsNotNone(sl)
        self.assertLess(sl, 0.0)
        expected_distance = (100.0 * 1.008 - 103.5) / 103.5
        self.assertAlmostEqual(sl, expected_distance, places=4)

    def test_custom_stoploss_trailing_runner(self):
        """Profit >= +8.0%: runner trailing activates with 4.0% distance."""
        trade = MockTrade(open_rate=100.0)
        now = datetime.now(timezone.utc)
        sl = self.strategy.custom_stoploss(
            pair="FET/EUR",
            trade=trade,
            current_time=now,
            current_rate=112.0,
            current_profit=0.12,  # +12.0% profit
        )
        self.assertIsNotNone(sl)
        expected_trail = -float(self.strategy.trailing_runner_distance.value)  # -0.040
        self.assertEqual(sl, expected_trail)


# =============================================================================
# 6. EDGE CASES & DATA HYGIENE TESTS
# =============================================================================

class TestEdgeCasesAndDataHygiene(unittest.TestCase):
    """Verifies resilience against corrupted feeds, empty data, and NaNs."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_empty_dataframe(self):
        """Empty dataframe must be returned cleanly without exception."""
        empty_df = pd.DataFrame()
        res_ind = self.strategy.populate_indicators(empty_df.copy(), {"pair": "FET/EUR"})
        self.assertTrue(res_ind.empty)
        res_entry = self.strategy.populate_entry_trend(empty_df.copy(), {"pair": "FET/EUR"})
        self.assertTrue(res_entry.empty)
        res_exit = self.strategy.populate_exit_trend(empty_df.copy(), {"pair": "FET/EUR"})
        self.assertTrue(res_exit.empty)

    def test_missing_required_columns(self):
        """DataFrame with missing required columns handled safely."""
        corrupt_df = pd.DataFrame({"some_col": [1, 2, 3]})
        res = self.strategy.populate_indicators(corrupt_df.copy(), {"pair": "FET/EUR"})
        self.assertEqual(len(res), 3)

    def test_fifty_consecutive_flat_candles(self):
        """Fifty zero-volatility bars must not trigger division errors or entry signals."""
        flat_df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=50, freq="1h", tz="UTC"),
            "open": np.full(50, 100.0),
            "high": np.full(50, 100.0),
            "low": np.full(50, 100.0),
            "close": np.full(50, 100.0),
            "volume": np.full(50, 1000.0),
        })
        analyzed = self.strategy.populate_indicators(flat_df, {"pair": "FET/EUR"})
        entry_df = self.strategy.populate_entry_trend(analyzed, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].sum(), 0)

    def test_startup_warmup_nans_do_not_trigger_entries(self):
        """During startup warmup period, enter_long must never be 1."""
        df = generate_synthetic_ohlcv(n_bars=50)
        analyzed = self.strategy.populate_indicators(df, {"pair": "FET/EUR"})
        entry_df = self.strategy.populate_entry_trend(analyzed, {"pair": "FET/EUR"})
        self.assertEqual(entry_df["enter_long"].sum(), 0)


# =============================================================================
# 7. FREQTRADE API CONFORMANCE & MAKER CONFIGURATION
# =============================================================================

class TestFreqtradeInterfaceAndContract(unittest.TestCase):
    """Verifies interface contract compliance, limit order types, and hyperopt spaces."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})

    def test_interface_version_and_timeframe(self):
        """Contract: INTERFACE_VERSION == 3 and timeframe == '1h'."""
        self.assertEqual(self.strategy.INTERFACE_VERSION, 3)
        self.assertEqual(self.strategy.timeframe, "1h")

    def test_informative_pairs_contract(self):
        """informative_pairs must register BTC/EUR and BTC/USDT on 1h."""
        pairs = self.strategy.informative_pairs()
        self.assertIn(("BTC/EUR", "1h"), pairs)
        self.assertIn(("BTC/USDT", "1h"), pairs)

    def test_order_types_maker_fees(self):
        """Entry and exit order types must be limit orders to capture maker fee rebate."""
        self.assertEqual(self.strategy.order_types.get("entry"), "limit")
        self.assertEqual(self.strategy.order_types.get("exit"), "limit")

    def test_hyperopt_spaces_presence(self):
        """Verify parameters exist across buy and sell spaces with zero dead code."""
        # Buy Space
        self.assertEqual(self.strategy.donchian_period.space, "buy")
        self.assertEqual(self.strategy.keltner_mult.space, "buy")
        self.assertEqual(self.strategy.pvr_threshold.space, "buy")
        self.assertEqual(self.strategy.rs_threshold.space, "buy")
        self.assertEqual(self.strategy.volume_factor.space, "buy")
        self.assertEqual(self.strategy.macro_filter_mode.space, "buy")

        # Sell Space: Fast invalidation & two-tier trailing stop
        self.assertEqual(self.strategy.exit_donchian_mid.space, "sell")
        self.assertEqual(self.strategy.invalidation_candles.space, "sell")
        self.assertEqual(self.strategy.be_profit_threshold.space, "sell")
        self.assertEqual(self.strategy.be_lock_margin.space, "sell")
        self.assertEqual(self.strategy.trailing_runner_offset.space, "sell")
        self.assertEqual(self.strategy.trailing_runner_distance.space, "sell")

        # Hard stoploss facade parameter must be deleted (stoploss is handled natively)
        self.assertFalse(
            hasattr(WolfBreakout_HVRSPB, "hard_stoploss"),
            "Dead-code facade parameter hard_stoploss must be removed from strategy class."
        )

        # Native stoploss and HyperOpt inner class
        self.assertEqual(self.strategy.stoploss, -0.06)
        self.assertTrue(hasattr(self.strategy, "HyperOpt"))
        sl_space = self.strategy.HyperOpt.stoploss_space()
        self.assertEqual(len(sl_space), 1)
        self.assertEqual(sl_space[0].name, "stoploss")
        self.assertEqual(sl_space[0].low, -0.12)
        self.assertEqual(sl_space[0].high, -0.04)

        # Invariant: All custom strategy parameters must belong exclusively to buy or sell spaces
        self.strategy.ft_load_hyper_params()
        for name, param in self.strategy.enumerate_parameters():
            self.assertIn(
                param.space,
                ["buy", "sell"],
                f"Parameter '{name}' has space='{param.space}'. Custom parameters must only use 'buy' or 'sell'.",
            )

    def test_no_dead_code_parameters(self):
        """
        AST inspection: Asserts that every BaseParameter defined at the class level
        is actively accessed on self in executable strategy methods.
        """
        import ast
        import inspect

        source = inspect.getsource(WolfBreakout_HVRSPB)
        tree = ast.parse(source)
        strat_class = [
            n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "WolfBreakout_HVRSPB"
        ][0]

        # Parameters declared on class
        param_names = set()
        for stmt in strat_class.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                        func_name = getattr(stmt.value.func, "id", "")
                        if "Parameter" in func_name:
                            param_names.add(target.id)

        # Attributes accessed on self inside method bodies
        used_attrs = set()
        for stmt in strat_class.body:
            if isinstance(stmt, ast.FunctionDef):
                for subnode in ast.walk(stmt):
                    if (
                        isinstance(subnode, ast.Attribute)
                        and isinstance(subnode.value, ast.Name)
                        and subnode.value.id == "self"
                    ):
                        used_attrs.add(subnode.attr)

        dead_params = param_names - used_attrs
        self.assertEqual(
            dead_params,
            set(),
            f"Dead-code parameters detected in WolfBreakout_HVRSPB: {dead_params}. "
            f"Every parameter must be actively referenced in strategy logic."
        )

    def test_hyperopt_parameter_resolution_all_spaces(self):
        """
        Simulates Freqtrade HyperOptimizer across all spaces
        (['buy', 'sell'], ['stoploss'], ['trailing'], ['buy', 'sell', 'stoploss'], ['default'], ['all']).
        Verifies that all parameters where p.in_space and p.optimize can be resolved
        from the trial dictionary without KeyError.
        """
        from freqtrade.optimize.hyperopt.hyperopt_auto import HyperOptAuto

        space_combos = [
            ["buy", "sell"],
            ["buy", "sell", "stoploss"],
            ["stoploss"],
            ["trailing"],
            ["all"],
            ["default"],
        ]
        for spaces in space_combos:
            config = {"stake_currency": "EUR", "timeframe": "1h", "spaces": spaces}
            strat = WolfBreakout_HVRSPB(config)
            strat.ft_load_hyper_params(hyperopt=True)
            auto = HyperOptAuto(config)
            auto.strategy = strat

            dimensions = []
            if "buy" in spaces or "all" in spaces or "default" in spaces:
                dimensions.extend(auto.get_indicator_space("buy"))
            if "sell" in spaces or "all" in spaces or "default" in spaces:
                dimensions.extend(auto.get_indicator_space("sell"))
            if "stoploss" in spaces or "all" in spaces or "default" in spaces:
                dimensions.extend(auto.stoploss_space())
            if "trailing" in spaces or "all" in spaces:
                dimensions.extend(auto.trailing_space())

            # Generate synthetic trial parameters dictionary from dimensions
            params_dict = {}
            for dim in dimensions:
                if hasattr(dim, "low") and hasattr(dim, "high"):
                    params_dict[dim.name] = (dim.low + dim.high) / 2.0
                elif hasattr(dim, "categories"):
                    params_dict[dim.name] = dim.categories[0]
                else:
                    params_dict[dim.name] = 0

            # Simulate Freqtrade HyperOptimizer parameter assignment
            for attr_name, attr in strat.enumerate_parameters():
                if attr.in_space and attr.optimize:
                    self.assertIn(
                        attr_name,
                        params_dict,
                        f"Hyperopt KeyError risk! Parameter '{attr_name}' (space='{attr.space}') is marked "
                        f"in_space=True for spaces={spaces}, but missing from trial params_dict!"
                    )
                    attr.value = params_dict[attr_name]

            # Simulate native stoploss space assignment
            if "stoploss" in spaces or "all" in spaces or "default" in spaces:
                self.assertIn("stoploss", params_dict)
                strat.stoploss = params_dict["stoploss"]

    def test_minimal_roi_table_monotonic_decay(self):
        """Minimal ROI targets must monotonically decrease over time."""
        roi = self.strategy.minimal_roi
        sorted_times = sorted([int(k) for k in roi.keys()])
        for i in range(len(sorted_times) - 1):
            t1, t2 = str(sorted_times[i]), str(sorted_times[i + 1])
            self.assertGreaterEqual(
                roi[t1],
                roi[t2],
                f"ROI target at {t1}m ({roi[t1]}) must be >= target at {t2}m ({roi[t2]})"
            )


if __name__ == "__main__":
    unittest.main()
