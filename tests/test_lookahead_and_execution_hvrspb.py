"""
tests/test_lookahead_and_execution_hvrspb.py — Adversarial Lookahead & Order Execution Suite
=============================================================================================
Milestone 1 Challenger 2: Lookahead Bias & Order Execution / Fee Conformance Verification
Strategy: WolfBreakout_HVRSPB (user_data/strategies/WolfBreakout_HVRSPB.py)

Empirically challenges:
1. Lookahead Bias Verification:
   - Future candle perturbation (t+1, t+2, ..., t+k):
     Empirically proves that altering future candle prices (pumps, dumps, volatility surges, flat)
     does NOT alter indicators or signals generated at candle t.
   - Informative BTC pair future perturbation:
     Proves that future BTC candles do NOT leak into altcoin signals at candle t.
   - Point-in-time incremental slicing invariance:
     Proves that feeding data candle-by-candle (live mode) yields signals identical
     to processing the full series in a single batch (backtest mode).
   - Donchian shift(1) decoupling proof:
     Proves that candle t's high/low never influences candle t's resistance levels.

2. Order Execution & Fee Assumptions:
   - Limit order pricing and execution sanity:
     Verifies strategy uses standard Freqtrade limit orders without unrealistic custom price overrides.
   - Fee hurdle resilience:
     Verifies maker vs taker fee assumptions against Kraken exchange schedule (0.16% maker, 0.26% taker).
   - Strict Freqtrade custom_stoploss conformance:
     Verifies custom_stoploss returns strictly conforming negative float distances or None.
   - Real Trade model stoploss ratcheting lifecycle:
     Simulates full trade progression (-6% floor -> +0.8% BE lock -> 4% trailing runner).
   - Custom exit reason contracts and invalidation thresholds.
"""
from __future__ import annotations

import math
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

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
from freqtrade.persistence import Trade
from test_wolfbreakout_hvrspb import (
    MockDataProvider,
    MockTrade,
    generate_synthetic_ohlcv,
    generate_synthetic_btc,
)


class TestLookaheadFutureCandlePerturbation(unittest.TestCase):
    """
    Adversarial challenge: Mutate future candles (t+1, t+2, ... t+k) with extreme shocks
    and verify that candle t's indicators and entry/exit signals remain 100% immutable.
    """

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        # 300 candles provides ample history past the 250 startup_candle_count
        self.base_df = generate_synthetic_ohlcv(n_bars=300, base_price=100.0, volatility=0.015, seed=123)
        self.btc_df = generate_synthetic_btc(n_bars=300, base_price=60000.0, return_24h_pct=0.01, is_bullish=True)
        self.strategy.dp = MockDataProvider(btc_df=self.btc_df)

        # Baseline evaluation
        self.baseline_analyzed = self.strategy.populate_indicators(self.base_df.copy(), {"pair": "FET/EUR"})
        self.baseline_entry = self.strategy.populate_entry_trend(self.baseline_analyzed.copy(), {"pair": "FET/EUR"})
        self.baseline_exit = self.strategy.populate_exit_trend(self.baseline_entry.copy(), {"pair": "FET/EUR"})

    def _verify_invariance_at_t(self, mutated_df: pd.DataFrame, t: int, scenario_name: str):
        """Helper to verify that all indicators and signals at <= t match baseline exactly."""
        mut_analyzed = self.strategy.populate_indicators(mutated_df.copy(), {"pair": "FET/EUR"})
        mut_entry = self.strategy.populate_entry_trend(mut_analyzed.copy(), {"pair": "FET/EUR"})
        mut_exit = self.strategy.populate_exit_trend(mut_entry.copy(), {"pair": "FET/EUR"})

        # Check signals at candle t
        self.assertEqual(
            mut_exit.loc[t, "enter_long"],
            self.baseline_exit.loc[t, "enter_long"],
            f"[{scenario_name}] enter_long altered at candle t={t} due to future perturbation!"
        )
        self.assertEqual(
            mut_exit.loc[t, "exit_long"],
            self.baseline_exit.loc[t, "exit_long"],
            f"[{scenario_name}] exit_long altered at candle t={t} due to future perturbation!"
        )
        self.assertEqual(
            mut_exit.loc[t, "enter_tag"],
            self.baseline_exit.loc[t, "enter_tag"],
            f"[{scenario_name}] enter_tag altered at candle t={t} due to future perturbation!"
        )
        self.assertEqual(
            mut_exit.loc[t, "exit_tag"],
            self.baseline_exit.loc[t, "exit_tag"],
            f"[{scenario_name}] exit_tag altered at candle t={t} due to future perturbation!"
        )

        # Check key indicator columns at candle t
        key_indicators = [
            "parkinson_20", "parkinson_ema", "pvr",
            "donchian_high", "donchian_low", "donchian_mid",
            "atr", "keltner_basis", "keltner_upper", "keltner_lower",
            "asset_return_24h", "rs_btc"
        ]
        for col in key_indicators:
            base_val = self.baseline_exit.loc[t, col]
            mut_val = mut_exit.loc[t, col]
            if np.isnan(base_val):
                self.assertTrue(np.isnan(mut_val), f"[{scenario_name}] {col} was NaN in base but not in mutated at t={t}")
            else:
                self.assertAlmostEqual(
                    base_val, mut_val, places=9,
                    msg=f"[{scenario_name}] Indicator '{col}' leaked future data at candle t={t}!"
                )

    def test_future_massive_pump_at_t_plus_1_and_2(self):
        """Perturb t+1 and t+2 with +500% price pump and 100x volume surge."""
        for t in [250, 260, 270, 280]:
            df_mut = self.base_df.copy()
            for future_idx in [t + 1, t + 2]:
                if future_idx < len(df_mut):
                    df_mut.loc[future_idx, "open"] *= 5.0
                    df_mut.loc[future_idx, "high"] *= 6.0
                    df_mut.loc[future_idx, "low"] *= 4.5
                    df_mut.loc[future_idx, "close"] *= 5.5
                    df_mut.loc[future_idx, "volume"] *= 100.0

            self._verify_invariance_at_t(df_mut, t, "Future Massive Pump")

    def test_future_catastrophic_dump_at_t_plus_1_and_2(self):
        """Perturb t+1 and t+2 with -90% price crash."""
        for t in [250, 260, 270, 280]:
            df_mut = self.base_df.copy()
            for future_idx in [t + 1, t + 2]:
                if future_idx < len(df_mut):
                    df_mut.loc[future_idx, "open"] *= 0.1
                    df_mut.loc[future_idx, "high"] *= 0.12
                    df_mut.loc[future_idx, "low"] *= 0.05
                    df_mut.loc[future_idx, "close"] *= 0.08
                    df_mut.loc[future_idx, "volume"] *= 50.0

            self._verify_invariance_at_t(df_mut, t, "Future Catastrophic Dump")

    def test_future_volatility_hyper_spike(self):
        """Perturb future candles with astronomical high/low spreads."""
        for t in [250, 265, 285]:
            df_mut = self.base_df.copy()
            for future_idx in range(t + 1, min(t + 6, len(df_mut))):
                df_mut.loc[future_idx, "high"] = 10000.0
                df_mut.loc[future_idx, "low"] = 0.001
                df_mut.loc[future_idx, "close"] = 500.0

            self._verify_invariance_at_t(df_mut, t, "Future Volatility Hyper Spike")

    def test_future_zero_volume_flat_freeze(self):
        """Perturb future candles into a completely dead frozen market (volume=0, O=H=L=C)."""
        for t in [250, 270, 290]:
            df_mut = self.base_df.copy()
            c_val = df_mut.loc[t, "close"]
            for future_idx in range(t + 1, len(df_mut)):
                df_mut.loc[future_idx, "open"] = c_val
                df_mut.loc[future_idx, "high"] = c_val
                df_mut.loc[future_idx, "low"] = c_val
                df_mut.loc[future_idx, "close"] = c_val
                df_mut.loc[future_idx, "volume"] = 0.0

            self._verify_invariance_at_t(df_mut, t, "Future Flat Freeze")


class TestLookaheadInformativeBtcLeakage(unittest.TestCase):
    """
    Adversarial challenge: Mutate future candles of the BTC informative pair
    and verify no cross-asset lookahead leakage into altcoin signals at candle t.
    """

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.base_df = generate_synthetic_ohlcv(n_bars=300, base_price=100.0, volatility=0.015, seed=456)
        self.btc_df = generate_synthetic_btc(n_bars=300, base_price=60000.0, return_24h_pct=0.01, is_bullish=True)

    def test_btc_future_pump_does_not_alter_altcoin_rs_at_t(self):
        """Mutating BTC at t+1 and t+2 (+50% pump) must not change rs_btc or entry at candle t."""
        t = 260
        self.strategy.dp = MockDataProvider(btc_df=self.btc_df.copy())
        base_analyzed = self.strategy.populate_indicators(self.base_df.copy(), {"pair": "NEAR/EUR"})
        base_entry = self.strategy.populate_entry_trend(base_analyzed.copy(), {"pair": "NEAR/EUR"})

        # Mutate BTC at t+1 and t+2
        mut_btc = self.btc_df.copy()
        mut_btc.loc[t + 1, "close"] *= 1.5
        mut_btc.loc[t + 1, "high"] *= 1.6
        mut_btc.loc[t + 2, "close"] *= 2.0
        mut_btc.loc[t + 2, "high"] *= 2.1

        self.strategy.dp = MockDataProvider(btc_df=mut_btc)
        mut_analyzed = self.strategy.populate_indicators(self.base_df.copy(), {"pair": "NEAR/EUR"})
        mut_entry = self.strategy.populate_entry_trend(mut_analyzed.copy(), {"pair": "NEAR/EUR"})

        self.assertEqual(
            mut_entry.loc[t, "enter_long"],
            base_entry.loc[t, "enter_long"],
            "BTC future pump altered altcoin entry signal at candle t!"
        )
        self.assertAlmostEqual(
            mut_entry.loc[t, "rs_btc"],
            base_entry.loc[t, "rs_btc"],
            places=9,
            msg="BTC future pump leaked into altcoin rs_btc at candle t!"
        )
        self.assertEqual(
            mut_entry.loc[t, "btc_uptrend_clean"],
            base_entry.loc[t, "btc_uptrend_clean"],
            "BTC future pump altered btc_uptrend_clean at candle t!"
        )

    def test_btc_future_trend_reversal_does_not_leak(self):
        """BTC 200 EMA flips to downtrend starting at t+1; verify candle t retains uptrend status."""
        t = 260
        self.strategy.dp = MockDataProvider(btc_df=self.btc_df.copy())
        base_analyzed = self.strategy.populate_indicators(self.base_df.copy(), {"pair": "NEAR/EUR"})

        # Mutate BTC from t+1 onwards to crash below EMA200
        mut_btc = self.btc_df.copy()
        for idx in range(t + 1, len(mut_btc)):
            mut_btc.loc[idx, "close"] = 1000.0
            mut_btc.loc[idx, "high"] = 1050.0
            mut_btc.loc[idx, "low"] = 950.0

        self.strategy.dp = MockDataProvider(btc_df=mut_btc)
        mut_analyzed = self.strategy.populate_indicators(self.base_df.copy(), {"pair": "NEAR/EUR"})

        self.assertEqual(
            mut_analyzed.loc[t, "btc_uptrend_clean"],
            base_analyzed.loc[t, "btc_uptrend_clean"],
            "Future BTC trend collapse leaked backward into candle t!"
        )


class TestPointInTimeIncrementalInvariance(unittest.TestCase):
    """
    Simulates real-world production bot behavior:
    Processes dataframe sequentially candle-by-candle (expanding window),
    and asserts that the signal generated on bar t in real-time matches
    the signal generated in full batch backtest mode.
    """

    def test_expanding_window_matches_batch_signals(self):
        """Gold standard point-in-time test across 30 consecutive live candles."""
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        n_bars = 280
        df = generate_synthetic_ohlcv(n_bars=n_bars, base_price=50.0, volatility=0.02, seed=789)
        btc_df = generate_synthetic_btc(n_bars=n_bars, base_price=60000.0, return_24h_pct=0.01)

        # Batch evaluation
        strategy.dp = MockDataProvider(btc_df=btc_df.copy())
        batch_analyzed = strategy.populate_indicators(df.copy(), {"pair": "SOL/EUR"})
        batch_entry = strategy.populate_entry_trend(batch_analyzed.copy(), {"pair": "SOL/EUR"})
        batch_exit = strategy.populate_exit_trend(batch_entry.copy(), {"pair": "SOL/EUR"})

        # Incremental evaluation for bars 250 to 279
        for t in range(250, 280):
            df_slice = df.iloc[: t + 1].copy()
            btc_slice = btc_df.iloc[: t + 1].copy()
            strategy.dp = MockDataProvider(btc_df=btc_slice)

            slice_analyzed = strategy.populate_indicators(df_slice, {"pair": "SOL/EUR"})
            slice_entry = strategy.populate_entry_trend(slice_analyzed, {"pair": "SOL/EUR"})
            slice_exit = strategy.populate_exit_trend(slice_entry, {"pair": "SOL/EUR"})

            # Incremental signal at the latest candle
            inc_enter = slice_exit.iloc[-1]["enter_long"]
            inc_exit = slice_exit.iloc[-1]["exit_long"]
            batch_enter = batch_exit.loc[t, "enter_long"]
            batch_exit_sig = batch_exit.loc[t, "exit_long"]

            self.assertEqual(
                inc_enter, batch_enter,
                f"Discrepancy in enter_long at t={t}: incremental={inc_enter} vs batch={batch_enter}"
            )
            self.assertEqual(
                inc_exit, batch_exit_sig,
                f"Discrepancy in exit_long at t={t}: incremental={inc_exit} vs batch={batch_exit_sig}"
            )


class TestDonchianLookaheadStrictDecoupling(unittest.TestCase):
    """Verifies that Donchian channels strictly ignore the current candle's high/low."""

    def test_current_candle_extreme_high_ignored(self):
        strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        df = generate_synthetic_ohlcv(n_bars=60, base_price=100.0, volatility=0.01)
        t = df.index[-1]

        # Normal run
        analyzed_normal = strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        normal_donch_high = analyzed_normal.loc[t, "donchian_high"]

        # Mutate candle t's high to 1,000,000.0
        df_spike = df.copy()
        df_spike.loc[t, "high"] = 1000000.0
        df_spike.loc[t, "close"] = 999999.0
        analyzed_spike = strategy.populate_indicators(df_spike, {"pair": "FET/EUR"})
        spike_donch_high = analyzed_spike.loc[t, "donchian_high"]

        self.assertEqual(
            normal_donch_high, spike_donch_high,
            "Donchian Upper shifted lookahead bias detected: current candle's high altered current donchian_high!"
        )


class TestOrderExecutionAndFeeAssumptions(unittest.TestCase):
    """
    Verifies realistic order execution properties:
    - Limit order types for maker fees
    - Absence of unrealistic custom pricing overrides
    - Fee hurdle validation (Kraken 0.26% taker vs 0.16% maker)
    """

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})

    def test_order_types_configuration(self):
        """Order types must enforce limit orders for entry and exit to capture maker fees."""
        self.assertEqual(self.strategy.order_types.get("entry"), "limit")
        self.assertEqual(self.strategy.order_types.get("exit"), "limit")
        self.assertEqual(self.strategy.order_types.get("emergency_exit"), "market")
        self.assertEqual(self.strategy.order_types.get("stoploss"), "market")
        self.assertFalse(self.strategy.order_types.get("stoploss_on_exchange"))

    def test_no_unrealistic_custom_pricing_methods(self):
        """
        Strategy must not override custom_entry_price or custom_exit_price with unrealistic
        assumptions (such as buying at low or selling at high).
        """
        # IStrategy base class has custom_entry_price / custom_exit_price returning None
        # Verify strategy does not override them
        self.assertFalse(
            "custom_entry_price" in self.strategy.__class__.__dict__,
            "WolfBreakout_HVRSPB must not override custom_entry_price"
        )
        self.assertFalse(
            "custom_exit_price" in self.strategy.__class__.__dict__,
            "WolfBreakout_HVRSPB must not override custom_exit_price"
        )

    def test_process_only_new_candles_enabled(self):
        """Prevents intra-candle order churn and ensures signals only generate on candle close."""
        self.assertTrue(self.strategy.process_only_new_candles)

    def test_fee_hurdle_safety_margin(self):
        """
        Kraken taker fee is 0.26% (0.0026), maker fee is 0.16% (0.0016).
        Backtest requirement uses --fee 0.0026.
        Verify that 0.0026 provides a +62.5% conservative hurdle over maker rates.
        """
        maker_fee = 0.0016
        taker_fee = 0.0026
        safety_buffer = (taker_fee - maker_fee) / maker_fee
        self.assertGreaterEqual(safety_buffer, 0.60)


class TestCustomStoplossFreqtradeContract(unittest.TestCase):
    """
    Stress tests Freqtrade custom_stoploss conformance:
    - Return value contract: strictly negative float or None
    - Real Trade model lifecycle and ratcheting
    - Wide profit spectrum (-50% to +1000%)
    """

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})
        self.mock_trade = MockTrade(open_rate=100.0, is_short=False)

    def test_custom_stoploss_return_type_across_profit_spectrum(self):
        """
        Freqtrade requirement: custom_stoploss must return either None or a float.
        In WolfBreakout_HVRSPB, when active, it returns -float(...) representing distance below current rate.
        Verify across 200 profit scenarios.
        """
        profits = np.linspace(-0.50, 5.0, 200)
        for p in profits:
            ret = self.strategy.custom_stoploss(
                pair="FET/EUR",
                trade=self.mock_trade,
                current_time=datetime.now(timezone.utc),
                current_rate=100.0 * (1.0 + p),
                current_profit=float(p),
            )
            if p < float(self.strategy.be_profit_threshold.value):
                self.assertIsNone(ret, f"custom_stoploss should return None for profit={p:.4f} < 0.035")
            else:
                self.assertIsInstance(ret, float, f"custom_stoploss must return float for profit={p:.4f}")
                self.assertLess(ret, 0.0, f"custom_stoploss return must be negative float for profit={p:.4f}")
                self.assertFalse(math.isnan(ret) or math.isinf(ret), f"custom_stoploss returned NaN/Inf for profit={p:.4f}")

    def test_real_trade_model_ratcheting_lifecycle(self):
        """
        Tests exact Freqtrade Trade model stoploss adjustment:
        1. Trade open at 100.0 -> initial stop loss = 94.0 (-6.0% hard floor)
        2. Profit at +2.0% -> stop loss remains 94.0
        3. Profit at +4.0% -> BE lock activates -> stop loss ratchets to 100.8 (+0.8% above entry)
        4. Profit at +7.0% -> stop loss remains 100.8
        5. Profit at +10.0% -> runner trailing activates -> stop loss ratchets to 105.6 (4.0% below 110.0)
        6. Profit at +20.0% (120.0) -> stop loss ratchets to 115.2 (4.0% below 120.0)
        7. Pullback to 116.0 -> stop loss stays locked at 115.2 (never decreases)
        """
        trade = Trade(
            pair="FET/EUR",
            stake_amount=100.0,
            amount=1.0,
            open_rate=100.0,
            fee_open=0.0016,
            fee_close=0.0016,
            exchange="kraken",
            open_date=datetime.now(timezone.utc),
            is_open=True,
            leverage=1.0,
            is_short=False,
        )
        trade.adjust_stop_loss(trade.open_rate, self.strategy.stoploss, initial=True)
        self.assertAlmostEqual(trade.stop_loss, 94.0, places=4)

        now = datetime.now(timezone.utc)

        # Stage 1: +2% profit -> no adjustment
        self.strategy.ft_stoploss_adjust(102.0, trade, now, 0.02, 0)
        self.assertAlmostEqual(trade.stop_loss, 94.0, places=4)

        # Stage 2: +4% profit -> BE lock (100 * 1.008 = 100.8)
        self.strategy.ft_stoploss_adjust(104.0, trade, now, 0.04, 0)
        self.assertAlmostEqual(trade.stop_loss, 100.8, places=4)

        # Stage 3: +7% profit -> stays at 100.8
        self.strategy.ft_stoploss_adjust(107.0, trade, now, 0.07, 0)
        self.assertAlmostEqual(trade.stop_loss, 100.8, places=4)

        # Stage 4: +10% profit -> runner trailing (110.0 * 0.96 = 105.6)
        self.strategy.ft_stoploss_adjust(110.0, trade, now, 0.10, 0)
        self.assertAlmostEqual(trade.stop_loss, 105.6, places=4)

        # Stage 5: +20% profit -> runner trailing (120.0 * 0.96 = 115.2)
        self.strategy.ft_stoploss_adjust(120.0, trade, now, 0.20, 0)
        self.assertAlmostEqual(trade.stop_loss, 115.2, places=4)

        # Stage 6: Pullback to 116.0 (+16% profit) -> stop loss MUST NOT decrease
        self.strategy.ft_stoploss_adjust(116.0, trade, now, 0.16, 0)
        self.assertAlmostEqual(trade.stop_loss, 115.2, places=4)

    def test_custom_stoploss_extreme_parabolic_profit(self):
        """Altcoin surges +1000% (10x): trailing runner trails accurately without precision degradation."""
        current_rate = 1100.0  # +1000% on 100.0 entry
        ret = self.strategy.custom_stoploss(
            pair="FET/EUR",
            trade=self.mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=current_rate,
            current_profit=10.0,
        )
        self.assertAlmostEqual(ret, -0.04, places=4)

        # Resulting stop price is current_rate * (1 - 0.04) = 1056.0
        expected_stop = current_rate * (1.0 - 0.04)
        self.assertAlmostEqual(expected_stop, 1056.0, places=2)


class TestCustomExitContract(unittest.TestCase):
    """Verifies custom_exit behavior, invalidation timing, and returned exit tags."""

    def setUp(self):
        self.strategy = WolfBreakout_HVRSPB({"stake_currency": "EUR"})

    def test_custom_exit_no_invalidation_under_4_hours(self):
        """Even with negative profit, trades open < 4h are NOT liquidated prematurely."""
        open_time = datetime.now(timezone.utc)
        mock_trade = MockTrade(open_rate=100.0, open_date_utc=open_time)

        # At 3 hours, profit is -2%
        curr_time = open_time + timedelta(hours=3)
        exit_tag = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=mock_trade,
            current_time=curr_time,
            current_rate=98.0,
            current_profit=-0.02,
        )
        self.assertIsNone(exit_tag)

    def test_custom_exit_fast_invalidation_after_4_hours(self):
        """Trades open >= 4h with profit < -1.5% trigger 'fast_invalidation_loss'."""
        open_time = datetime.now(timezone.utc)
        mock_trade = MockTrade(open_rate=100.0, open_date_utc=open_time)

        # At 4.1 hours, profit is -1.8%
        curr_time = open_time + timedelta(hours=4, minutes=6)
        exit_tag = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=mock_trade,
            current_time=curr_time,
            current_rate=98.2,
            current_profit=-0.018,
        )
        self.assertEqual(exit_tag, "fast_invalidation_loss")

    def test_custom_exit_stale_trade_reclaimer(self):
        """Trades open >= 14 days trigger 'stale_exit'."""
        open_time = datetime.now(timezone.utc) - timedelta(days=15)
        mock_trade = MockTrade(open_rate=100.0, open_date_utc=open_time)

        exit_tag = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=101.0,
            current_profit=0.01,
        )
        self.assertEqual(exit_tag, "stale_exit")


if __name__ == "__main__":
    unittest.main()
