#!/usr/bin/env python3
"""
discover_signals.py — Phase 2 data-driven signal discovery.

GOAL
----
Before writing a single line of strategy logic, find out which candidate entry signals
*actually* carry forward-return edge on our universe — and crucially, whether that edge
survives the Kraken execution tax modelled in kraken_slippage.py. We do NOT want to hand-tune
yet another indicator stack from priors; we want the data to tell us what works, and in which
market regime.

METHOD
------
For every pair (1h candles), compute a regime label and a battery of LONG candidate signals,
then measure the distribution of forward returns over several horizons AFTER each signal fires.
We report, pooled across all pairs and split by regime + BTC trend:

    n            how many signal events (sample size — small n => ignore)
    mean%        average forward return at the horizon (gross)
    net%         mean MINUS the modelled round-trip Kraken cost (spread+vol-slip+impact)*2
    hit%         share of events with positive forward return
    t            mean / (std/sqrt(n))  — rough significance (see CAVEAT)

A signal is "interesting" only if NET edge is positive with a sane t (>~2-3) and enough n,
and ideally in the regime theory predicts (mean-reversion in RANGE, breakout in TREND).

CAVEAT: overlapping forward windows autocorrelate, so |t| is optimistic. We lean on economic
magnitude (net%) and hit% too, and treat this as a *screen* — Phase 3's slippage-on backtest
is the real arbiter.

REGIME (Kaufman Efficiency Ratio, ER10 on 1h):
    ER = |close - close[-n]| / sum(|Δclose|, n).  ER high => directional/trending; low => choppy.
    label: trend if ER>0.45, range if ER<0.30, else mid.  (ADX14 reported alongside as a check.)

RUN (on the VPS, inside the freqtrade container which has pandas/numpy/talib):
    docker exec freqtrade-wolf python3 /freqtrade/user_data/scripts/discover_signals.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.simplefilter("ignore")

DATA = Path("/freqtrade/user_data/data/binance")
TF = os.environ.get("DISC_TF", "1h")     # DISC_TF=4h python3 discover_signals.py
PAIRS = ["AAVE", "ADA", "ARB", "BTC", "ETH", "FET", "HBAR", "INJ", "LINK",
         "NEAR", "OP", "POL", "RENDER", "SOL", "STX", "SUI", "TIA"]
# forward-return horizons in BARS, chosen per timeframe so we probe ~4h .. ~8d holds
HORIZONS = {
    "5m":  [12, 48, 144, 288],            # 1h, 4h, 12h, 1d
    "15m": [8, 32, 96, 192],              # 2h, 8h, 1d, 2d
    "1h":  [4, 8, 24, 48, 96],            # 4h, 8h, 1d, 2d, 4d
    "4h":  [3, 6, 12, 24, 48],            # 12h, 1d, 2d, 4d, 8d
}.get(TF, [4, 8, 24, 48])
ER_N = 10
ZWIN = 50                          # rolling window for z-score / vwap-dev z
VWAP_WIN = 24                      # rolling VWAP window (1 day on 1h)

# --- pull the EXACT cost model from the slippage mixin (single source of truth) -------------
sys.path.insert(0, "/freqtrade/user_data/strategies")
try:
    from kraken_slippage import kraken_half_spread_frac, KrakenSlippageMixin as _M
    ATR_COEF = _M.SLIP_ATR_COEF
except Exception:                  # fallback if import path differs
    ATR_COEF = 0.08
    _SPREAD = {"BTC": 1.5, "ETH": 2.0, "SOL": 3.0, "LINK": 4.0, "ADA": 4.0, "AAVE": 5.0,
               "NEAR": 5.0, "ARB": 6.0, "OP": 6.0, "POL": 6.0, "SUI": 7.0, "INJ": 7.0,
               "RENDER": 7.0, "FET": 8.0, "TIA": 8.0, "HBAR": 8.0, "STX": 10.0, "KAS": 12.0}
    def kraken_half_spread_frac(pair):  # noqa: E306
        return _SPREAD.get(pair.split("/")[0].upper(), 12.0) / 1e4

FEE_PER_SIDE = 0.0026              # Kraken taker; round-trip commission = 2*this


# --- lightweight TA (no talib dependency needed) --------------------------------------------
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up, dn = h.diff(), -l.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_ = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def kaufman_er(close: pd.Series, n: int = ER_N) -> pd.Series:
    change = (close - close.shift(n)).abs()
    vol = close.diff().abs().rolling(n).sum()
    return change / vol.replace(0, np.nan)


def load(pair_base: str, tf: str = TF) -> pd.DataFrame | None:
    f = DATA / f"{pair_base}_USDT-{tf}.feather"
    if not f.exists():
        return None
    df = pd.read_feather(f).sort_values("date").reset_index(drop=True)
    return df


def build(pair_base: str) -> pd.DataFrame | None:
    df = load(pair_base)
    if df is None or len(df) < 600:
        return None
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    df["atr"] = atr(df, 14)
    df["atr_pct"] = (df["atr"] / c).clip(0.0005, 0.25)
    df["ema20"] = ema(c, 20)
    df["ema50"] = ema(c, 50)
    df["ema200"] = ema(c, 200)
    df["er"] = kaufman_er(c)
    df["adx"] = adx(df, 14)

    # z-score of price vs rolling mean
    m, sd = c.rolling(ZWIN).mean(), c.rolling(ZWIN).std()
    df["zscore"] = (c - m) / sd.replace(0, np.nan)

    # rolling VWAP deviation, then z-score of the deviation
    tp = (h + l + c) / 3
    vwap = (tp * v).rolling(VWAP_WIN).sum() / v.rolling(VWAP_WIN).sum()
    dev = (c - vwap) / vwap
    df["vwap_dev_z"] = (dev - dev.rolling(ZWIN).mean()) / dev.rolling(ZWIN).std().replace(0, np.nan)

    # Keltner channel + volatility expansion
    df["kelt_up"] = df["ema20"] + 2 * df["atr"]
    df["atr_expand"] = df["atr"] > df["atr"].rolling(20).mean()

    # Donchian breakout
    df["donch_hi"] = h.rolling(20).max()

    # volume z and signed-volume imbalance
    df["vol_z"] = (v - v.rolling(ZWIN).mean()) / v.rolling(ZWIN).std().replace(0, np.nan)
    signed = np.sign(c - df["close"].shift()) * v
    df["vol_imb"] = signed.rolling(10).sum() / v.rolling(10).sum().replace(0, np.nan)

    # regime label from Kaufman ER
    df["regime"] = np.where(df["er"] > 0.45, "trend",
                            np.where(df["er"] < 0.30, "range", "mid"))

    # per-row modelled round-trip Kraken cost: 2*(half_spread + ATR_COEF*atr_pct)  [impact~0 at our size]
    hs = kraken_half_spread_frac(f"{pair_base}/USDT")
    df["rt_cost"] = 2 * (hs + ATR_COEF * df["atr_pct"]) + 2 * FEE_PER_SIDE

    # forward returns
    for k in HORIZONS:
        df[f"fwd{k}"] = c.shift(-k) / c - 1.0
    return df


# --- candidate LONG signals: name -> boolean mask builder -----------------------------------
SIGNALS = {
    "mr_zscore<-2":   lambda d: d["zscore"] < -2.0,
    "mr_vwapdev<-2":  lambda d: d["vwap_dev_z"] < -2.0,
    "bo_keltner+exp": lambda d: (d["close"] > d["kelt_up"]) & d["atr_expand"],
    "bo_donchian20":  lambda d: d["close"] > d["donch_hi"].shift(1),
    "volimb>0.4":     lambda d: d["vol_imb"] > 0.4,
}


def main():
    frames = []
    loaded = []
    for p in PAIRS:
        d = build(p)
        if d is not None:
            d["pair"] = p
            frames.append(d)
            loaded.append(p)
    if not frames:
        print("No data built.")
        return
    big = pd.concat(frames, ignore_index=True)
    # BTC trend context from BTC's own 1h ema200 (proxy; strategy will use 4h informative)
    print(f"### TIMEFRAME={TF}  horizons(bars)={HORIZONS}")
    print(f"Loaded {len(loaded)} pairs: {', '.join(loaded)}   rows={len(big):,}\n")
    print(f"Regime mix: " + ", ".join(f"{k}={v/len(big)*100:.0f}%"
          for k, v in big['regime'].value_counts().items()) + "\n")

    rows = []
    for sig_name, fn in SIGNALS.items():
        mask = fn(big).fillna(False)
        for reg in ["all", "trend", "range", "mid"]:
            sub = big[mask] if reg == "all" else big[mask & (big["regime"] == reg)]
            if len(sub) < 30:
                continue
            for k in HORIZONS:
                fr = sub[f"fwd{k}"].dropna()
                if len(fr) < 30:
                    continue
                cost = sub.loc[fr.index, "rt_cost"]
                net = fr - cost
                n = len(fr)
                t = fr.mean() / (fr.std() / np.sqrt(n)) if fr.std() > 0 else 0.0
                rows.append({
                    "signal": sig_name, "regime": reg, "h(bars)": k, "n": n,
                    "mean%": round(fr.mean() * 100, 3),
                    "net%": round(net.mean() * 100, 3),
                    "hit%": round((fr > 0).mean() * 100, 1),
                    "t": round(t, 1),
                })
    res = pd.DataFrame(rows)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_rows", 400)

    print("=" * 92)
    print("ALL CANDIDATE SIGNAL × REGIME × HORIZON  (sorted by net% within each signal)")
    print("=" * 92)
    for sig_name in SIGNALS:
        block = res[res["signal"] == sig_name].sort_values("net%", ascending=False)
        if len(block):
            print("\n" + block.to_string(index=False))

    print("\n" + "=" * 92)
    print("TOP 15 BY NET EDGE (n>=100, net%>0) — the survivors of the Kraken tax")
    print("=" * 92)
    win = res[(res["n"] >= 100) & (res["net%"] > 0)].sort_values("net%", ascending=False).head(15)
    print(win.to_string(index=False) if len(win) else "  (none cleared the bar — signals/thresholds need rework)")

    out = Path(f"/freqtrade/user_data/scripts/discovery_results_{TF}.csv")
    res.to_csv(out, index=False)
    print(f"\nSaved full grid -> {out}")


if __name__ == "__main__":
    main()
