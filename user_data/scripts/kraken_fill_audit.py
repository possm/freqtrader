#!/usr/bin/env python3
"""
kraken_fill_audit.py — Phase 4 live-fill vs backtest-model audit.

Extends the original analyze_slippage.py. That script measured ACTUAL slippage (fill vs candle
reference). This one goes one step further and the whole point of Phase 4: it compares each live
(dry-run) Kraken fill against what the BACKTEST SLIPPAGE MODEL (kraken_slippage.py) ASSUMED the
slippage would be — and flags where reality and the model diverge.

Why this matters: our entire edge estimate (+16% net) is only trustworthy if the Kraken tax we
modelled in backtest matches the Kraken tax we actually pay. If real fills are consistently
WORSE than the model, the backtest overstated the edge (tighten KRAKEN_SPREAD_BPS / SLIP_ATR_COEF).
If real fills are consistently BETTER, we were too pessimistic and left trades on the table.

  ACTUAL slip   = adverse move of the fill vs the candle's typical price, in bps
  MODEL slip    = kraken_slippage one-way model: half_spread + SLIP_ATR_COEF * atr_pct, in bps
  DIVERGENCE    = ACTUAL - MODEL  (positive => real Kraken is worse than we assumed)

Run in-container (so freqtrade + the strategy modules import cleanly):
  docker exec freqtrade-wolf python3 /freqtrade/user_data/scripts/kraken_fill_audit.py \
      --db sqlite:////freqtrade/user_data/tradesv3_qe.sqlite
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/freqtrade/user_data/strategies")
try:
    from kraken_slippage import kraken_half_spread_frac, KrakenSlippageMixin as _M
    ATR_COEF = _M.SLIP_ATR_COEF
except Exception:
    ATR_COEF = 0.08
    def kraken_half_spread_frac(pair):  # noqa: E306
        _S = {"BTC": 1.5, "ETH": 2.0, "SOL": 3.0, "LINK": 4.0, "ADA": 4.0, "AAVE": 5.0,
              "NEAR": 5.0, "ARB": 6.0, "OP": 6.0, "POL": 6.0, "SUI": 7.0, "INJ": 7.0,
              "RENDER": 7.0, "FET": 8.0, "TIA": 8.0, "HBAR": 8.0, "STX": 10.0, "KAS": 12.0}
        return _S.get(pair.split("/")[0].upper(), 12.0) / 1e4

DATA_DIR = Path("/freqtrade/user_data/data/kraken")
TF = "1h"        # match the strategy timeframe the model reads atr_pct from
FLAG_BPS = 15.0  # |divergence| above this (bps) gets flagged


def _atr_pct_at(df: pd.DataFrame, when) -> float:
    """ATR(14)/close on the candle at-or-before `when`."""
    sub = df[df["date"] <= when]
    if len(sub) < 20:
        return 0.01
    c = sub["close"]
    h, l = sub["high"], sub["low"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
    close = c.iloc[-1]
    return float(atr / close) if close else 0.01


def _ref_typical(df: pd.DataFrame, when) -> float | None:
    sub = df[df["date"] <= when]
    if not len(sub):
        return None
    c = sub.iloc[-1]
    return float((c["high"] + c["low"] + c["close"]) / 3)


def load_candles(pair: str) -> pd.DataFrame | None:
    f = DATA_DIR / f"{pair.replace('/', '_')}-{TF}.feather"
    if not f.exists():
        return None
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.sort_values("date").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/freqtrade/user_data/tradesv3_qe.sqlite",
                    help="path or sqlite:/// URL to the dry-run trades DB")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    db_path = args.db.replace("sqlite:///", "").replace("sqlite://", "") or args.db
    if not Path(db_path).exists():
        print(f"DB not found: {db_path} (start the dry-run first, then re-run this audit).")
        return

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT pair, open_rate, close_rate, open_date, close_date, close_profit_abs "
        "FROM trades WHERE is_open=0 ORDER BY close_date DESC LIMIT ?", (args.limit,)
    ).fetchall()
    con.close()
    if not rows:
        print("No closed trades yet — let the dry-run accumulate fills, then re-run.")
        return

    cache: dict[str, pd.DataFrame | None] = {}
    recs = []
    for r in rows:
        pair = r["pair"]
        if pair not in cache:
            cache[pair] = load_candles(pair)
        df = cache[pair]
        if df is None:
            continue
        ot = pd.to_datetime(r["open_date"], utc=True)
        ct = pd.to_datetime(r["close_date"], utc=True)
        model_one_way = (kraken_half_spread_frac(pair) + ATR_COEF * _atr_pct_at(df, ot)) * 1e4  # bps

        for side, when, rate, sgn in (("entry", ot, r["open_rate"], +1),
                                      ("exit", ct, r["close_rate"], -1)):
            ref = _ref_typical(df, when)
            if not ref:
                continue
            # adverse = paying above typical on entry, receiving below typical on exit
            actual_bps = sgn * (rate - ref) / ref * 1e4
            recs.append({
                "pair": pair, "side": side,
                "actual_bps": round(actual_bps, 1),
                "model_bps": round(model_one_way, 1),
                "diverge_bps": round(actual_bps - model_one_way, 1),
            })

    if not recs:
        print("No fills could be matched to Kraken candles (is user_data/data/kraken fresh? "
              "run download-data for kraken via --dl-trades).")
        return

    res = pd.DataFrame(recs)
    pd.set_option("display.width", 160)

    print("=" * 76)
    print("PER-PAIR: actual vs MODELLED one-way slippage (bps)  [+diverge => Kraken worse]")
    print("=" * 76)
    agg = res.groupby("pair").agg(
        fills=("actual_bps", "size"),
        actual=("actual_bps", "mean"),
        model=("model_bps", "mean"),
        diverge=("diverge_bps", "mean"),
    ).round(1).sort_values("diverge", ascending=False)
    print(agg.to_string())

    flagged = agg[agg["diverge"].abs() > FLAG_BPS]
    print("\n" + "=" * 76)
    print(f"FLAGGED (|divergence| > {FLAG_BPS} bps) — model needs recalibration here")
    print("=" * 76)
    print(flagged.to_string() if len(flagged) else "  none — model matches live fills well.")

    overall = res["diverge_bps"].mean()
    print(f"\nOverall mean divergence: {overall:+.1f} bps "
          f"({'real Kraken WORSE than model — tighten the model' if overall > 2 else 'real Kraken better/at model — model is conservative' if overall < -2 else 'model well-calibrated'}).")

    out = Path("/freqtrade/user_data/scripts/fill_audit_results.json")
    out.write_text(json.dumps(recs, indent=2, default=str))
    print(f"Saved {len(recs)} fill records -> {out}")


if __name__ == "__main__":
    main()
