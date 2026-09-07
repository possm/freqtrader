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

def run_simulation(donch_len=36, kelt_mult=1.42, pvr_th=1.12, vol_factor=1.45, ema_trend_len=150, 
                   use_rs=True, rs_th=0.02, sl=-0.08, exit_mid=True, roi_target=0.15):
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
            
        # Indicators
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
        df["ema_trend"] = ta.EMA(df, timeperiod=ema_trend_len)
        
        df["vol_sma"] = df["volume"].rolling(20).mean()
        df["rvol"] = df["volume"] / (df["vol_sma"] + 1e-9)
        
        df["btc_bull"] = df["date"].map(btc_bull_map).fillna(0)
        df["btc_ret"] = df["date"].map(btc_ret_map).fillna(0)
        df["pair_ret_24h"] = df["close"].pct_change(24)
        df["rel_strength"] = df["pair_ret_24h"] - df["btc_ret"]
        
        # Entry rule
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
                    
                # Exits:
                # 1. Hard SL
                if (cur_low - entry_price) / entry_price <= sl:
                    exit_p = entry_price * (1.0 + sl)
                    reason = "sl"
                    all_trades.append({"pair": pair, "ret": (exit_p - entry_price)/entry_price - 0.0052, "bars": bars, "reason": reason})
                    in_trade = False
                    continue
                    
                # 2. ROI target
                if (cur_high - entry_price) / entry_price >= roi_target:
                    exit_p = entry_price * (1.0 + roi_target)
                    reason = "roi"
                    all_trades.append({"pair": pair, "ret": (exit_p - entry_price)/entry_price - 0.0052, "bars": bars, "reason": reason})
                    in_trade = False
                    continue
                    
                # 3. Donchian Midline
                if exit_mid and cur_close < df["donch_mid"].iloc[i]:
                    exit_p = cur_close
                    reason = "midline"
                    all_trades.append({"pair": pair, "ret": (exit_p - entry_price)/entry_price - 0.0052, "bars": bars, "reason": reason})
                    in_trade = False
                    continue
                    
                # 4. Stale exit after 14 days (336 hours)
                if bars >= 336:
                    exit_p = cur_close
                    reason = "stale"
                    all_trades.append({"pair": pair, "ret": (exit_p - entry_price)/entry_price - 0.0052, "bars": bars, "reason": reason})
                    in_trade = False
                    continue

    tdf = pd.DataFrame(all_trades)
    if len(tdf) == 0:
        return 0, 0, 0, 0, 0
    wins = tdf[tdf["ret"] > 0]
    wr = len(wins) / len(tdf) * 100
    avg_ret = tdf["ret"].mean() * 100
    n_mo = len(tdf) / 12.0
    p_fact = abs(wins["ret"].sum() / tdf[tdf["ret"]<=0]["ret"].sum()) if len(tdf[tdf["ret"]<=0]) > 0 else 0
    mo_p = n_mo * 0.16 * avg_ret
    return len(tdf), n_mo, wr, avg_ret, mo_p, p_fact

print(f"{'Donch':<6} {'RS?':<5} {'SL':<6} {'ROI':<6} {'Trades':<8} {'MoTrades':<10} {'WinRate':<8} {'AvgRet%':<8} {'MoPort%':<8} {'PF':<6}")
for donch in [24, 30, 36]:
    for rs in [False, True]:
        for sl in [-0.06, -0.08, -0.12]:
            for roi in [0.12, 0.18, 0.25]:
                cnt, n_mo, wr, avg_ret, mo_p, pf = run_simulation(donch_len=donch, use_rs=rs, rs_th=0.03, sl=sl, roi_target=roi)
                if cnt > 0 and mo_p > 0:
                    print(f"{donch:<6} {str(rs):<5} {sl:<6} {roi:<6} {cnt:<8} {n_mo:<10.1f} {wr:<8.1f} {avg_ret:<8.2f} {mo_p:<8.2f} {pf:<6.2f}")
