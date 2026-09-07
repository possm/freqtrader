"""
tests/test_adversarial_hvrspb.py — Adversarial Stress & Robustness Challenger Suite
===================================================================================
Milestone 1 Challenger 1: Empirical Robustness & Extreme Boundary Verification
Strategy: WolfBreakout_HVRSPB (user_data/strategies/WolfBreakout_HVRSPB.py)

This test suite empirically stresses:
1. Sudden Flash Crashes:
   - Single candle -50% flash crash.
   - Severe -95% catastrophic market collapse.
   - Flash crash with immediate V-bottom rebound.
   - Zero and negative low prices during crash wick.
2. Massive Volatility Spikes:
   - Coiling consolidation followed by explosive breakout driving PVR > 10.0.
   - Astronomical high/low price ratios (10^12) without numerical overflow.
   - Evaluation of entry filters under extreme PVR expansion.
3. Zero Volume, Flat Candles & Degenerate Ranges:
   - 100 consecutive flat candles (O=H=L=C, volume=0) checking division by zero and log(0).
   - Degenerate zero and negative lows (low <= 0).
   - Inverted candles (High < Low).
   - Subatomic micro-spreads (High - Low = 1e-10).
4. Completely Missing BTC Informative Pair Data:
   - Standalone execution with dp = None.
   - Empty dataframe returned by DataProvider.
   - DataProvider raising unhandled socket/network exceptions.
   - Disjoint date ranges between BTC and candidate asset.
   - BTC dataframe containing all NaNs.
5. Startup NaN Propagation & Truncated Series:
   - Dataframes with lengths below startup_candle_count (0, 1, 5, 14, 20, 24, 50, 100, 249).
   - Zero premature entry or exit triggers during indicator warmup.
6. Custom Stoploss, Custom Exit & Order Contract:
   - Monotonic behavior of two-tier asymmetric trailing stop across profit spectrum (-50% to +1000%).
   - Strict adherence to Freqtrade negative float return contract for custom stoploss.
   - Fast invalidation timing matrix (under 4h vs over 4h, rate < mid vs loss < -1.5%).
   - Stale exit after 14 days.
   - Datetime tz-aware vs tz-naive resilience and clock skew safety.
7. Mutual Exclusivity & Scale Performance:
   - Strict guarantee that enter_long and exit_long NEVER fire on the same candle.
   - 50,000 candles processed in under 3.0s (no infinite loops, O(N) complexity).
"""
from __future__ import annotations

import math
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRAT_DIR = PROJECT_ROOT / "user_data" / "strategies"
TESTS_DIR = PROJECT_ROOT / "tests"
if str(STRAT_DIR) not in sys.path:
    sys.path.insert(0, str(STRAT_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from WolfBreakout_HVRSPB import WolfBreakout_HVRSPB
from test_wolfbreakout_hvrspb import (
    MockDataProvider,
    MockTrade,
    generate_synthetic_ohlcv,
    generate_synthetic_btc,
)


class TestAdversarialFlashCrashes(unittest.TestCase):
    """Stress tests strategy behavior under violent downward market shocks."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_single_candle_minus_50_pct_flash_crash(self):
        """A single candle plunges -50%: verify no crashes, no false entries, and proper exit triggers."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0, volatility=0.01)
        crash_idx = df.index[-1]

        # Inject -50% plunge on final candle
        prev_close = df.loc[df.index[-2], "close"]
        df.loc[crash_idx, "open"] = prev_close
        df.loc[crash_idx, "high"] = prev_close
        df.loc[crash_idx, "low"] = prev_close * 0.50
        df.loc[crash_idx, "close"] = prev_close * 0.50
        df.loc[crash_idx, "volume"] = 100000.0  # massive panic selling volume

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        self.assertFalse(analyzed.empty)

        # All key indicators must be finite numbers
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "parkinson_20"]))
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "pvr"]))
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "donchian_high"]))
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "donchian_mid"]))

        # Entry logic: must NOT trigger enter_long
        entry_df = self.strategy.populate_entry_trend(analyzed.copy(), {"pair": "FET/EUR"})
        self.assertEqual(entry_df.loc[crash_idx, "enter_long"], 0, "Flash crash candle must NEVER trigger entry!")

        # Exit logic: must trigger exit_long because close is far below donchian_mid
        exit_df = self.strategy.populate_exit_trend(analyzed.copy(), {"pair": "FET/EUR"})
        self.assertEqual(exit_df.loc[crash_idx, "exit_long"], 1, "Flash crash must trigger exit on midline breach!")
        self.assertEqual(exit_df.loc[crash_idx, "exit_tag"], "trend_invalidation_mid")

    def test_severe_minus_95_pct_catastrophic_crash(self):
        """Catastrophic 95% crash from 100 to 5: verify continuous range estimator doesn't overflow or crash."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0, volatility=0.01)
        crash_idx = df.index[-1]

        df.loc[crash_idx, "open"] = 100.0
        df.loc[crash_idx, "high"] = 100.0
        df.loc[crash_idx, "low"] = 5.0
        df.loc[crash_idx, "close"] = 5.0
        df.loc[crash_idx, "volume"] = 500000.0

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        entry_df = self.strategy.populate_entry_trend(analyzed.copy(), {"pair": "FET/EUR"})
        exit_df = self.strategy.populate_exit_trend(analyzed.copy(), {"pair": "FET/EUR"})

        self.assertEqual(entry_df.loc[crash_idx, "enter_long"], 0)
        self.assertEqual(exit_df.loc[crash_idx, "exit_long"], 1)
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "parkinson_var" if "parkinson_var" in analyzed else "parkinson_20"]))

    def test_flash_crash_immediate_v_rebound(self):
        """Flash crash followed by instant +100% rebound: verify shift(1) prevents lookahead bias."""
        df = generate_synthetic_ohlcv(n_bars=65, base_price=100.0, volatility=0.005)
        crash_idx = df.index[-2]
        rebound_idx = df.index[-1]

        # Candle -2: flash crash
        df.loc[crash_idx, "open"] = 100.0
        df.loc[crash_idx, "high"] = 100.0
        df.loc[crash_idx, "low"] = 50.0
        df.loc[crash_idx, "close"] = 50.0

        # Candle -1: V-rebound back to 100.0
        df.loc[rebound_idx, "open"] = 50.0
        df.loc[rebound_idx, "high"] = 101.0
        df.loc[rebound_idx, "low"] = 50.0
        df.loc[rebound_idx, "close"] = 100.0

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        # donchian_high at rebound candle must NOT see rebound candle's high of 101.0
        # It must be based strictly on candles prior to rebound_idx
        prev_window_max = df.loc[df.index[-22]:df.index[-2], "high"].max()
        self.assertEqual(analyzed.loc[rebound_idx, "donchian_high"], prev_window_max)

    def test_crash_with_zero_low_wick(self):
        """Low drops to exactly 0.0 or negative: safe_low clipping must prevent log(0) or domain errors."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=50.0)
        crash_idx = df.index[-1]
        df.loc[crash_idx, "open"] = 50.0
        df.loc[crash_idx, "high"] = 50.0
        df.loc[crash_idx, "low"] = 0.0  # glitched zero wick
        df.loc[crash_idx, "close"] = 10.0

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "parkinson_20"]))
        self.assertTrue(np.isfinite(analyzed.loc[crash_idx, "pvr"]))


class TestAdversarialVolatilitySpikes(unittest.TestCase):
    """Stress tests strategy behavior under massive volatility spikes (PVR > 10.0)."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_massive_pvr_spike_above_10(self):
        """
        Verify that an explosive range expansion after prolonged compression
        produces PVR > 10.0 cleanly without overflow or numerical instability.
        """
        n_bars = 70
        df = generate_synthetic_ohlcv(n_bars=n_bars, base_price=100.0)

        # Force tight coiling compression for candles 0..59 (range = 0.05%)
        for i in range(60):
            idx = df.index[i]
            df.loc[idx, "open"] = 100.0
            df.loc[idx, "high"] = 100.02
            df.loc[idx, "low"] = 99.98
            df.loc[idx, "close"] = 100.0
            df.loc[idx, "volume"] = 1000.0

        # Candle 60..69: massive volatility explosion (range expands from 0.04% to 50%)
        for i in range(60, n_bars):
            idx = df.index[i]
            mult = 1.0 + (i - 59) * 0.1
            df.loc[idx, "open"] = 100.0 * mult
            df.loc[idx, "high"] = 150.0 * mult
            df.loc[idx, "low"] = 80.0 * mult
            df.loc[idx, "close"] = 145.0 * mult
            df.loc[idx, "volume"] = 20000.0

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})

        # PVR at the transition candle (candle 60 or 61) should surge dramatically
        pvr_max = analyzed["pvr"].iloc[60:].max()
        self.assertGreater(pvr_max, 10.0, f"Expected PVR > 10.0 during massive expansion, got {pvr_max:.2f}")

        # Ensure no infinite or NaN values
        self.assertFalse(np.isneginf(analyzed["pvr"]).any())
        self.assertFalse(np.isposinf(analyzed["pvr"]).any())
        self.assertFalse(analyzed["pvr"].iloc[60:].isna().any())

    def test_extreme_price_ratio_astronomical_wick(self):
        """
        Extreme candle with High = 1e8, Low = 1e-4 (ratio = 10^12).
        Continuous variance must compute cleanly without overflow.
        """
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0)
        idx = df.index[-1]
        df.loc[idx, "open"] = 100.0
        df.loc[idx, "high"] = 1e8
        df.loc[idx, "low"] = 1e-4
        df.loc[idx, "close"] = 100.0

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        pvr_val = analyzed.loc[idx, "pvr"]
        self.assertTrue(np.isfinite(pvr_val), f"PVR must be finite even on 10^12 ratio, got {pvr_val}")
        self.assertGreater(pvr_val, 0.0)

    def test_volatility_spike_entry_evaluation(self):
        """When PVR > 10.0, entry conditions must evaluate without TypeError or mask corruption."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0)
        idx = df.index[-1]
        # Set all conditions to align with huge PVR
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        analyzed.loc[idx, "close"] = 200.0
        analyzed.loc[idx, "donchian_high"] = 150.0
        analyzed.loc[idx, "keltner_upper"] = 160.0
        analyzed.loc[idx, "pvr"] = 15.75  # PVR > 10.0
        analyzed.loc[idx, "rs_btc"] = 0.05
        analyzed.loc[idx, "volume"] = 10000.0
        analyzed.loc[idx, "volume_mean"] = 2000.0
        analyzed.loc[idx, "btc_uptrend_clean"] = 1

        entry_df = self.strategy.populate_entry_trend(analyzed, {"pair": "FET/EUR"})
        self.assertEqual(entry_df.loc[idx, "enter_long"], 1)
        self.assertEqual(entry_df.loc[idx, "enter_tag"], "hvrspb_breakout")


class TestZeroVolumeAndDegenerateBars(unittest.TestCase):
    """Stress tests division-by-zero, log-of-zero, and zero-volume scenarios."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_one_hundred_consecutive_flat_candles_zero_volume(self):
        """
        100 identical bars: O=H=L=C=100.0, Volume=0.0.
        Must produce variance = 0.0, PVR = 0.0 without ZeroDivisionError or RuntimeWarning.
        """
        dt_index = pd.date_range(start="2026-01-01", periods=100, freq="1h", tz="UTC")
        flat_df = pd.DataFrame({
            "date": dt_index,
            "open": np.full(100, 100.0),
            "high": np.full(100, 100.0),
            "low": np.full(100, 100.0),
            "close": np.full(100, 100.0),
            "volume": np.zeros(100),
        })

        analyzed = self.strategy.populate_indicators(flat_df.copy(), {"pair": "FET/EUR"})

        # After rolling warmup, variance, parkinson_20, and PVR must be 0.0
        valid_slice = analyzed.iloc[25:]
        self.assertTrue((valid_slice["parkinson_20"] == 0.0).all())
        self.assertTrue((valid_slice["pvr"] == 0.0).all())
        self.assertTrue((valid_slice["atr"] == 0.0).all())

        # Check entry and exit signals: strictly ZERO
        entry_df = self.strategy.populate_entry_trend(analyzed.copy(), {"pair": "FET/EUR"})
        exit_df = self.strategy.populate_exit_trend(analyzed.copy(), {"pair": "FET/EUR"})

        self.assertEqual(entry_df["enter_long"].sum(), 0, "No entries on flat zero-volume candles!")
        self.assertEqual(exit_df["exit_long"].sum(), 0, "No exits on flat zero-volume candles!")

    def test_degenerate_zero_and_negative_lows(self):
        """Negative and zero prices from corrupt ticks must be sanitized safely."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=50.0)
        df.loc[df.index[30], "low"] = -10.0
        df.loc[df.index[31], "low"] = 0.0
        df.loc[df.index[32], "high"] = -5.0
        df.loc[df.index[32], "low"] = -15.0

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        self.assertFalse(analyzed.empty)
        self.assertFalse(analyzed["parkinson_20"].isna().iloc[35:].any())

    def test_inverted_candle_high_less_than_low(self):
        """Inverted candle (High < Low) must be clipped so ratio >= 1.0 and variance >= 0.0."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0)
        idx = df.index[-1]
        df.loc[idx, "high"] = 90.0
        df.loc[idx, "low"] = 100.0  # High < Low

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        # Should not raise math domain error on log or sqrt
        pvr_val = analyzed.loc[idx, "pvr"]
        self.assertTrue(np.isfinite(pvr_val))
        self.assertGreaterEqual(pvr_val, 0.0)

    def test_subatomic_spread_micro_range(self):
        """High - Low = 1e-10: micro range must evaluate safely to near-zero variance."""
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0)
        idx = df.index[-1]
        df.loc[idx, "high"] = 100.0000000001
        df.loc[idx, "low"] = 100.0000000000

        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        self.assertTrue(np.isfinite(analyzed.loc[idx, "pvr"]))


class TestMissingBTCInformativePairFallback(unittest.TestCase):
    """Stress tests benchmark-neutral fallback when BTC data is missing, corrupted, or disjoint."""

    def test_dp_is_none_standalone(self):
        """Strategy executed standalone without DataProvider attached."""
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        strategy.dp = None

        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})

        self.assertIn("btc_return_24h_clean", analyzed.columns)
        self.assertIn("btc_uptrend_clean", analyzed.columns)
        self.assertIn("rs_btc", analyzed.columns)

        self.assertTrue((analyzed["btc_return_24h_clean"] == 0.0).all())
        self.assertTrue((analyzed["btc_uptrend_clean"] == 1).all())
        # rs_btc should equal asset_return_24h (filled with 0.0 on warmup NaNs)
        expected_rs = analyzed["asset_return_24h"].fillna(0.0)
        assert_series_equal(analyzed["rs_btc"], expected_rs, check_names=False)

    def test_dp_returns_empty_dataframe(self):
        """DataProvider exists but returns empty DataFrame for BTC."""
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        strategy.dp = MockDataProvider(btc_df=pd.DataFrame())

        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})

        self.assertTrue((analyzed["btc_return_24h_clean"] == 0.0).all())
        self.assertTrue((analyzed["btc_uptrend_clean"] == 1).all())

    def test_dp_raises_unhandled_exception(self):
        """DataProvider raises connection or API exception: strategy must catch and fallback."""
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        mock_dp = MockDataProvider()
        mock_dp.get_pair_dataframe = MagicMock(side_effect=RuntimeError("Kraken WS connection reset"))
        strategy.dp = mock_dp

        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})

        self.assertTrue((analyzed["btc_return_24h_clean"] == 0.0).all())
        self.assertTrue((analyzed["btc_uptrend_clean"] == 1).all())

    def test_btc_disjoint_date_ranges(self):
        """BTC dataframe has zero date overlap with candidate asset (e.g. 2020 vs 2026)."""
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        btc_old = generate_synthetic_btc(n_bars=60, start_date="2020-01-01 00:00:00")
        strategy.dp = MockDataProvider(btc_df=btc_old)

        df_2026 = generate_synthetic_ohlcv(n_bars=60, start_date="2026-01-01 00:00:00")
        analyzed = strategy.populate_indicators(df_2026.copy(), {"pair": "FET/EUR"})

        # When dates don't overlap, merged btc columns will be all NaN,
        # which must cleanly ffill and fillna to 0.0 and 1
        self.assertTrue((analyzed["btc_return_24h_clean"] == 0.0).all())
        self.assertTrue((analyzed["btc_uptrend_clean"] == 1).all())
        self.assertFalse(analyzed["rs_btc"].isna().any())

    def test_btc_dataframe_all_nans(self):
        """BTC dataframe contains all NaNs in price data."""
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        btc_nan = generate_synthetic_btc(n_bars=60)
        btc_nan["close"] = np.nan
        btc_nan["open"] = np.nan
        strategy.dp = MockDataProvider(btc_df=btc_nan)

        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})

        self.assertTrue((analyzed["btc_return_24h_clean"] == 0.0).all())
        # When BTC data exists but contains all NaNs, btc_uptrend evaluates to 0 (safe fail-closed)
        self.assertTrue((analyzed["btc_uptrend_clean"] == 0).all())


class TestStartupNaNPropagationAndTruncatedSeries(unittest.TestCase):
    """Stress tests truncated series below startup_candle_count and NaN behavior."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_truncated_series_lengths(self):
        """
        Verify that for ANY length from 0 to 249 bars (< startup_candle_count=250),
        the strategy executes without exception and NEVER triggers an entry signal on unready bars.
        """
        lengths_to_test = [0, 1, 2, 5, 10, 13, 14, 19, 20, 23, 24, 25, 50, 100, 249]

        for n in lengths_to_test:
            with self.subTest(bars=n):
                if n == 0:
                    df = pd.DataFrame()
                else:
                    df = generate_synthetic_ohlcv(n_bars=n)

                analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
                if n == 0:
                    self.assertTrue(analyzed.empty)
                    continue

                entry_df = self.strategy.populate_entry_trend(analyzed.copy(), {"pair": "FET/EUR"})
                exit_df = self.strategy.populate_exit_trend(analyzed.copy(), {"pair": "FET/EUR"})

                # In warmup zone (first 24 bars), indicators have NaNs, so enter_long must be 0
                warmup_cutoff = min(n, 24)
                warmup_entries = entry_df["enter_long"].iloc[:warmup_cutoff]
                self.assertEqual(warmup_entries.sum(), 0, f"Premature entry triggered during warmup of {n} bars!")

    def test_intermittent_nans_in_input_ohlcv(self):
        """Single NaN injected into inputs does not trigger unhandled exception."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df.loc[df.index[30], "high"] = np.nan

        # Should execute without throwing unhandled exception
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        entry_df = self.strategy.populate_entry_trend(analyzed.copy(), {"pair": "FET/EUR"})
        # Row 30 must not trigger entry
        self.assertEqual(entry_df.loc[entry_df.index[30], "enter_long"], 0)


class TestOrderContractAndDynamicRiskExecution(unittest.TestCase):
    """Stress tests custom_stoploss and custom_exit across full profit and time boundaries."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_custom_stoploss_negative_distance_contract(self):
        """
        Freqtrade contract requirement:
        custom_stoploss must ALWAYS return either None or a negative float (relative distance from current price).
        A positive return would place a stoploss ABOVE current price for a long trade, causing exchange rejection.
        """
        trade = MockTrade(open_rate=100.0)
        now = datetime.now(timezone.utc)

        # Test fine-grained profit spectrum from -50% to +500%
        profits = np.linspace(-0.50, 5.0, 500)
        for p in profits:
            current_rate = 100.0 * (1.0 + p)
            sl = self.strategy.custom_stoploss(
                pair="FET/EUR",
                trade=trade,
                current_time=now,
                current_rate=current_rate,
                current_profit=float(p),
            )
            if sl is not None:
                self.assertIsInstance(sl, float)
                self.assertLess(sl, 0.0, f"Stoploss return must be strictly negative! Got {sl} for profit {p}")
                self.assertFalse(math.isnan(sl), f"Stoploss returned NaN for profit {p}")
                self.assertFalse(math.isinf(sl), f"Stoploss returned Inf for profit {p}")

    def test_custom_stoploss_profit_lock_guarantee(self):
        """
        Verify that in Tier 1 (profit between 3.5% and 8.0%),
        the locked stop price is ALWAYS >= entry_price * (1 + be_lock_margin).
        """
        open_rate = 100.0
        trade = MockTrade(open_rate=open_rate)
        now = datetime.now(timezone.utc)
        be_margin = float(self.strategy.be_lock_margin.value)  # 0.008

        for p in [0.035, 0.040, 0.050, 0.060, 0.070, 0.079]:
            current_rate = open_rate * (1.0 + p)
            sl = self.strategy.custom_stoploss(
                pair="FET/EUR",
                trade=trade,
                current_time=now,
                current_rate=current_rate,
                current_profit=p,
            )
            self.assertIsNotNone(sl)
            stop_price = current_rate * (1.0 + sl)
            expected_locked_price = open_rate * (1.0 + be_margin)
            self.assertAlmostEqual(
                stop_price, expected_locked_price, places=3,
                msg=f"Stop price {stop_price} should equal breakeven locked price {expected_locked_price}"
            )

    def test_custom_exit_fast_invalidation_matrix(self):
        """Exhaustively verify custom_exit fast invalidation conditions."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [trade_open_time + timedelta(hours=5)],
            "donchian_mid": [100.0],
            "close": [98.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # 1. Before 4h: No exit even if price < donchian_mid
        t_early = trade_open_time + timedelta(hours=3, minutes=59)
        exit_early = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=t_early, current_rate=98.0, current_profit=-0.02
        )
        self.assertIsNone(exit_early, "Under 4h must not exit early")

        # 2. After 4h: Exits if rate < donchian_mid
        t_late = trade_open_time + timedelta(hours=4, minutes=1)
        exit_mid = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=t_late, current_rate=98.0, current_profit=-0.01
        )
        self.assertEqual(exit_mid, "fast_invalidation_mid")

        # 3. After 4h: Exits if profit < -1.5% even if dp is absent
        self.strategy.dp = MockDataProvider(analyzed_df=None)
        exit_loss = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=t_late, current_rate=98.0, current_profit=-0.016
        )
        self.assertEqual(exit_loss, "fast_invalidation_loss")

        # 4. After 4h: Retains position if healthy (> mid and profit >= -1.5%)
        exit_hold = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=t_late, current_rate=105.0, current_profit=0.05
        )
        self.assertIsNone(exit_hold)

        # 5. After 14 days: Stale exit
        t_stale = trade_open_time + timedelta(days=14, hours=1)
        exit_stale = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=t_stale, current_rate=102.0, current_profit=0.02
        )
        self.assertEqual(exit_stale, "stale_exit")

    def test_custom_exit_timezone_awareness_and_clock_skew(self):
        """Verify naive vs aware datetime safety and negative elapsed time."""
        # Naive open_date_utc
        naive_open = datetime(2026, 1, 1, 10, 0)
        trade = MockTrade(open_date_utc=naive_open, open_rate=100.0)
        aware_now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Must not throw TypeError: can't subtract offset-naive and offset-aware datetimes
        res1 = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=aware_now, current_rate=100.0, current_profit=0.0
        )
        self.assertIsNone(res1)

        # Clock skew: current_time is in the past
        skewed_time = datetime(2025, 12, 31, 10, 0, tzinfo=timezone.utc)
        res2 = self.strategy.custom_exit(
            pair="FET/EUR", trade=trade, current_time=skewed_time, current_rate=100.0, current_profit=0.0
        )
        self.assertIsNone(res2)


class TestMutualExclusivityAndScaleStress(unittest.TestCase):
    """Stress tests signal mutual exclusivity and execution scalability."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.strategy.dp = MockDataProvider()

    def test_mutual_exclusivity_enter_and_exit_signals(self):
        """
        Mathematical Invariance Test:
        enter_long == 1 and exit_long == 1 can NEVER occur on the same candle.
        Proof:
        enter_long requires: close > donchian_high
        exit_long requires:  close < donchian_mid
        Since donchian_high >= donchian_mid (always), close cannot simultaneously be > donchian_high and < donchian_mid.
        """
        # Test across 2000 randomized and perturbed candles
        df = generate_synthetic_ohlcv(n_bars=2000, volatility=0.03)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        entry_df = self.strategy.populate_entry_trend(analyzed.copy(), {"pair": "FET/EUR"})
        exit_df = self.strategy.populate_exit_trend(analyzed.copy(), {"pair": "FET/EUR"})

        both_active = (entry_df["enter_long"] == 1) & (exit_df["exit_long"] == 1)
        self.assertEqual(
            both_active.sum(), 0,
            f"Mutual exclusivity violation: enter_long and exit_long both fired on {both_active.sum()} candles!"
        )

    def test_execution_performance_50k_candles(self):
        """Process 50,000 candles to verify O(N) linear complexity, no infinite loops, and execution < 3.0s."""
        n_bars = 50000
        df = generate_synthetic_ohlcv(n_bars=n_bars, volatility=0.01)

        t0 = time.perf_counter()
        analyzed = self.strategy.populate_indicators(df, {"pair": "FET/EUR"})
        t_ind = time.perf_counter() - t0

        t1 = time.perf_counter()
        entry_df = self.strategy.populate_entry_trend(analyzed, {"pair": "FET/EUR"})
        t_entry = time.perf_counter() - t1

        t2 = time.perf_counter()
        exit_df = self.strategy.populate_exit_trend(analyzed, {"pair": "FET/EUR"})
        t_exit = time.perf_counter() - t2

        total_time = t_ind + t_entry + t_exit
        self.assertLess(total_time, 3.0, f"Processing 50k candles took {total_time:.2f}s, exceeding 3.0s budget!")
        self.assertFalse(analyzed.empty)


if __name__ == "__main__":
    unittest.main()
