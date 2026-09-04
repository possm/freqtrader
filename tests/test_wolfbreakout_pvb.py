"""
tests/test_wolfbreakout_pvb.py — Rigorous Unit Test Suite for WolfBreakout_PVB Strategy
========================================================================================
Validates:
1. Parkinson (1980) Continuous Volatility Variance & Expansion Ratio (PVR)
2. Donchian & Keltner Channels (Strict .shift(1) lookahead bias prevention)
3. Lookahead Invariance (Perturbation of future bars does not affect past indicators/signals)
4. Entry Signal Matrix & Suppression (Combinatorial truth table for all 7 filters)
5. Exit Signal Generation (Donchian mid break, EMA basis break, stale exit)
6. Edge Cases & Data Hygiene (Startup NaNs, 50 flat candles, zero volume, missing BTC)
7. Freqtrade API Conformance (INTERFACE_VERSION 3, 1h timeframe, ROI monotonicity, Hyperopt)
8. Slippage Mixin Compatibility (atr_pct calculation for KrakenSlippageMixin)
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

# Add strategy directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRAT_DIR = PROJECT_ROOT / "user_data" / "strategies"
if str(STRAT_DIR) not in sys.path:
    sys.path.insert(0, str(STRAT_DIR))

try:
    from WolfBreakout_PVB import WolfBreakout_PVB
except ImportError:
    # Allow test file to be imported even if strategy implementation is pending
    WolfBreakout_PVB = None


# =============================================================================
# SYNTHETIC TEST FIXTURES & MOCK INFRASTRUCTURE
# =============================================================================

class MockDataProvider:
    """Mock Freqtrade DataProvider for isolating informative pairs."""

    def __init__(self, btc_df: pd.DataFrame | None = None, runmode: str = "backtest"):
        self.btc_df = btc_df
        self.runmode = runmode

    def get_pair_dataframe(self, pair: str, timeframe: str) -> pd.DataFrame:
        if "BTC" in pair and self.btc_df is not None:
            return self.btc_df.copy()
        return pd.DataFrame()

    def current_whitelist(self) -> list[str]:
        return ["ETH/EUR", "SOL/EUR", "BTC/EUR"]


def generate_synthetic_ohlcv(
    n_bars: int = 260,
    base_price: float = 100.0,
    volatility: float = 0.015,
    seed: int = 42,
    start_date: str = "2026-01-01 00:00:00"
) -> pd.DataFrame:
    """
    Generates a realistic, deterministic OHLCV DataFrame for testing.
    Guarantees: High >= max(Open, Close) and Low <= min(Open, Close).
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
    is_bullish: bool = True,
    start_date: str = "2026-01-01 00:00:00"
) -> pd.DataFrame:
    """Generates synthetic BTC informative pair data with guaranteed bullish/bearish state."""
    dt_index = pd.date_range(start=start_date, periods=n_bars, freq="1h", tz="UTC")
    if is_bullish:
        # Monotonically rising BTC ensures close > EMA200
        prices = np.linspace(base_price * 0.8, base_price * 1.2, n_bars)
    else:
        # Monotonically falling BTC ensures close < EMA200
        prices = np.linspace(base_price * 1.2, base_price * 0.8, n_bars)

    df = pd.DataFrame({
        "date": dt_index,
        "open": prices,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": np.full(n_bars, 1000.0),
    })
    return df


# =============================================================================
# UNIT TEST SUITE 1: PARKINSON VOLATILITY FORMULATION & EXPANSION
# =============================================================================

class TestParkinsonVolatility(unittest.TestCase):
    """Rigorous mathematical tests for the Parkinson (1980) variance estimator."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}

    def test_parkinson_variance_exact_closed_form(self):
        """
        Closed-form verification:
        When H/L = 2.0:
        sigma_P^2 = (ln(2))^2 / (4 * ln(2)) = ln(2) / 4 = 0.17328679513998632.
        sigma_P   = sqrt(ln(2) / 4)         = 0.4162773055788724.
        """
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=40, freq="1h", tz="UTC"),
            "open": np.full(40, 150.0),
            "high": np.full(40, 200.0),
            "low": np.full(40, 100.0),      # H/L = 2.0 exactly
            "close": np.full(40, 150.0),
            "volume": np.full(40, 1000.0),
        })
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        expected_var = math.log(2.0) / 4.0
        expected_sigma = math.sqrt(expected_var)

        # After fast window (10) and slow window (30) have warmed up
        actual_fast = res["parkinson_fast"].iloc[-1]
        actual_slow = res["parkinson_slow"].iloc[-1]

        self.assertAlmostEqual(actual_fast, expected_sigma, places=6,
                               msg="Parkinson fast sigma does not match analytical closed-form.")
        self.assertAlmostEqual(actual_slow, expected_sigma, places=6,
                               msg="Parkinson slow sigma does not match analytical closed-form.")
        # Under uniform constant variance, PVR = sigma_fast / sigma_slow == 1.0
        self.assertAlmostEqual(res["pvr"].iloc[-1], 1.0, places=4,
                               msg="Constant volatility must yield PVR = 1.0.")

    def test_parkinson_variance_hand_calculated_ratio_1_10(self):
        """
        Hand-calculated check:
        H = 110.0, L = 100.0 (H/L = 1.10).
        ln(1.10) = 0.0953101798
        (ln(1.10))^2 = 0.0090840304
        4 * ln(2) = 2.7725887222
        sigma_P^2 = 0.0032763714
        sigma_P = 0.0572395963
        """
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=40, freq="1h", tz="UTC"),
            "open": np.full(40, 105.0),
            "high": np.full(40, 110.0),
            "low": np.full(40, 100.0),
            "close": np.full(40, 105.0),
            "volume": np.full(40, 1000.0),
        })
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        expected_sigma = 0.0572395963
        self.assertAlmostEqual(res["parkinson_fast"].iloc[-1], expected_sigma, places=5)

    def test_parkinson_flat_candle_zero_variance(self):
        """Flat candle (H == L) must yield sigma_P^2 = 0.0 without ZeroDivisionError."""
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=40, freq="1h", tz="UTC"),
            "open": np.full(40, 100.0),
            "high": np.full(40, 100.0),
            "low": np.full(40, 100.0),      # H == L
            "close": np.full(40, 100.0),
            "volume": np.full(40, 1000.0),
        })
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        self.assertEqual(res["parkinson_fast"].iloc[-1], 0.0)
        self.assertEqual(res["parkinson_slow"].iloc[-1], 0.0)
        # PVR division by zero protection: 0 / (0 + 1e-9) = 0.0
        self.assertAlmostEqual(res["pvr"].iloc[-1], 0.0, places=5)
        self.assertFalse(np.isinf(res["pvr"].iloc[-1]))
        self.assertFalse(np.isnan(res["pvr"].iloc[-1]))

    def test_pvr_surges_during_volatility_expansion(self):
        """PVR must exceed 1.10 when low volatility is followed by high volatility."""
        # 30 bars of calm volatility (H/L = 1.01), then 10 bars of explosive volatility (H/L = 1.20)
        calm_bars = 30
        surge_bars = 10
        total = calm_bars + surge_bars

        highs = np.concatenate([np.full(calm_bars, 101.0), np.full(surge_bars, 120.0)])
        lows = np.concatenate([np.full(calm_bars, 100.0), np.full(surge_bars, 100.0)])
        closes = np.concatenate([np.full(calm_bars, 100.5), np.full(surge_bars, 118.0)])

        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=total, freq="1h", tz="UTC"),
            "open": np.full(total, 100.0),
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(total, 1000.0),
        })
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        last_pvr = res["pvr"].iloc[-1]
        self.assertGreater(last_pvr, 1.20,
                           f"PVR ({last_pvr}) should surge well above 1.20 after explosive range expansion.")


# =============================================================================
# UNIT TEST SUITE 2: DONCHIAN & KELTNER BANDS (LOOKAHEAD PREVENTION)
# =============================================================================

class TestDonchianAndKeltnerBands(unittest.TestCase):
    """Validates Donchian and Keltner calculation and strict lookahead bias elimination."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}

    def test_donchian_shift1_strictly_prevents_lookahead(self):
        """
        Verify that donchian_high[t] does NOT include high[t].
        If high[t] spikes to 999999.0, donchian_high[t] MUST remain unaffected.
        The spike must only appear in donchian_high[t+1].
        """
        n_bars = 50
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": np.full(n_bars, 100.0),
            "high": np.full(n_bars, 105.0),
            "low": np.full(n_bars, 95.0),
            "close": np.full(n_bars, 100.0),
            "volume": np.full(n_bars, 1000.0),
        })

        # Inject extreme high at candle 35
        spike_index = 35
        df.loc[spike_index, "high"] = 999999.0

        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        # On the exact candle of the spike (35), donchian_high MUST be 105.0 (unaffected)
        self.assertEqual(res.loc[spike_index, "donchian_high"], 105.0,
                         "Lookahead bias detected! donchian_high[t] includes high[t] instead of high[t-1].")

        # On the candle AFTER the spike (36), donchian_high must reflect 999999.0
        self.assertEqual(res.loc[spike_index + 1, "donchian_high"], 999999.0,
                         "donchian_high[t+1] failed to register previous candle's breakout high.")

    def test_donchian_channel_ordering(self):
        """Verify donchian_high >= donchian_mid >= donchian_low and mid is the exact average."""
        df = generate_synthetic_ohlcv(n_bars=100)
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        valid_slice = res.iloc[30:]  # after warmup
        highs = valid_slice["donchian_high"]
        mids = valid_slice["donchian_mid"]
        lows = valid_slice["donchian_low"]

        self.assertTrue((highs >= mids).all(), "Donchian high must be >= mid.")
        self.assertTrue((mids >= lows).all(), "Donchian mid must be >= low.")
        np.testing.assert_allclose(mids, (highs + lows) / 2.0, rtol=1e-6)

    def test_keltner_channel_envelope_properties(self):
        """Verify Keltner Upper = EMA_basis + keltner_mult * ATR."""
        df = generate_synthetic_ohlcv(n_bars=100)
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        valid = res.iloc[30:]
        mult = self.strategy.keltner_mult.value
        expected_upper = valid["ema_basis"] + mult * valid["atr"]
        expected_lower = valid["ema_basis"] - mult * valid["atr"]

        np.testing.assert_allclose(valid["keltner_upper"], expected_upper, rtol=1e-5)
        np.testing.assert_allclose(valid["keltner_lower"], expected_lower, rtol=1e-5)


# =============================================================================
# UNIT TEST SUITE 3: TEMPORAL CAUSALITY & LOOKAHEAD INVARIANCE
# =============================================================================

class TestLookaheadBiasPrevention(unittest.TestCase):
    """
    Stress tests temporal invariance: modifying future bars must have ZERO
    effect on past indicator calculations or past buy/sell signals.
    """

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}

    def test_past_indicators_invariant_to_future_price_changes(self):
        """Perturbing candles 150..200 must NOT alter indicators for candles 0..149."""
        df1 = generate_synthetic_ohlcv(n_bars=200, seed=101)
        df2 = df1.copy()

        # Massively perturb the future (bars 150 to 199)
        df2.loc[150:, "open"] *= 2.5
        df2.loc[150:, "high"] *= 3.0
        df2.loc[150:, "low"] *= 0.5
        df2.loc[150:, "close"] *= 2.8
        df2.loc[150:, "volume"] *= 10.0

        self.strategy.dp = MockDataProvider()
        res1 = self.strategy.populate_indicators(df1, self.metadata)
        res2 = self.strategy.populate_indicators(df2, self.metadata)

        # Columns to verify
        indicator_cols = [
            "parkinson_fast", "parkinson_slow", "pvr",
            "donchian_high", "donchian_mid", "donchian_low",
            "atr", "atr_pct", "ema_basis", "keltner_upper",
            "volume_mean", "ema_trend"
        ]

        past_res1 = res1.loc[:149, indicator_cols]
        past_res2 = res2.loc[:149, indicator_cols]

        assert_frame_equal(past_res1, past_res2,
                           obj="Past indicator data altered by future price perturbations (lookahead leak)!")

    def test_past_entry_signals_invariant_to_future_data(self):
        """Past buy/sell signals must be identical regardless of subsequent price action."""
        df1 = generate_synthetic_ohlcv(n_bars=200, seed=202)
        df2 = df1.copy()
        df2.loc[160:, "close"] *= 5.0

        self.strategy.dp = MockDataProvider()
        ind1 = self.strategy.populate_indicators(df1, self.metadata)
        ind2 = self.strategy.populate_indicators(df2, self.metadata)

        entry1 = self.strategy.populate_entry_trend(ind1, self.metadata)
        entry2 = self.strategy.populate_entry_trend(ind2, self.metadata)

        signal_cols = ["enter_long", "enter_tag"]
        assert_frame_equal(entry1.loc[:159, signal_cols], entry2.loc[:159, signal_cols],
                           obj="Past entry signals changed when future data changed!")


# =============================================================================
# UNIT TEST SUITE 4: ENTRY SIGNAL MATRIX & SUPPRESSION TRUTH TABLE
# =============================================================================

class TestEntrySignals(unittest.TestCase):
    """Validates full breakout trigger and orthogonal suppression when any filter fails."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}
        self.strategy.dp = MockDataProvider()

    def _create_baseline_test_frame(self) -> pd.DataFrame:
        """Creates a DataFrame where candle 50 meets ALL 7 entry conditions."""
        n_bars = 60
        df = generate_synthetic_ohlcv(n_bars=n_bars, base_price=100.0, volatility=0.01)
        df = self.strategy.populate_indicators(df, self.metadata)

        idx = 50
        # Force all baseline conditions on candle 50:
        # 1. close > donchian_high
        df.loc[idx, "close"] = df.loc[idx, "donchian_high"] + 5.0
        # 2. close > keltner_upper
        if df.loc[idx, "close"] <= df.loc[idx, "keltner_upper"]:
            df.loc[idx, "close"] = df.loc[idx, "keltner_upper"] + 2.0
        # 3. pvr > threshold (1.10)
        df.loc[idx, "pvr"] = 1.35
        # 4. volume > volume_factor * volume_mean
        df.loc[idx, "volume"] = df.loc[idx, "volume_mean"] * 2.0
        # 5. close > ema_trend
        df.loc[idx, "ema_trend"] = df.loc[idx, "close"] - 10.0
        # 6. btc_uptrend_1h == 1
        df.loc[idx, "btc_uptrend_1h"] = 1
        # 7. volume > 0
        self.assertGreater(df.loc[idx, "volume"], 0)

        return df

    def test_entry_triggers_when_all_conditions_satisfied(self):
        """All 7 conditions met -> enter_long == 1 and enter_tag == 'pvb_breakout'."""
        df = self._create_baseline_test_frame()
        res = self.strategy.populate_entry_trend(df, self.metadata)

        self.assertEqual(res.loc[50, "enter_long"], 1, "Failed to trigger entry when all 7 conditions met.")
        self.assertEqual(res.loc[50, "enter_tag"], "pvb_breakout", "Incorrect enter_tag.")

    def test_entry_suppressed_when_donchian_fails(self):
        """Condition 1 fails: close <= donchian_high -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "close"] = df.loc[50, "donchian_high"] - 0.50
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered despite Donchian breakout failure!")

    def test_entry_suppressed_when_keltner_fails(self):
        """Condition 2 fails: close <= keltner_upper -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "close"] = df.loc[50, "keltner_upper"] - 0.50
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered despite Keltner breakout failure!")

    def test_entry_suppressed_when_pvr_fails(self):
        """Condition 3 fails: PVR <= 1.10 (no volatility expansion) -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "pvr"] = 1.05  # below 1.10 threshold
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered despite weak PVR volatility!")

    def test_entry_suppressed_when_volume_fails(self):
        """Condition 4 fails: volume <= volume_factor * volume_mean -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "volume"] = df.loc[50, "volume_mean"] * 0.90  # low volume
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered despite below-average volume!")

    def test_entry_suppressed_when_macro_trend_fails(self):
        """Condition 5 fails: close <= ema_trend -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "ema_trend"] = df.loc[50, "close"] + 5.0  # trend resistance above price
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered in structural asset downtrend!")

    def test_entry_suppressed_when_btc_bearish(self):
        """Condition 6 fails: btc_uptrend_1h == 0 -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "btc_uptrend_1h"] = 0  # Bitcoin macro gate closed
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered while Bitcoin is in macro bear market!")

    def test_entry_suppressed_on_zero_volume(self):
        """Condition 7 fails: volume == 0 -> enter_long must be 0."""
        df = self._create_baseline_test_frame()
        df.loc[50, "volume"] = 0.0
        res = self.strategy.populate_entry_trend(df, self.metadata)
        self.assertEqual(res.loc[50, "enter_long"], 0, "Entry triggered on zero volume bar!")


# =============================================================================
# UNIT TEST SUITE 5: EXIT SIGNAL GENERATION & REVERSION
# =============================================================================

class TestExitSignals(unittest.TestCase):
    """Validates trend exhaustion exits (Donchian mid and EMA basis breaks)."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}
        self.strategy.dp = MockDataProvider()

    def test_exit_on_donchian_mid_break(self):
        """Close penetrates below Donchian Mid -> exit_long == 1."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df = self.strategy.populate_indicators(df, self.metadata)

        idx = 45
        df.loc[idx, "close"] = df.loc[idx, "donchian_mid"] - 1.0
        df.loc[idx, "volume"] = 1000.0

        res = self.strategy.populate_exit_trend(df, self.metadata)
        self.assertEqual(res.loc[idx, "exit_long"], 1, "Failed to exit when close dropped below Donchian mid.")
        self.assertEqual(res.loc[idx, "exit_tag"], "trend_exhaustion")

    def test_exit_on_ema_basis_break_when_enabled(self):
        """Close penetrates below EMA basis when exit_ema_basis is True -> exit_long == 1."""
        self.strategy.exit_donchian_mid.value = False
        self.strategy.exit_ema_basis.value = True

        df = generate_synthetic_ohlcv(n_bars=60)
        df = self.strategy.populate_indicators(df, self.metadata)

        idx = 45
        df.loc[idx, "close"] = df.loc[idx, "ema_basis"] - 1.0
        df.loc[idx, "volume"] = 1000.0

        res = self.strategy.populate_exit_trend(df, self.metadata)
        self.assertEqual(res.loc[idx, "exit_long"], 1, "Failed to exit when close dropped below EMA basis.")

    def test_no_exit_when_trend_remains_healthy(self):
        """Close remains safely above Donchian mid and EMA basis -> exit_long == 0."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df = self.strategy.populate_indicators(df, self.metadata)

        idx = 45
        df.loc[idx, "close"] = max(df.loc[idx, "donchian_mid"], df.loc[idx, "ema_basis"]) + 5.0
        df.loc[idx, "volume"] = 1000.0

        res = self.strategy.populate_exit_trend(df, self.metadata)
        self.assertEqual(res.loc[idx, "exit_long"], 0, "Premature exit triggered while trend was healthy.")

    def test_custom_exit_stale_trade(self):
        """custom_exit returns 'stale_exit' when trade is older than STALE_EXIT_DAYS."""
        class MockTrade:
            open_date_utc = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        trade = MockTrade()
        # 15 days later (STALE_EXIT_DAYS = 14)
        current_time = datetime(2026, 1, 16, 0, 0, 0, tzinfo=timezone.utc)
        result = self.strategy.custom_exit("SOL/EUR", trade, current_time, 100.0, 0.01)
        self.assertEqual(result, "stale_exit", "Stale trade was not liquidated after 15 days.")

        # 5 days later -> should return None
        fresh_time = datetime(2026, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
        result_fresh = self.strategy.custom_exit("SOL/EUR", trade, fresh_time, 100.0, 0.01)
        self.assertIsNone(result_fresh, "Active trade prematurely flagged as stale.")


# =============================================================================
# UNIT TEST SUITE 6: EDGE CASES, DATA HYGIENE & CORRUPT DATA
# =============================================================================

class TestEdgeCasesAndDataHygiene(unittest.TestCase):
    """Stress tests anomalous market conditions, startup warmup, and missing data."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}

    def test_startup_warmup_nans_do_not_trigger_entries(self):
        """During startup period (candles with NaNs), enter_long must never be 1."""
        df = generate_synthetic_ohlcv(n_bars=150)
        self.strategy.dp = MockDataProvider()
        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)

        # Check the first 25 bars (where EMA, ATR, Donchian, PVR have NaNs)
        warmup_entries = entry.loc[:24, "enter_long"].fillna(0)
        self.assertTrue((warmup_entries == 0).all(), "Entry triggered during NaN warmup phase!")

    def test_fifty_consecutive_flat_candles(self):
        """A prolonged flatline market (zero volatility) must not crash or generate signals."""
        n_bars = 70
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC"),
            "open": np.full(n_bars, 50.0),
            "high": np.full(n_bars, 50.0),
            "low": np.full(n_bars, 50.0),
            "close": np.full(n_bars, 50.0),
            "volume": np.full(n_bars, 500.0),
        })
        self.strategy.dp = MockDataProvider()
        ind = self.strategy.populate_indicators(df, self.metadata)
        entry = self.strategy.populate_entry_trend(ind, self.metadata)
        exit_df = self.strategy.populate_exit_trend(ind, self.metadata)

        self.assertFalse(np.isinf(ind["pvr"]).any(), "Infinite value in PVR on flat market.")
        self.assertTrue((entry["enter_long"].fillna(0) == 0).all(), "Entry triggered in zero volatility flatline!")

    def test_missing_btc_informative_falls_back_gracefully(self):
        """If BTC informative data is missing or empty, strategy defaults btc_uptrend_1h to 1."""
        df = generate_synthetic_ohlcv(n_bars=60)
        self.strategy.dp = MockDataProvider(btc_df=None)  # No BTC data
        res = self.strategy.populate_indicators(df, self.metadata)

        self.assertIn("btc_uptrend_1h", res.columns, "btc_uptrend_1h column missing from dataframe.")
        self.assertTrue((res["btc_uptrend_1h"] == 1).all(), "Default fallback for missing BTC should be 1.")

    def test_inverted_or_zero_low_candle_sanitization(self):
        """Test resilience against data feed glitches (e.g. low <= 0)."""
        df = generate_synthetic_ohlcv(n_bars=60)
        df.loc[30, "low"] = 0.0  # Glitched zero low
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        self.assertFalse(np.isinf(res.loc[30, "parkinson_fast"]), "Zero low caused inf in parkinson_fast.")
        self.assertFalse(np.isnan(res.loc[30, "parkinson_fast"]), "Zero low caused NaN in parkinson_fast.")


# =============================================================================
# UNIT TEST SUITE 7: FREQTRADE API CONFORMANCE & METADATA
# =============================================================================

class TestFreqtradeInterfaceAndMetadata(unittest.TestCase):
    """Validates Freqtrade v3 strategy interface contracts and risk parameters."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})

    def test_interface_version(self):
        self.assertEqual(self.strategy.INTERFACE_VERSION, 3, "Must implement INTERFACE_VERSION = 3.")

    def test_timeframe_is_one_hour(self):
        self.assertEqual(self.strategy.timeframe, "1h", "Base timeframe must be '1h' to beat Kraken fees.")

    def test_stoploss_within_asymmetric_bounds(self):
        self.assertLess(self.strategy.stoploss, -0.02, "Stoploss must be negative and at least -2%.")
        self.assertGreaterEqual(self.strategy.stoploss, -0.06, "Stoploss should not exceed -6%.")

    def test_trailing_stop_configured_properly(self):
        self.assertTrue(self.strategy.trailing_stop, "Trailing stop must be enabled.")
        self.assertGreater(self.strategy.trailing_stop_positive_offset, self.strategy.trailing_stop_positive,
                           "trailing_stop_positive_offset must be strictly greater than trailing_stop_positive.")
        self.assertTrue(self.strategy.trailing_only_offset_is_reached,
                        "trailing_only_offset_is_reached must be True.")

    def test_minimal_roi_table_monotonic_decay(self):
        """Minimal ROI table must have non-increasing profit targets as holding time grows."""
        roi_table = self.strategy.minimal_roi
        sorted_times = sorted([int(k) for k in roi_table.keys()])

        previous_target = float("inf")
        for t in sorted_times:
            current_target = roi_table[str(t)]
            self.assertLessEqual(current_target, previous_target,
                                 f"ROI target at {t}m ({current_target}) exceeds target at previous time ({previous_target}).")
            previous_target = current_target

    def test_informative_pairs_registration(self):
        """informative_pairs must register BTC/{stake_currency} on 1h."""
        pairs = self.strategy.informative_pairs()
        self.assertIsInstance(pairs, list)
        self.assertIn(("BTC/EUR", "1h"), pairs)

    def test_hyperopt_parameters_initialized(self):
        """Verify all hyperopt parameters have valid initial priors within bounds."""
        self.assertTrue(14 <= self.strategy.donchian_period.value <= 36)
        self.assertTrue(1.02 <= self.strategy.pvr_threshold.value <= 1.35)
        self.assertTrue(1.20 <= self.strategy.keltner_mult.value <= 2.50)
        self.assertTrue(1.05 <= self.strategy.volume_factor.value <= 1.50)


# =============================================================================
# UNIT TEST SUITE 8: SLIPPAGE MIXIN COMPATIBILITY
# =============================================================================

class TestSlippageMixinIntegration(unittest.TestCase):
    """Validates compatibility with KrakenSlippageMixin (requires atr_pct)."""

    def setUp(self):
        if WolfBreakout_PVB is None:
            self.skipTest("WolfBreakout_PVB strategy not yet implemented.")
        self.strategy = WolfBreakout_PVB(config={"stake_currency": "EUR"})
        self.metadata = {"pair": "SOL/EUR"}

    def test_atr_pct_is_computed_and_valid(self):
        """KrakenSlippageMixin requires 'atr_pct' in the analyzed dataframe."""
        df = generate_synthetic_ohlcv(n_bars=60)
        self.strategy.dp = MockDataProvider()
        res = self.strategy.populate_indicators(df, self.metadata)

        self.assertIn("atr_pct", res.columns, "Column 'atr_pct' missing! Required by KrakenSlippageMixin.")
        valid = res.loc[30:, "atr_pct"]
        self.assertTrue((valid > 0).all(), "atr_pct must be strictly positive for normal candles.")
        self.assertTrue((valid < 0.50).all(), "atr_pct should be realistic (< 50% of price).")


if __name__ == "__main__":
    unittest.main()
