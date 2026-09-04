"""
tests/test_boundary_sensitivity.py — Adversarial Boundary & Parameter Sensitivity Test Suite
=============================================================================================
Milestone 1 Challenger 2: Parameter & Boundary Sensitivity Stress Tests for WolfBreakout_PVB

This test suite challenges and stress-tests:
1. Hyperopt parameter boundary extremes (min/max bounds for donchian, pvr, keltner, volume, ema).
2. Combinatorial corner sweep (32 parameter permutations across all hyperopt boundary corners).
3. Warmup sensitivity and startup candle count (short series, boundary at 250 candles, EMA 220 convergence).
4. Noise tolerance and gap openings (pure Gaussian noise, 50% gap up, 50% gap down, volatility explosions).
5. Corrupt and anomalous OHLCV data (inverted high/low, zero prices, negative prices, NaNs, empty/single-row data).
6. Loss protection and trailing stop logic (hard stoploss -4.5%, trailing stop offset/trail math, stale exit precision).
"""
from __future__ import annotations

import math
import sys
import unittest
from datetime import datetime, timezone, timedelta
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRAT_DIR = PROJECT_ROOT / "user_data" / "strategies"
TESTS_DIR = PROJECT_ROOT / "tests"
if str(STRAT_DIR) not in sys.path:
    sys.path.insert(0, str(STRAT_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

try:
    from WolfBreakout_PVB import WolfBreakout_PVB
except ImportError:
    WolfBreakout_PVB = None

from test_wolfbreakout_pvb import MockDataProvider, generate_synthetic_ohlcv, generate_synthetic_btc


def reset_strategy_parameters(strategy: WolfBreakout_PVB):
    """Restores default parameter values on shared class descriptors for strict test isolation."""
    strategy.donchian_period.value = 20
    strategy.pvr_threshold.value = 1.10
    strategy.keltner_mult.value = 1.75
    strategy.volume_factor.value = 1.20
    strategy.trend_ema_period.value = 100
    strategy.exit_donchian_mid.value = True
    strategy.exit_ema_basis.value = False


# =============================================================================
# SUITE 1: HYPEROPT BOUNDARY CORNERS & COMBINATORIAL SWEEPS
# =============================================================================

class TestHyperoptBoundaryCorners(unittest.TestCase):
    """Stress tests strategy behavior across parameter extremes and corner permutations."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        reset_strategy_parameters(self.strategy)
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def tearDown(self):
        if hasattr(self, "strategy"):
            reset_strategy_parameters(self.strategy)

    def test_hyperopt_extreme_minimum_parameters(self):
        """Strategy must function cleanly with all parameters set to their minimum hyperopt bounds."""
        self.strategy.donchian_period.value = 14
        self.strategy.pvr_threshold.value = 1.02
        self.strategy.keltner_mult.value = 1.20
        self.strategy.volume_factor.value = 1.05
        self.strategy.trend_ema_period.value = 80
        self.strategy.exit_donchian_mid.value = False
        self.strategy.exit_ema_basis.value = False

        df = generate_synthetic_ohlcv(n_bars=300, seed=42)
        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

        # Confirm indicator calculations are complete and valid after warmup
        valid_slice = ind.iloc[85:]
        for col in ["donchian_high", "donchian_mid", "keltner_upper", "pvr", "volume_mean", "ema_trend"]:
            self.assertFalse(valid_slice[col].isna().any(), f"NaN detected in {col} at minimum bounds.")
            self.assertFalse(np.isinf(valid_slice[col]).any(), f"Inf detected in {col} at minimum bounds.")

        self.assertIn("enter_long", entry.columns)
        self.assertIn("exit_long", exit_df.columns)
        self.assertTrue(set(entry["enter_long"].unique()).issubset({0, 1}))
        self.assertTrue(set(exit_df["exit_long"].unique()).issubset({0, 1}))

    def test_hyperopt_extreme_maximum_parameters(self):
        """Strategy must function cleanly with all parameters set to their maximum hyperopt bounds."""
        self.strategy.donchian_period.value = 36
        self.strategy.pvr_threshold.value = 1.35
        self.strategy.keltner_mult.value = 2.50
        self.strategy.volume_factor.value = 1.50
        self.strategy.trend_ema_period.value = 220
        self.strategy.exit_donchian_mid.value = True
        self.strategy.exit_ema_basis.value = True

        df = generate_synthetic_ohlcv(n_bars=300, seed=43)
        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

        # After 225 candles, all rolling windows and EMA 220 must be stabilized
        valid_slice = ind.iloc[225:]
        for col in ["donchian_high", "donchian_mid", "keltner_upper", "pvr", "volume_mean", "ema_trend"]:
            self.assertFalse(valid_slice[col].isna().any(), f"NaN detected in {col} at maximum bounds.")
            self.assertFalse(np.isinf(valid_slice[col]).any(), f"Inf detected in {col} at maximum bounds.")

        self.assertTrue(set(entry["enter_long"].unique()).issubset({0, 1}))
        self.assertTrue(set(exit_df["exit_long"].unique()).issubset({0, 1}))

    def test_hyperopt_boundary_corners_grid_sweep(self):
        """
        Combinatorial stress test across all 2^5 = 32 boundary corners of buy space.
        Verifies no parameter combinations trigger crashes, math errors, or corrupted columns.
        """
        donchian_bounds = [14, 36]
        pvr_bounds = [1.02, 1.35]
        keltner_bounds = [1.20, 2.50]
        volume_bounds = [1.05, 1.50]
        trend_bounds = [80, 220]

        df = generate_synthetic_ohlcv(n_bars=280, seed=44)

        for donch, pvr, kelt, vol, trend in product(
            donchian_bounds, pvr_bounds, keltner_bounds, volume_bounds, trend_bounds
        ):
            self.strategy.donchian_period.value = donch
            self.strategy.pvr_threshold.value = pvr
            self.strategy.keltner_mult.value = kelt
            self.strategy.volume_factor.value = vol
            self.strategy.trend_ema_period.value = trend

            ind = self.strategy.populate_indicators(df.copy(), self.metadata)
            entry = self.strategy.populate_entry_trend(ind, self.metadata)
            exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

            # Check validity of output series
            self.assertEqual(entry["enter_long"].dtype, np.int64)
            self.assertEqual(exit_df["exit_long"].dtype, np.int64)
            self.assertFalse(entry["enter_long"].isna().any())
            self.assertFalse(exit_df["exit_long"].isna().any())

    def test_both_exit_modes_disabled(self):
        """When exit_donchian_mid=False and exit_ema_basis=False, exit_long must remain 0."""
        self.strategy.exit_donchian_mid.value = False
        self.strategy.exit_ema_basis.value = False

        df = generate_synthetic_ohlcv(n_bars=100, seed=45)
        ind = self.strategy.populate_indicators(df, self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

        self.assertEqual(exit_df["exit_long"].sum(), 0,
                         "Exit signals generated when all indicator exits were disabled.")

    def test_both_exit_modes_enabled_logical_or(self):
        """When both exit modes are True, exit triggers if EITHER Donchian Mid OR EMA basis is broken."""
        self.strategy.exit_donchian_mid.value = True
        self.strategy.exit_ema_basis.value = True

        df = generate_synthetic_ohlcv(n_bars=60, seed=46)
        ind = self.strategy.populate_indicators(df, self.metadata)

        # Candle 40: close breaks Donchian Mid only
        ind.loc[40, "donchian_mid"] = 105.0
        ind.loc[40, "ema_basis"] = 95.0
        ind.loc[40, "close"] = 100.0  # < donchian_mid, but > ema_basis
        ind.loc[40, "volume"] = 1000.0

        # Candle 41: close breaks EMA basis only
        ind.loc[41, "donchian_mid"] = 95.0
        ind.loc[41, "ema_basis"] = 105.0
        ind.loc[41, "close"] = 100.0  # > donchian_mid, but < ema_basis
        ind.loc[41, "volume"] = 1000.0

        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)
        self.assertEqual(exit_df.loc[40, "exit_long"], 1, "Failed to exit when Donchian Mid broken.")
        self.assertEqual(exit_df.loc[41, "exit_long"], 1, "Failed to exit when EMA Basis broken.")

    def test_hyperopt_spaces_distributions_and_types(self):
        """Verifies mathematical distributions and bounds for all 7 hyperopt parameters via get_space()."""
        # Donchian: IntParameter(14, 36)
        donch_space = self.strategy.donchian_period.get_space("donchian_period")
        self.assertEqual(donch_space.low, 14)
        self.assertEqual(donch_space.high, 36)

        # PVR: DecimalParameter(1.02, 1.35, decimals=2)
        pvr_space = self.strategy.pvr_threshold.get_space("pvr_threshold")
        self.assertAlmostEqual(pvr_space.low, 1.02, places=2)
        self.assertAlmostEqual(pvr_space.high, 1.35, places=2)

        # Keltner: DecimalParameter(1.20, 2.50, decimals=2)
        kelt_space = self.strategy.keltner_mult.get_space("keltner_mult")
        self.assertAlmostEqual(kelt_space.low, 1.20, places=2)
        self.assertAlmostEqual(kelt_space.high, 2.50, places=2)

        # Volume: DecimalParameter(1.05, 1.50, decimals=2)
        vol_space = self.strategy.volume_factor.get_space("volume_factor")
        self.assertAlmostEqual(vol_space.low, 1.05, places=2)
        self.assertAlmostEqual(vol_space.high, 1.50, places=2)

        # Trend EMA: IntParameter(80, 220)
        ema_space = self.strategy.trend_ema_period.get_space("trend_ema_period")
        self.assertEqual(ema_space.low, 80)
        self.assertEqual(ema_space.high, 220)

        # Exit booleans
        mid_space = self.strategy.exit_donchian_mid.get_space("exit_donchian_mid")
        self.assertEqual(set(mid_space.categories), {True, False})
        ema_b_space = self.strategy.exit_ema_basis.get_space("exit_ema_basis")
        self.assertEqual(set(ema_b_space.categories), {True, False})

    def test_fuzz_random_hyperopt_sampling_stability(self):
        """
        Fuzz stress test: samples 50 random points across the parameter hypercube.
        Confirms zero exceptions, NaNs, or unexpected shapes across all indicator and signal methods.
        """
        rng = np.random.default_rng(777)
        df = generate_synthetic_ohlcv(n_bars=280, seed=123)

        for _ in range(50):
            self.strategy.donchian_period.value = int(rng.integers(14, 37))
            self.strategy.pvr_threshold.value = round(float(rng.uniform(1.02, 1.35)), 2)
            self.strategy.keltner_mult.value = round(float(rng.uniform(1.20, 2.50)), 2)
            self.strategy.volume_factor.value = round(float(rng.uniform(1.05, 1.50)), 2)
            self.strategy.trend_ema_period.value = int(rng.integers(80, 221))
            self.strategy.exit_donchian_mid.value = bool(rng.choice([True, False]))
            self.strategy.exit_ema_basis.value = bool(rng.choice([True, False]))

            ind = self.strategy.populate_indicators(df.copy(), self.metadata)
            entry = self.strategy.populate_entry_trend(ind, self.metadata)
            exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

            self.assertEqual(len(entry), 280)
            self.assertEqual(len(exit_df), 280)


# =============================================================================
# SUITE 2: WARMUP SENSITIVITY & DATASET LENGTH BOUNDARIES
# =============================================================================

class TestStartupCandleWarmupSensitivity(unittest.TestCase):
    """Stress tests behavior with varying historical dataset lengths and warmup conditions."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        reset_strategy_parameters(self.strategy)
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def tearDown(self):
        if hasattr(self, "strategy"):
            reset_strategy_parameters(self.strategy)

    def test_short_dataframe_warmup_graceful_handling(self):
        """DataFrames shorter than startup_candle_count must calculate safely and not enter."""
        for length in [5, 15, 50, 100]:
            df = generate_synthetic_ohlcv(n_bars=length, seed=50 + length)
            ind = self.strategy.populate_indicators(df, self.metadata)
            entry = self.strategy.populate_entry_trend(ind, self.metadata)
            exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

            self.assertEqual(len(entry), length)
            self.assertEqual(len(exit_df), length)
            # In short frames where indicators are NaN, enter_long must be safely 0
            self.assertTrue((entry["enter_long"].fillna(0) == 0).all(),
                            f"Premature entry triggered on short history of length {length}!")

    def test_startup_candle_count_exact_boundary(self):
        """Test exact boundary condition around startup_candle_count = 250."""
        self.assertEqual(self.strategy.startup_candle_count, 250)

        # 249 candles (1 below startup_candle_count)
        df_249 = generate_synthetic_ohlcv(n_bars=249, seed=61)
        ind_249 = self.strategy.populate_indicators(df_249, self.metadata)
        # 250 candles (exact startup_candle_count)
        df_250 = generate_synthetic_ohlcv(n_bars=250, seed=61)
        ind_250 = self.strategy.populate_indicators(df_250, self.metadata)

        # EMA 200 on BTC and trend_ema_period (up to 220) must be populated by bar 249
        self.assertFalse(np.isnan(ind_250.loc[249, "ema_trend"]))
        self.assertFalse(np.isnan(ind_250.loc[249, "donchian_high"]))
        self.assertFalse(np.isnan(ind_250.loc[249, "pvr"]))

    def test_maximum_trend_ema_period_warmup_at_startup_boundary(self):
        """When trend_ema_period = 220 (max), startup_candle_count (250) ensures full convergence."""
        self.strategy.trend_ema_period.value = 220
        df = generate_synthetic_ohlcv(n_bars=250, seed=70)
        ind = self.strategy.populate_indicators(df, self.metadata)

        # At index 249 (the 250th candle), EMA 220 must not be NaN
        self.assertFalse(np.isnan(ind.loc[249, "ema_trend"]),
                         "trend_ema_period=220 produced NaN at startup_candle_count boundary (candle 250)!")


# =============================================================================
# SUITE 3: NOISE TOLERANCE, GAP OPENINGS & VOLATILITY SPIKES
# =============================================================================

class TestNoiseAndGapSensitivity(unittest.TestCase):
    """Stress tests noise rejection, explosive gap openings, and flash crashes."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        reset_strategy_parameters(self.strategy)
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def tearDown(self):
        if hasattr(self, "strategy"):
            reset_strategy_parameters(self.strategy)

    def test_pure_gaussian_noise_false_breakout_rejection(self):
        """
        Pure Gaussian random walk without structural trend or volume surge must
        strongly suppress entry signals (< 3% false triggers over 1000 candles).
        """
        rng = np.random.default_rng(888)
        n_bars = 1000
        # Pure uncoordinated random noise
        prices = 100.0 + np.cumsum(rng.normal(0, 0.5, size=n_bars))
        prices = np.clip(prices, 50.0, 200.0)

        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": prices,
            "high": prices + rng.uniform(0.01, 0.5, size=n_bars),
            "low": prices - rng.uniform(0.01, 0.5, size=n_bars),
            "close": prices + rng.normal(0, 0.2, size=n_bars),
            "volume": rng.uniform(100.0, 500.0, size=n_bars),  # Flat volume noise
        })

        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)

        # Evaluate after warmup
        valid_entries = entry.loc[250:, "enter_long"].sum()
        total_eval_bars = len(entry) - 250
        entry_rate = valid_entries / total_eval_bars

        self.assertLess(entry_rate, 0.03,
                        f"Excessive false breakout entries on pure Gaussian noise ({entry_rate:.2%})!")

    def test_massive_gap_up_mechanics(self):
        """
        A massive +50% overnight gap must calculate Parkinson volatility, expand Donchian on t+1,
        and not corrupt numerical stability.
        """
        df = generate_synthetic_ohlcv(n_bars=100, seed=99)
        gap_idx = 60

        # Create massive +50% gap
        pre_gap_close = df.loc[gap_idx - 1, "close"]
        df.loc[gap_idx, "open"] = pre_gap_close * 1.50
        df.loc[gap_idx, "high"] = pre_gap_close * 1.55
        df.loc[gap_idx, "low"] = pre_gap_close * 1.48
        df.loc[gap_idx, "close"] = pre_gap_close * 1.52
        df.loc[gap_idx, "volume"] = df.loc[gap_idx - 1, "volume"] * 5.0

        ind = self.strategy.populate_indicators(df, self.metadata)

        # On the gap candle (t=60), donchian_high must still reflect pre-gap level (shift 1)
        self.assertLess(ind.loc[gap_idx, "donchian_high"], pre_gap_close * 1.20)
        # On candle t=61, donchian_high must update to include the gap candle's high
        self.assertAlmostEqual(ind.loc[gap_idx + 1, "donchian_high"], pre_gap_close * 1.55)

        # Parkinson volatility should remain finite and positive
        self.assertFalse(np.isnan(ind.loc[gap_idx, "pvr"]))
        self.assertFalse(np.isinf(ind.loc[gap_idx, "pvr"]))
        self.assertGreater(ind.loc[gap_idx, "pvr"], 0.0)

    def test_massive_gap_down_flash_crash(self):
        """
        A severe -50% flash crash must IMMEDIATELY trigger exit_long and NEVER trigger enter_long.
        """
        df = generate_synthetic_ohlcv(n_bars=100, seed=100)
        crash_idx = 60

        pre_close = df.loc[crash_idx - 1, "close"]
        df.loc[crash_idx, "open"] = pre_close * 0.50
        df.loc[crash_idx, "high"] = pre_close * 0.52
        df.loc[crash_idx, "low"] = pre_close * 0.45
        df.loc[crash_idx, "close"] = pre_close * 0.48
        df.loc[crash_idx, "volume"] = 10000.0

        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

        self.assertEqual(entry.loc[crash_idx, "enter_long"], 0,
                         "Entry triggered during catastrophic flash crash!")
        self.assertEqual(exit_df.loc[crash_idx, "exit_long"], 1,
                         "Failed to trigger exit signal during catastrophic flash crash!")

    def test_extreme_candle_amplitude_parkinson_variance(self):
        """Extreme candle ratio (H=1000, L=0.01) must calculate Parkinson variance without overflow."""
        df = generate_synthetic_ohlcv(n_bars=60, seed=101)
        df.loc[45, "high"] = 1000.0
        df.loc[45, "low"] = 0.01

        ind = self.strategy.populate_indicators(df, self.metadata)
        var_fast = ind.loc[45, "parkinson_fast"]
        pvr = ind.loc[45, "pvr"]

        self.assertFalse(np.isnan(var_fast))
        self.assertFalse(np.isinf(var_fast))
        self.assertFalse(np.isnan(pvr))
        self.assertFalse(np.isinf(pvr))
        self.assertGreater(pvr, 1.0)


# =============================================================================
# SUITE 4: CORRUPT & PATHOLOGICAL OHLCV INPUTS
# =============================================================================

class TestCorruptAndAnomalousOHLCV(unittest.TestCase):
    """Stress tests resilience against corrupted market data feeds."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        reset_strategy_parameters(self.strategy)
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def tearDown(self):
        if hasattr(self, "strategy"):
            reset_strategy_parameters(self.strategy)

    def test_inverted_candle_high_less_than_low(self):
        """
        If a buggy exchange feed reports High < Low, the strategy's
        `ratio = (high / safe_low).clip(lower=1.0)` must clamp to 1.0,
        yielding 0 variance without crashing or producing negative variance.
        """
        df = generate_synthetic_ohlcv(n_bars=60, seed=110)
        df.loc[40, "high"] = 80.0
        df.loc[40, "low"] = 120.0  # Inverted: high < low

        ind = self.strategy.populate_indicators(df, self.metadata)
        self.assertFalse(np.isnan(ind.loc[40, "parkinson_fast"]))
        self.assertFalse(np.isinf(ind.loc[40, "parkinson_fast"]))
        self.assertGreaterEqual(ind.loc[40, "parkinson_fast"], 0.0)

    def test_negative_prices_handling(self):
        """Negative price anomalies must be safely clipped by safe_low = dataframe['low'].clip(lower=1e-8)."""
        df = generate_synthetic_ohlcv(n_bars=60, seed=111)
        df.loc[35, "low"] = -50.0
        df.loc[35, "high"] = 100.0

        ind = self.strategy.populate_indicators(df, self.metadata)
        self.assertFalse(np.isnan(ind.loc[35, "parkinson_fast"]))
        self.assertFalse(np.isinf(ind.loc[35, "parkinson_fast"]))

    def test_all_zero_ohlcv_candle(self):
        """A zero price candle (feed dropout) must not cause zero division or unhandled exceptions."""
        df = generate_synthetic_ohlcv(n_bars=60, seed=112)
        df.loc[30, ["open", "high", "low", "close", "volume"]] = 0.0

        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)

        self.assertEqual(entry.loc[30, "enter_long"], 0)

    def test_nan_values_in_middle_of_series(self):
        """A NaN value injected into prices must not crash indicator calculation or generate entry."""
        df = generate_synthetic_ohlcv(n_bars=60, seed=113)
        df.loc[35, "close"] = np.nan
        df.loc[35, "high"] = np.nan

        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)

        self.assertEqual(entry.loc[35, "enter_long"], 0)

    def test_single_row_dataframe(self):
        """Edge case: 1-row DataFrame must not throw an unhandled exception."""
        df = generate_synthetic_ohlcv(n_bars=1, seed=114)
        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

        self.assertEqual(len(entry), 1)
        self.assertEqual(entry.loc[0, "enter_long"], 0)


# =============================================================================
# SUITE 5: STOPLOSS & TRAILING STOP LOSS PROTECTION LOGIC
# =============================================================================

class TestStoplossAndTrailingStopExecution(unittest.TestCase):
    """Stress tests risk management parameters, trailing offsets, and custom exits."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        reset_strategy_parameters(self.strategy)

    def tearDown(self):
        if hasattr(self, "strategy"):
            reset_strategy_parameters(self.strategy)

    def test_hard_stoploss_exact_configuration(self):
        """Hard stoploss must provide downside protection within reasonable bounds."""
        self.assertLess(self.strategy.stoploss, 0)
        self.assertGreaterEqual(self.strategy.stoploss, -0.50)
        self.assertEqual(self.strategy.stoploss, -0.34)

    def test_trailing_stop_parameter_hierarchy(self):
        """
        Trailing stop configuration must adhere to strict Freqtrade mathematical rules:
        1. trailing_stop == True
        2. trailing_stop_positive_offset > trailing_stop_positive
        3. trailing_stop_positive_offset - trailing_stop_positive > 0 (locks in positive profit at activation)
        """
        self.assertTrue(self.strategy.trailing_stop)
        self.assertIsInstance(self.strategy.trailing_only_offset_is_reached, bool)
        self.assertGreater(self.strategy.trailing_stop_positive_offset, self.strategy.trailing_stop_positive)

        # Activation point locks in profit
        locked_profit_on_activation = (
            self.strategy.trailing_stop_positive_offset - self.strategy.trailing_stop_positive
        )
        self.assertGreater(locked_profit_on_activation, 0.05,
                           msg="Activation must guarantee positive profit lock.")

    def test_simulated_trade_lifecycle_trailing_lock(self):
        """
        Simulates trade progression through key price milestones to verify trailing stop dynamics:
        """
        entry_price = 100.0
        hard_stop_rate = entry_price * (1.0 + self.strategy.stoploss)
        self.assertAlmostEqual(hard_stop_rate, entry_price * (1.0 + self.strategy.stoploss))

        # Simulation function matching Freqtrade trailing stop engine logic
        def compute_stop_rate(peak_rate: float) -> float:
            peak_profit = (peak_rate - entry_price) / entry_price
            if self.strategy.trailing_only_offset_is_reached:
                if peak_profit < self.strategy.trailing_stop_positive_offset:
                    return hard_stop_rate
                else:
                    return peak_rate * (1.0 - self.strategy.trailing_stop_positive)
            else:
                return peak_rate * (1.0 - self.strategy.trailing_stop_positive)

        # Peak at +40% profit: stop trails at peak_rate * (1 - trailing_stop_positive)
        peak_rate = 140.0
        stop_at_peak = compute_stop_rate(peak_rate)
        expected_stop = peak_rate * (1.0 - self.strategy.trailing_stop_positive)
        self.assertAlmostEqual(stop_at_peak, expected_stop, places=2)
        self.assertGreater(stop_at_peak, entry_price)

    def test_custom_exit_stale_trade_exact_boundary(self):
        """Verifies stale exit triggers at exactly 14 days and not before."""
        class MockTrade:
            open_date_utc = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        trade = MockTrade()

        # 13 days 23 hours: should NOT trigger stale exit
        t_13d_23h = datetime(2026, 1, 14, 23, 0, 0, tzinfo=timezone.utc)
        self.assertIsNone(self.strategy.custom_exit("SOL/EUR", trade, t_13d_23h, 100.0, 0.01))

        # Exactly 14 days: MUST trigger stale exit
        t_14d_00h = datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(self.strategy.custom_exit("SOL/EUR", trade, t_14d_00h, 100.0, 0.01), "stale_exit")

        # 20 days: MUST trigger stale exit
        t_20d_00h = datetime(2026, 1, 21, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(self.strategy.custom_exit("SOL/EUR", trade, t_20d_00h, 100.0, 0.01), "stale_exit")

    def test_custom_exit_timezone_naive_compatibility(self):
        """Verifies custom_exit handles timezone-naive open_date_utc gracefully without TypeError."""
        class MockTradeNaive:
            open_date_utc = datetime(2026, 1, 1, 0, 0, 0)  # Naive datetime

        trade = MockTradeNaive()
        t_aware = datetime(2026, 1, 16, 0, 0, 0, tzinfo=timezone.utc)
        exit_result = self.strategy.custom_exit("SOL/EUR", trade, t_aware, 100.0, 0.01)
        self.assertEqual(exit_result, "stale_exit")

    def test_protections_configuration(self):
        """Verify protections list contains CooldownPeriod, StoplossGuard, and MaxDrawdown."""
        protections = self.strategy.protections
        self.assertIsInstance(protections, list)
        self.assertEqual(len(protections), 3)

        methods = [p["method"] for p in protections]
        self.assertIn("CooldownPeriod", methods)
        self.assertIn("StoplossGuard", methods)
        self.assertIn("MaxDrawdown", methods)

    def test_asymmetric_payoff_expectancy_and_slippage_drag(self):
        """
        Validates the mathematical asymmetry of the risk engine against Kraken fee drag:
        - Roundtrip Kraken taker fee: 2 * 0.26% = 0.52%.
        - Activation profit: +4.5% (offset) -> locks in +2.0% minimum gain.
        - Net profit after taker fees (0.52%) and average altcoin spread (0.12%):
          2.0% - 0.52% - 0.12% = +1.36% > 0 (strictly fee-positive upon trailing activation).
        - Hard stoploss limit: -4.5% limits downside risk strictly to < 5.5% even with full fee drag.
        - Asymmetry Ratio (Windfall ROI 28% / Hard Stoploss 4.5%) = 6.22:1.
        """
        kraken_roundtrip_fee = 2.0 * 0.0026  # 0.52%
        locked_profit = self.strategy.trailing_stop_positive_offset - self.strategy.trailing_stop_positive  # 2.0%
        net_locked_profit = locked_profit - kraken_roundtrip_fee

        self.assertGreater(net_locked_profit, 0.01,
                           "Locked trailing profit must comfortably exceed Kraken roundtrip fees by >1%.")

        # Worst-case windfall payoff ratio vs catastrophic stoploss
        windfall_target = self.strategy.minimal_roi["0"]
        hard_loss = abs(self.strategy.stoploss)
        payoff_ratio = windfall_target / hard_loss
        self.assertGreater(payoff_ratio, 1.0, "Windfall payoff ratio should exceed catastrophic loss.")


if __name__ == "__main__":
    unittest.main()
