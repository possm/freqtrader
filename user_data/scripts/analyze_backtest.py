#!/usr/bin/env python3
"""
analyze_backtest.py — Phase 3 deep metric analysis across IS/OOS windows.

Reads the per-window result files produced by run_isos.sh (wqe_<window>.json) and produces
the cross-strategy comparison the brief asks for:

  * EDGE ROBUSTNESS : profit% / profit-factor / expectancy for every strategy in every window,
    so you can read IS vs OOS under all three framings at a glance.
  * DRAWDOWN        : max drawdown depth AND the true peak-to-recovery underwater duration
    (recomputed from the trade-by-trade equity curve, not just peak->trough).
  * TRADE DISTRIBUTION : is the profit real or driven by 1-2 lucky outliers? We report the
    top-3 trades' share of gross profit and the full-period result with the single best trade
    removed.
  * ROBUSTNESS vs RETURN scoreboard : #positive windows, worst-window profit (robustness) next
    to full-period profit and Calmar (return) — so a good all-rounder is obvious.

RUN IN-CONTAINER (uses freqtrade's own stats loader):
  docker exec freqtrade-wolf python3 /freqtrade/user_data/scripts/analyze_backtest.py
"""
from __future__ import annotations

import glob
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RESULTS = "/freqtrade/user_data/backtest_results"
WALLET = 900.0  # starting balance (config_binance dry_run_wallet) for equity-curve reconstruction


def _load(path: str) -> dict | None:
    """Read the stats JSON straight out of the result .zip.

    We read the zip member directly rather than via load_backtest_stats(), because that helper
    derives the internal member name from the zip filename — which breaks once we rename results
    to wqe_<window>.zip. The stats file is the largest .json member that isn't the *_config.json.
    """
    try:
        with zipfile.ZipFile(path) as z:
            jsons = [m for m in z.namelist() if m.endswith(".json") and "_config" not in m]
            if not jsons:
                return None
            member = max(jsons, key=lambda m: z.getinfo(m).file_size)
            with z.open(member) as fh:
                return json.load(fh)
    except Exception as e:
        print(f"  zip load err {Path(path).name}: {e}")
        return None


def g(d: dict, *keys, default=np.nan):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def underwater_recovery_days(trades: list) -> float:
    """Longest peak-to-recovery (back to a new equity high) span, in days, from closed trades."""
    if not trades:
        return np.nan
    df = pd.DataFrame(trades)
    if "close_date" not in df or "profit_abs" not in df:
        return np.nan
    df = df.sort_values("close_date")
    t = pd.to_datetime(df["close_date"])
    equity = WALLET + df["profit_abs"].cumsum().values
    peak = -np.inf
    peak_t = t.iloc[0]
    longest = 0.0
    for ts, eq in zip(t, equity):
        if eq >= peak:
            peak, peak_t = eq, ts
        else:
            longest = max(longest, (ts - peak_t).total_seconds() / 86400.0)
    return round(longest, 1)


def outlier_check(trades: list) -> tuple:
    """(top-3 share of gross profit %, full result with best trade removed %)."""
    if not trades:
        return (np.nan, np.nan)
    pa = pd.Series([t.get("profit_abs", 0.0) for t in trades]).sort_values(ascending=False)
    gross_pos = pa[pa > 0].sum()
    top3_share = (pa.head(3).clip(lower=0).sum() / gross_pos * 100) if gross_pos > 0 else np.nan
    total_minus_best = (pa.sum() - pa.iloc[0]) / WALLET * 100
    return (round(top3_share, 1), round(total_minus_best, 2))


def per_strategy(stats: dict) -> dict:
    out = {}
    for name, s in stats.get("strategy", {}).items():
        trades = s.get("trades", [])
        out[name] = {
            "trades": int(g(s, "total_trades", default=len(trades))),
            "profit%": round(float(g(s, "profit_total", default=0.0)) * 100, 2),
            "pf": round(float(g(s, "profit_factor", default=np.nan)), 2),
            "expR": round(float(g(s, "expectancy_ratio", default=np.nan)), 3),
            "win%": round(float(g(s, "winrate", default=np.nan)) * 100, 1)
            if not np.isnan(g(s, "winrate", default=np.nan)) else
            (round(g(s, "wins", default=0) / max(len(trades), 1) * 100, 1)),
            "maxDD%": round(float(g(s, "max_drawdown_account", "max_drawdown",
                                    "max_relative_drawdown", default=0.0)) * 100, 2),
            "calmar": round(float(g(s, "calmar", default=np.nan)), 2),
            "sharpe": round(float(g(s, "sharpe", default=np.nan)), 2),
            "recov_d": underwater_recovery_days(trades),
        }
        out[name]["top3%"], out[name]["minusBest%"] = outlier_check(trades)
    return out


def main():
    files = sorted(glob.glob(f"{RESULTS}/wqe_*.zip"))
    if not files:
        print(f"No result files in {RESULTS}/wqe_*.zip — run run_isos.sh first.")
        return

    rows = []
    for f in files:
        window = Path(f).stem.replace("wqe_", "")
        stats = _load(f)
        if not stats:
            print(f"  (could not load {f})")
            continue
        for strat, m in per_strategy(stats).items():
            rows.append({"window": window, "strategy": strat, **m})
    if not rows:
        print("No stats parsed.")
        return
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)

    # dynamic: include every yXXXX window found, sorted, then "full" at the end (future-proof)
    windows_present = df["window"].unique().tolist()
    year_windows = sorted(w for w in windows_present if w.startswith("y"))
    order = year_windows + (["full"] if "full" in windows_present else [])

    def matrix(metric):
        return (df.pivot(index="strategy", columns="window", values=metric)
                  .reindex(columns=order))

    print("\n" + "=" * 78 + "\nPROFIT %  (strategy x window)\n" + "=" * 78)
    print(matrix("profit%").to_string())
    print("\n" + "=" * 78 + "\nPROFIT FACTOR\n" + "=" * 78)
    print(matrix("pf").to_string())
    print("\n" + "=" * 78 + "\nMAX DRAWDOWN %\n" + "=" * 78)
    print(matrix("maxDD%").to_string())

    # full-window deep dive (return + distribution + recovery)
    full = df[df["window"] == "full"].set_index("strategy")
    if len(full):
        print("\n" + "=" * 78 + "\nFULL-PERIOD DEEP DIVE (2021->now)\n" + "=" * 78)
        cols = ["trades", "profit%", "pf", "expR", "win%", "maxDD%", "recov_d",
                "calmar", "sharpe", "top3%", "minusBest%"]
        print(full[cols].to_string())

    # robustness vs return scoreboard
    print("\n" + "=" * 78 + "\nROBUSTNESS vs RETURN SCOREBOARD\n" + "=" * 78)
    yearcols = [w for w in order if w.startswith("y")]
    score = []
    for strat in df["strategy"].unique():
        sub = df[(df["strategy"] == strat) & (df["window"].isin(yearcols))]
        prof = sub["profit%"]
        fullrow = df[(df["strategy"] == strat) & (df["window"] == "full")]
        score.append({
            "strategy": strat,
            "pos_windows": f"{int((prof > 0).sum())}/{len(prof)}",
            "worst_yr%": round(prof.min(), 2),
            "mean_yr%": round(prof.mean(), 2),
            "full%": round(fullrow["profit%"].iloc[0], 2) if len(fullrow) else np.nan,
            "full_calmar": round(fullrow["calmar"].iloc[0], 2) if len(fullrow) else np.nan,
            "full_maxDD%": round(fullrow["maxDD%"].iloc[0], 2) if len(fullrow) else np.nan,
        })
    sb = pd.DataFrame(score).sort_values(["worst_yr%", "full%"], ascending=False)
    print(sb.to_string(index=False))
    print("\nRead: pos_windows + worst_yr% = robustness; full% + full_calmar = return.")


if __name__ == "__main__":
    main()
