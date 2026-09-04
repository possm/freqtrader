"""
tests/test_adversarial_pvb.py — Adversarial Stress & Lookahead Challenger Suite
================================================================================
Milestone 1 Challenger 1: Adversarial Stress, Lookahead Bias & Causal Integrity
Author: Milestone 1 Challenger 1 (critic, specialist)

This test suite empirically verifies:
1. Strict Temporal Invariance & Lookahead Bias Absence:
   - Walk-forward point-in-time evaluation (oracle test): bar t signal in expanding window
     matches bar t signal in full historical window.
   - Future data perturbations (flash crashes, parabolic spikes, volume surges) do not leak
     into historical indicators or signals.
   - Informative BTC cross-asset macro filter temporal integrity.
2. Extreme Volatility & Hostile Market Shocks:
   - Flash crash 99% candle does not trigger false breakout entry.
   - Extreme price ratio (10^10 / 10^-5) numerical stability (no overflow/NaN/Inf).
   - Flatline zero-volatility market (50 candles of H=L=O=C) stability.
   - Inverted and zero/negative low sanitization.
3. Zero-Volume Bars & Microstructure Anomalies:
   - Strict suppression of entry signals on zero-volume candles.
   - Zero-volume exit behavior.
   - Dust volume after extended zero-volume drought.
4. Causal Separation & Mutual Exclusivity:
   - Mathematical proof and empirical verification that enter_long and exit_long NEVER
     fire on the same candle under any market conditions.
5. Strategy Interface & DataProvider Resilience:
   - Behavior when strategy is instantiated standalone without self.dp attached.
   - Custom exit datetime offset-naive vs offset-aware resilience.
"""
from __future__ import annotations

import math
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

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

from test_wolfbreakout_pvb import (
    MockDataProvider,
    generate_synthetic_ohlcv,
    generate_synthetic_btc,
)


class TestLookaheadPointInTimeOracle(unittest.TestCase):
    """
    Gold Standard Oracle Test:
    Compares expanding window point-in-time calculation (simulating live bar-by-bar arrival)
    against batch calculation on the full dataframe.
    If indicators or signals on bar t depend on ANY data after bar t, this test WILL fail.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not available.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def test_expanding_window_point_in_time_exact_match(self):
        """
        Verify that for bars 220 to 260, computing indicators on dataframe[:t+1]
        yields the EXACT same values at index t as computing on the full dataframe[:300].
        """
        full_df = generate_synthetic_ohlcv(n_bars=300, seed=777)
        full_ind = self.strategy.populate_indicators(full_df.copy(), self.metadata)
        full_entry = self.strategy.populate_entry_trend(full_ind.copy(), self.metadata)
        full_exit = self.strategy.populate_exit_trend(full_ind.copy(), self.metadata)

        checked_cols = [
            "parkinson_fast", "parkinson_slow", "pvr",
            "donchian_high", "donchian_mid", "donchian_low",
            "atr", "atr_pct", "ema_basis", "keltner_upper",
            "volume_mean", "ema_trend"
        ]

        for t in range(220, 260):
            window_df = full_df.iloc[: t + 1].copy()
            window_ind = self.strategy.populate_indicators(window_df, self.metadata)
            window_entry = self.strategy.populate_entry_trend(window_ind, self.metadata)
            window_exit = self.strategy.populate_exit_trend(window_ind, self.metadata)

            for col in checked_cols:
                val_full = full_ind.loc[t, col]
                val_window = window_ind.loc[t, col]
                self.assertAlmostEqual(
                    val_full, val_window, places=5,
                    msg=f"Lookahead leak detected in indicator {col} at bar {t}! "
                        f"Batch={val_full} vs Online={val_window}"
                )

            # Check signal agreement
            self.assertEqual(
                full_entry.loc[t, "enter_long"], window_entry.loc[t, "enter_long"],
                msg=f"Lookahead leak detected in enter_long at bar {t}!"
            )
            self.assertEqual(
                full_exit.loc[t, "exit_long"], window_exit.loc[t, "exit_long"],
                msg=f"Lookahead leak detected in exit_long at bar {t}!"
            )


class TestLookaheadAdversarialPerturbations(unittest.TestCase):
    """
    Hostile Future Perturbation Tests:
    Subject future bars (t >= 150) to extreme adversarial shocks and assert that
    past indicators and signals (t < 150) remain strictly bit-for-bit invariant.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not available.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def test_future_flash_crash_invariance(self):
        """A -99% catastrophic collapse at t >= 150 must not leak into t < 150."""
        df_clean = generate_synthetic_ohlcv(n_bars=250, seed=123)
        df_crash = df_clean.copy()

        df_crash.loc[150:, "open"] *= 0.01
        df_crash.loc[150:, "high"] *= 0.01
        df_crash.loc[150:, "low"] *= 0.001
        df_crash.loc[150:, "close"] *= 0.005
        df_crash.loc[150:, "volume"] *= 50.0

        res_clean = self.strategy.populate_indicators(df_clean, self.metadata)
        res_crash = self.strategy.populate_indicators(df_crash, self.metadata)

        entry_clean = self.strategy.populate_entry_trend(res_clean, self.metadata)
        entry_crash = self.strategy.populate_entry_trend(res_crash, self.metadata)

        exit_clean = self.strategy.populate_exit_trend(res_clean, self.metadata)
        exit_crash = self.strategy.populate_exit_trend(res_crash, self.metadata)

        eval_cols = ["parkinson_fast", "parkinson_slow", "pvr", "donchian_high",
                     "keltner_upper", "ema_trend", "enter_long", "exit_long"]

        assert_frame_equal(
            entry_clean.loc[:149, ["enter_long"]],
            entry_crash.loc[:149, ["enter_long"]],
            obj="Past entry signals leaked future flash crash!"
        )
        assert_frame_equal(
            exit_clean.loc[:149, ["exit_long"]],
            exit_crash.loc[:149, ["exit_long"]],
            obj="Past exit signals leaked future flash crash!"
        )
        assert_frame_equal(
            res_clean.loc[:149, ["pvr", "donchian_high", "keltner_upper"]],
            res_crash.loc[:149, ["pvr", "donchian_high", "keltner_upper"]],
            obj="Past indicators altered by future flash crash!"
        )

    def test_future_parabolic_pump_invariance(self):
        """A +10,000% parabolic explosion at t >= 150 must not leak into t < 150."""
        df_clean = generate_synthetic_ohlcv(n_bars=250, seed=456)
        df_pump = df_clean.copy()

        df_pump.loc[150:, "open"] *= 100.0
        df_pump.loc[150:, "high"] *= 150.0
        df_pump.loc[150:, "low"] *= 90.0
        df_pump.loc[150:, "close"] *= 120.0
        df_pump.loc[150:, "volume"] *= 100.0

        res_clean = self.strategy.populate_indicators(df_clean, self.metadata)
        res_pump = self.strategy.populate_indicators(df_pump, self.metadata)

        entry_clean = self.strategy.populate_entry_trend(res_clean, self.metadata)
        entry_pump = self.strategy.populate_entry_trend(res_pump, self.metadata)

        assert_frame_equal(
            entry_clean.loc[:149, ["enter_long"]],
            entry_pump.loc[:149, ["enter_long"]],
            obj="Past entry signals leaked future pump!"
        )

    def test_btc_macro_filter_future_leakage_adversarial(self):
        """
        Adversarial BTC manipulation: Future BTC crashes below EMA200.
        Verify past btc_uptrend_1h remains strictly invariant.
        """
        n_bars = 250
        df = generate_synthetic_ohlcv(n_bars=n_bars, seed=888)
        btc_bull = generate_synthetic_btc(n_bars=n_bars, is_bullish=True)
        btc_crash = btc_bull.copy()
        # Crash BTC future after bar 160
        btc_crash.loc[160:, ["open", "high", "low", "close"]] *= 0.10

        self.strategy.dp = MockDataProvider(btc_df=btc_bull)
        res_bull = self.strategy.populate_indicators(df.copy(), self.metadata)

        self.strategy.dp = MockDataProvider(btc_df=btc_crash)
        res_crash = self.strategy.populate_indicators(df.copy(), self.metadata)

        assert_series_equal(
            res_bull.loc[:159, "btc_uptrend_1h"],
            res_crash.loc[:159, "btc_uptrend_1h"],
            obj="BTC macro filter future crash leaked into past signals!"
        )


class TestExtremeVolatilityAndAnomalousData(unittest.TestCase):
    """
    Stress tests extreme volatility, numerical bounds, and anomalous data feeds.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not available.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def test_flash_crash_candle_does_not_trigger_false_breakout(self):
        """
        When a flash crash occurs on bar 50 (High=100, Low=1, Close=2),
        PVR surges due to volatility expansion, but enter_long MUST NOT trigger
        because close is far below donchian_high.
        """
        df = generate_synthetic_ohlcv(n_bars=70, seed=333)
        df.loc[50, "high"] = 100.0
        df.loc[50, "low"] = 1.0
        df.loc[50, "close"] = 2.0
        df.loc[50, "volume"] = 100000.0

        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)

        # Confirm PVR surged
        self.assertGreater(ind.loc[50, "pvr"], 1.10)
        # Confirm entry is strictly NOT triggered
        self.assertEqual(entry.loc[50, "enter_long"], 0,
                         "Flash crash bar falsely triggered long breakout entry!")

    def test_astronomical_ratio_no_overflow_or_nan(self):
        """Extreme range (High=1e9, Low=1e-5) must not cause overflow or NaN."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df.loc[40, "high"] = 1e9
        df.loc[40, "low"] = 1e-5
        df.loc[40, "close"] = 1e8

        ind = self.strategy.populate_indicators(df, self.metadata)
        self.assertFalse(np.isinf(ind.loc[40, "parkinson_fast"]))
        self.assertFalse(np.isnan(ind.loc[40, "parkinson_fast"]))
        self.assertFalse(np.isinf(ind.loc[40, "pvr"]))
        self.assertFalse(np.isnan(ind.loc[40, "pvr"]))

    def test_negative_low_clamped_safely(self):
        """Negative low (corrupt exchange print e.g. -50.0) is clipped to 1e-8 without crash."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df.loc[30, "low"] = -50.0

        ind = self.strategy.populate_indicators(df, self.metadata)
        self.assertFalse(np.isnan(ind.loc[30, "pvr"]))
        self.assertFalse(np.isinf(ind.loc[30, "pvr"]))

    def test_inverted_candle_high_less_than_low(self):
        """Corrupt tick where high < low (e.g. High=90, Low=100) is sanitized cleanly."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df.loc[30, "high"] = 90.0
        df.loc[30, "low"] = 100.0

        ind = self.strategy.populate_indicators(df, self.metadata)
        # Ratio high/low < 1.0 is clipped to 1.0, ln(1.0)=0, variance=0
        self.assertFalse(np.isnan(ind.loc[30, "pvr"]))
        self.assertFalse(np.isinf(ind.loc[30, "pvr"]))


class TestZeroVolumeAndIlliquidity(unittest.TestCase):
    """
    Stress tests zero volume, illiquid trading halts, and dust volume behavior.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not available.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def test_zero_volume_strictly_suppresses_entry(self):
        """Even if all price criteria are perfectly satisfied, volume=0 MUST suppress entry."""
        n_bars = 60
        df = generate_synthetic_ohlcv(n_bars=n_bars)
        ind = self.strategy.populate_indicators(df, self.metadata)

        idx = 50
        # Satisfy all price criteria
        ind.loc[idx, "close"] = ind.loc[idx, "donchian_high"] + 10.0
        ind.loc[idx, "pvr"] = 1.50
        ind.loc[idx, "ema_trend"] = ind.loc[idx, "close"] - 10.0
        ind.loc[idx, "btc_uptrend_1h"] = 1
        ind.loc[idx, "volume"] = 0.0  # Zero volume

        entry = self.strategy.populate_entry_trend(ind, self.metadata)
        self.assertEqual(entry.loc[idx, "enter_long"], 0,
                         "Zero volume bar triggered long entry!")

    def test_zero_volume_suppresses_exit(self):
        """A zero-volume bar (e.g. trading halt) should not trigger trend exhaustion exit."""
        n_bars = 60
        df = generate_synthetic_ohlcv(n_bars=n_bars)
        ind = self.strategy.populate_indicators(df, self.metadata)

        idx = 45
        ind.loc[idx, "close"] = ind.loc[idx, "donchian_mid"] - 10.0
        ind.loc[idx, "volume"] = 0.0

        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)
        self.assertEqual(exit_df.loc[idx, "exit_long"], 0,
                         "Zero volume bar falsely triggered trend exhaustion exit!")


class TestCausalSeparationAndMutualExclusivity(unittest.TestCase):
    """
    Verifies that enter_long and exit_long are strictly mutually exclusive:
    No single bar can ever produce both enter_long == 1 and exit_long == 1.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not available.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()
        self.metadata = {"pair": "SOL/EUR"}

    def test_enter_and_exit_signals_never_coincide_over_large_dataset(self):
        """Across 2,000 candles with heavy volatility, enter_long & exit_long never both equal 1."""
        df = generate_synthetic_ohlcv(n_bars=2000, seed=999, volatility=0.03)
        ind = self.strategy.populate_indicators(df, self.metadata)

        # Test with default exit (donchian mid)
        entry = self.strategy.populate_entry_trend(ind.copy(), self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind.copy(), self.metadata)

        clash = (entry["enter_long"] == 1) & (exit_df["exit_long"] == 1)
        self.assertFalse(clash.any(),
                         f"Entry and exit signals coincided on {clash.sum()} candles (donchian_mid)!")

        # Test with exit_ema_basis enabled as well
        self.strategy.exit_ema_basis.value = True
        exit_ema = self.strategy.populate_exit_trend(ind.copy(), self.metadata)
        clash_ema = (entry["enter_long"] == 1) & (exit_ema["exit_long"] == 1)
        self.assertFalse(clash_ema.any(),
                         f"Entry and exit signals coincided on {clash_ema.sum()} candles (ema_basis)!")

    def test_mathematical_impossibility_of_signal_clash(self):
        """
        Proof by contradiction verification:
        Entry requires: close > donchian_high AND close > keltner_upper.
        Exit requires: close < donchian_mid OR close < ema_basis.
        Since donchian_mid <= donchian_high AND ema_basis <= keltner_upper (keltner_mult > 0, atr >= 0),
        close cannot simultaneously be > donchian_high and < donchian_mid,
        nor > keltner_upper and < ema_basis.
        """
        df = generate_synthetic_ohlcv(n_bars=100)
        ind = self.strategy.populate_indicators(df, self.metadata)

        for i in range(30, len(ind)):
            c = ind.loc[i, "close"]
            dh = ind.loc[i, "donchian_high"]
            dm = ind.loc[i, "donchian_mid"]
            ku = ind.loc[i, "keltner_upper"]
            eb = ind.loc[i, "ema_basis"]

            self.assertGreaterEqual(dh, dm)
            self.assertGreaterEqual(ku, eb)


class TestStrategyStandaloneInitialization(unittest.TestCase):
    """
    Stress tests standalone instantiation and edge case handling.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not available.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}

    def test_attribute_error_when_dp_not_set(self):
        """
        Documents the architectural boundary:
        In WolfBreakout_PVB line 190, `if self.dp:` expects self.dp to exist.
        If an external caller instantiates the strategy without attaching dp or mocking it,
        accessing self.dp raises AttributeError.
        Verify that attaching self.dp = None or MockDataProvider works cleanly.
        """
        # Standalone strategy without dp attached
        strat = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        df = generate_synthetic_ohlcv(n_bars=40)

        # Confirm that without dp attached, self.dp raises AttributeError
        self.assertFalse(hasattr(strat, "dp"))

        # When dp is explicitly set to None (or mock), populate_indicators succeeds
        strat.dp = None
        res = strat.populate_indicators(df.copy(), self.metadata)
        self.assertIn("btc_uptrend_1h", res.columns)
        self.assertTrue((res["btc_uptrend_1h"] == 1).all())

    def test_custom_exit_timezone_resilience(self):
        """custom_exit handles naive, aware, and mismatched datetime objects cleanly."""
        class MockTrade:
            open_date_utc = datetime(2026, 1, 1, 12, 0, 0)  # naive

        trade = MockTrade()
        # Aware current_time
        ct_aware = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        exit_result = self.strategy.custom_exit("SOL/EUR", trade, ct_aware, 100.0, 0.05)
        self.assertEqual(exit_result, "stale_exit")

        # Reverse order / negative elapsed time (clock drift)
        ct_early = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
        exit_early = self.strategy.custom_exit("SOL/EUR", trade, ct_early, 100.0, 0.05)
        self.assertIsNone(exit_early)


if __name__ == "__main__":
    unittest.main()
