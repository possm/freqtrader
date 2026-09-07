import pandas as pd
import numpy as np
import os
import talib.abstract as ta

data_dir = "/freqtrade/project/user_data/data/binance"
pairs = ["SOL", "NEAR", "FET", "HBAR", "ADA", "LINK", "INJ", "SUI", "ARB", "TIA", "OP", "RENDER", "STX"]

# Load BTC
df_btc = pd.read_feather(os.path.join(data_dir, "BTC_USDT-1h.feather"))
df_btc["date"] = pd.to_datetime(df_btc["date"])
df_btc["btc_ema200"] = ta.EMA(df_btc, timeperiod=200)
df_btc["btc_bull"] = (df_btc["close"] > df_btc["btc_ema200"]).astype(int)
df_btc["btc_ret_24h"] = df_btc["close"].pct_change(24)
btc_bull_map = dict(zip(df_btc["date"], df_btc["btc_bull"]))
btc_ret_map = dict(zip(df_btc["date"], df_btc["btc_ret_24h"]))

def evaluate_asymmetric_strategy(donch_len=36, pvr_th=1.12, vol_factor=1.45, rs_th=0.03, 
                                 tp1=0.08, tp2=0.18, trail_offset=0.10, trail_dist=0.04, sl=-0.05,
                                 fee=0.0032):
    all_trades = []
    
    for pair in pairs:
        fpath = os.path.join(data_dir, f"{pair}_USDT-1h.feather")
        if not os.path.exists(fpath):
            continue
        df = pd.read_feather(fpath)
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= "2024-01-01") & (df["date"] <= "2024-12-31")].reset_index(drop=True)
        if len(df) < 250:
            continue
            
        safe_low = df["low"].clip(lower=1e-8)
        ratio = (df["high"] / safe_low).clip(lower=1.0)
        log_hl = np.log(ratio)
        p_var = (log_hl ** 2) / (4.0 * np.log(2.0))
        df["pv_fast"] = np.sqrt(p_var.rolling(10).mean())
        df["pv_slow"] = np.sqrt(p_var.rolling(30).mean())
        df["pvr"] = df["pv_fast"] / (df["pv_slow"] + 1e-9)
        
        df["donch_high"] = df["high"].shift(1).rolling(donch_len).max()
        df["donch_low"] = df["low"].shift(1).rolling(donch_len).min()
        df["donch_mid"] = (df["donch_high"] + df["donch_low"]) / 2.0
        
        df["atr"] = ta.ATR(df, timeperiod=14)
        df["ema20"] = ta.EMA(df, timeperiod=20)
        df["keltner_upper"] = df["ema20"] + 1.42 * df["atr"]
        df["ema_trend"] = ta.EMA(df, timeperiod=150)
        
        df["vol_sma"] = df["volume"].rolling(20).mean()
        df["rvol"] = df["volume"] / (df["vol_sma"] + 1e-9)
        
        df["btc_bull"] = df["date"].map(btc_bull_map).fillna(0)
        df["btc_ret"] = df["date"].map(btc_ret_map).fillna(0)
        df["pair_ret_24h"] = df["close"].pct_change(24)
        df["rel_strength"] = df["pair_ret_24h"] - df["btc_ret"]
        
        entry_cond = (
            (df["close"] > df["donch_high"]) &
            (df["close"] > df["keltner_upper"]) &
            (df["pvr"] > pvr_th) &
            (df["rvol"] > vol_factor) &
            (df["close"] > df["ema_trend"]) &
            (df["btc_bull"] == 1) &
            (df["rel_strength"] > rs_th) &
            (df["volume"] > 0)
        )
        
        in_trade = False
        entry_price = 0
        entry_idx = 0
        highest_price = 0
        
        for i in range(1, len(df)):
            if not in_trade:
                if entry_cond.iloc[i-1]:
                    in_trade = True
                    entry_price = df["open"].iloc[i]
                    entry_idx = i
                    highest_price = entry_price
            else:
                bars = i - entry_idx
                cur_high = df["high"].iloc[i]
                cur_low = df["low"].iloc[i]
                cur_close = df["close"].iloc[i]
                if cur_high > highest_price:
                    highest_price = cur_high
                    
                profit = (highest_price - entry_price) / entry_price
                
                # Invalidation cut: if after 6 hours close is below entry price by > 2%
                if bars >= 6 and cur_close < entry_price * 0.98:
                    exit_p = cur_close
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee, "reason": "invalidation"})
                    in_trade = False
                    continue
                    
                # Hard stoploss
                if (cur_low - entry_price) / entry_price <= sl:
                    exit_p = entry_price * (1.0 + sl)
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee, "reason": "sl"})
                    in_trade = False
                    continue
                    
                # Trailing stop
                if profit >= trail_offset:
                    trail_level = highest_price * (1.0 - trail_dist)
                    if cur_low <= trail_level:
                        exit_p = trail_level
                        all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee, "reason": "trail"})
                        in_trade = False
                        continue
                        
                # Exit on midline break after 12 bars
                if bars >= 12 and cur_close < df["donch_mid"].iloc[i]:
                    exit_p = cur_close
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee, "reason": "midline"})
                    in_trade = False
                    continue
                    
                # Max hold 120 hours (5 days)
                if bars >= 120:
                    exit_p = cur_close
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee, "reason": "timeout"})
                    in_trade = False
                    continue

    tdf = pd.DataFrame(all_trades)
    if len(tdf) == 0:
        return None
    wins = tdf[tdf["ret"] > 0]
    losses = tdf[tdf["ret"] <= 0]
    win_rate = len(wins) / len(tdf) * 100
    avg_win = wins["ret"].mean() * 100 if len(wins) > 0 else 0
    avg_loss = losses["ret"].mean() * 100 if len(losses) > 0 else 0
    avg_trade_net = tdf["ret"].mean() * 100
    pf = abs(wins["ret"].sum() / losses["ret"].sum()) if len(losses) > 0 and losses["ret"].sum() != 0 else 0
    monthly_trades = len(tdf) / 12.0
    
    # Compounding calculation per month
    tdf["month"] = pd.to_datetime(tdf["date"]).dt.strftime("%Y-%m")
    m_rets = []
    for m, grp in tdf.groupby("month"):
        bal = 1.0
        for r in grp["ret"]:
            bal *= (1.0 + 0.22 * r) # 22% stake per trade
        m_rets.append((bal - 1.0) * 100)
    
    mean_mo = np.mean(m_rets)
    med_mo = np.median(m_rets)
    ann_ret = (np.prod([1.0 + x/100.0 for x in m_rets]) - 1.0) * 100
    
    return {
        "trades": len(tdf),
        "monthly_trades": monthly_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_trade_net": avg_trade_net,
        "pf": pf,
        "mean_monthly_ret": mean_mo,
        "med_monthly_ret": med_mo,
        "ann_ret": ann_ret
    }

print("Running Asymmetric Payoff Grid...")
for sl_val in [-0.04, -0.05, -0.06]:
    for toff, tdist in [(0.08, 0.035), (0.10, 0.04), (0.12, 0.05)]:
        for rs in [0.02, 0.03]:
            r = evaluate_asymmetric_strategy(sl=sl_val, trail_offset=toff, trail_dist=tdist, rs_th=rs, fee=0.0032)
            if r:
                print(f"SL={sl_val} | Trail={toff}/{tdist} | RS={rs} -> MoTrades: {r['monthly_trades']:.1f} | WR: {r['win_rate']:.1f}% | AvgWin: +{r['avg_win']:.2f}% | AvgLoss: {r['avg_loss']:.2f}% | Payoff: {abs(r['avg_win']/r['avg_loss']):.2f} | PF: {r['pf']:.2f} | MeanMonthly: {r['mean_monthly_ret']:.2f}% | Annual: {r['ann_ret']:.1f}%")
