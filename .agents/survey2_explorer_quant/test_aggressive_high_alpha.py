import pandas as pd
import numpy as np
import os
import talib.abstract as ta

data_dir = "/freqtrade/project/user_data/data/binance"
pairs = ["SOL", "NEAR", "FET", "HBAR", "ADA", "LINK", "INJ", "SUI", "ARB", "TIA", "OP", "RENDER", "STX"]

# Load BTC 1h
df_btc = pd.read_feather(os.path.join(data_dir, "BTC_USDT-1h.feather"))
df_btc["date"] = pd.to_datetime(df_btc["date"])
df_btc["btc_ema200"] = ta.EMA(df_btc, timeperiod=200)
df_btc["btc_bull"] = (df_btc["close"] > df_btc["btc_ema200"]).astype(int)
df_btc["btc_ret_24h"] = df_btc["close"].pct_change(24)
btc_bull_map = dict(zip(df_btc["date"], df_btc["btc_bull"]))
btc_ret_map = dict(zip(df_btc["date"], df_btc["btc_ret_24h"]))

def run_aggressive_sim(fee_roundtrip=0.0032, # Maker-Maker 0.16%*2 = 0.32% or 0.42% maker-taker
                       stake_pct=0.22,      # 4-5 max open trades (22% per trade)
                       donch_len=30,
                       kelt_mult=1.35,
                       pvr_th=1.08,
                       vol_factor=1.35,
                       use_rs=True,
                       rs_th=0.015,
                       sl=-0.07,
                       trail_act=0.12,
                       trail_dist=0.05,
                       exit_mid=True):
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
        df["keltner_upper"] = df["ema20"] + kelt_mult * df["atr"]
        df["ema_trend"] = ta.EMA(df, timeperiod=120)
        
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
            (df["volume"] > 0)
        )
        if use_rs:
            entry_cond = entry_cond & (df["rel_strength"] > rs_th)
            
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
                    
                profit_from_entry = (highest_price - entry_price) / entry_price
                
                # 1. Trailing Stop
                if profit_from_entry >= trail_act:
                    trail_level = highest_price * (1.0 - trail_dist)
                    if cur_low <= trail_level:
                        exit_p = trail_level
                        all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee_roundtrip, "reason": "trail"})
                        in_trade = False
                        continue
                        
                # 2. Hard Stoploss
                if (cur_low - entry_price) / entry_price <= sl:
                    exit_p = entry_price * (1.0 + sl)
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee_roundtrip, "reason": "sl"})
                    in_trade = False
                    continue
                    
                # 3. Donchian Midline
                if exit_mid and cur_close < df["donch_mid"].iloc[i]:
                    exit_p = cur_close
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee_roundtrip, "reason": "midline"})
                    in_trade = False
                    continue
                    
                # 4. Timeout
                if bars >= 168: # 7 days max hold
                    exit_p = cur_close
                    all_trades.append({"pair": pair, "date": df["date"].iloc[i], "ret": (exit_p - entry_price)/entry_price - fee_roundtrip, "reason": "timeout"})
                    in_trade = False
                    continue

    tdf = pd.DataFrame(all_trades)
    if len(tdf) == 0:
        return None
    tdf["month"] = tdf["date"].dt.to_period("M")
    
    # Calculate monthly compounding return
    monthly_stats = []
    for m, group in tdf.groupby("month"):
        m_trades = len(group)
        m_wins = group[group["ret"] > 0]
        m_wr = len(m_wins) / m_trades * 100
        # Compounded return across trades in the month:
        # Each trade risks stake_pct of wallet
        balance = 1.0
        for r in group["ret"]:
            balance *= (1.0 + stake_pct * r)
        net_m_ret = (balance - 1.0) * 100
        monthly_stats.append({
            "month": str(m),
            "trades": m_trades,
            "win_rate": m_wr,
            "net_monthly_pct": net_m_ret,
            "avg_ret": group["ret"].mean() * 100,
        })
        
    m_df = pd.DataFrame(monthly_stats)
    mean_m_ret = m_df["net_monthly_pct"].mean()
    med_m_ret = m_df["net_monthly_pct"].median()
    total_ann_ret = (np.prod([1.0 + x/100.0 for x in m_df["net_monthly_pct"]]) - 1.0) * 100
    
    return {
        "trades": len(tdf),
        "mean_monthly_trades": len(tdf) / len(m_df),
        "mean_monthly_ret": mean_m_ret,
        "median_monthly_ret": med_m_ret,
        "total_annual_compounded": total_ann_ret,
        "avg_trade_net": tdf["ret"].mean() * 100,
        "win_rate": len(tdf[tdf["ret"] > 0]) / len(tdf) * 100,
        "monthly_df": m_df
    }

# Test various parameterizations
print("Running parameter tests...")
for fee in [0.0032, 0.0042, 0.0052]:
    for stake in [0.20, 0.25]:
        for trail_a, trail_d in [(0.10, 0.04), (0.12, 0.05), (0.15, 0.06)]:
            res = run_aggressive_sim(fee_roundtrip=fee, stake_pct=stake, donch_len=30, trail_act=trail_a, trail_dist=trail_d)
            if res:
                print(f"Fee={fee*100:.2f}% | Stake={stake*100:.0f}% | TrailAct={trail_a*100:.0f}% | TrailDist={trail_d*100:.0f}% -> Mean Monthly: {res['mean_monthly_ret']:.2f}% | Med Monthly: {res['median_monthly_ret']:.2f}% | Annual: {res['total_annual_compounded']:.1f}% | WinRate: {res['win_rate']:.1f}% | AvgTrade: {res['avg_trade_net']:.2f}%")
