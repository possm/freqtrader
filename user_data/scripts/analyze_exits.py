#!/usr/bin/env python3
"""
analyze_exits.py — inspect WolfQuantEdge exit behaviour to inform exit-timing tuning.

For every closed trade we compare the REALISED profit against the trade's Maximum Favourable
Excursion (MFE = how high it ran) and Maximum Adverse Excursion (MAE = how low it dipped),
both reconstructed from freqtrade's max_rate/min_rate. The key column is GIVEBACK% = MFE - realised:
how much peak profit we let slip before the exit fired. Grouped by exit_reason, this tells us
whether we're closing too LATE (high giveback on winners -> trailing too loose / exit lagging) or
too EARLY (small MFE on losers, or ROI/trailing capping runners short).

Usage (in-container):
  docker exec freqtrade-wolf-qe python3 /freqtrade/user_data/scripts/analyze_exits.py --days 1
"""
from __future__ import annotations

import argparse
import sqlite3

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/freqtrade/user_data/tradesv3_qe.sqlite")
    ap.add_argument("--days", type=float, default=1.0)
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    t = pd.read_sql(
        "SELECT id,pair,is_open,open_rate,close_rate,max_rate,min_rate,open_date,close_date,"
        "close_profit,close_profit_abs,stake_amount,exit_reason,enter_tag FROM trades",
        con, parse_dates=["open_date", "close_date"],
    )
    con.close()

    for col in ["open_date", "close_date"]:
        if t[col].dt.tz is None:
            t[col] = t[col].dt.tz_localize("UTC")
    now = pd.Timestamp.now(tz="UTC")

    opent = t[t.is_open == 1].copy()
    closed = t[t.is_open == 0].copy()
    print(f"DB totals: {len(t)} trades | open {len(opent)} | closed {len(closed)}")
    if len(closed):
        print(f"closed range: {closed.close_date.min()} .. {closed.close_date.max()}")

    def mfe(r):
        return (r.max_rate - r.open_rate) / r.open_rate if r.open_rate else float("nan")

    def mae(r):
        return (r.min_rate - r.open_rate) / r.open_rate if r.open_rate else float("nan")

    cutoff = now - pd.Timedelta(days=args.days)
    win = closed[closed.close_date >= cutoff]

    for df, name in [(win, f"last {args.days}d"), (closed, "all-time")]:
        if not len(df):
            print(f"\n({name}: no closed trades)")
            continue
        df = df.copy()
        df["dur_h"] = (df.close_date - df.open_date).dt.total_seconds() / 3600
        df["prof%"] = df.close_profit * 100
        df["mfe%"] = df.apply(mfe, axis=1) * 100
        df["mae%"] = df.apply(mae, axis=1) * 100
        df["giveback%"] = df["mfe%"] - df["prof%"]
        print(f"\n=== {name}: {len(df)} closed ===")
        print(df.sort_values("close_date")[
            ["pair", "enter_tag", "exit_reason", "dur_h", "prof%", "mfe%", "mae%", "giveback%"]
        ].round(2).to_string(index=False))
        print(f"\n--- {name} by exit_reason ---")
        g = df.groupby("exit_reason").agg(
            n=("prof%", "size"), avg_prof=("prof%", "mean"), win_rate=("prof%", lambda s: (s > 0).mean() * 100),
            avg_dur_h=("dur_h", "mean"), avg_mfe=("mfe%", "mean"), avg_giveback=("giveback%", "mean"),
        ).round(2)
        print(g.to_string())

    if len(opent):
        opent = opent.copy()
        opent["age_h"] = (now - opent.open_date).dt.total_seconds() / 3600
        opent["mfe%"] = opent.apply(mfe, axis=1) * 100
        opent["mae%"] = opent.apply(mae, axis=1) * 100
        print(f"\n=== OPEN now: {len(opent)} ===")
        print(opent.sort_values("age_h", ascending=False)[
            ["pair", "enter_tag", "age_h", "mfe%", "mae%"]
        ].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
