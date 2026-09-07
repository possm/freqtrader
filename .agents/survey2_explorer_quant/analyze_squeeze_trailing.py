import pandas as pd
import numpy as np
import os
import talib.abstract as ta

data_dir = "/freqtrade/project/user_data/data/binance"
pairs = ["SOL", "NEAR", "FET", "HBAR", "ADA", "LINK", "INJ", "SUI", "ARB", "TIA", "OP", "RENDER", "STX"]

def test_model(name, entry_fn, exit_fn):
    all_trades = []
    
    # Load BTC 1h & 4h
    df_btc = pd.read_feather(os.path.join(data_dir, "BTC_USDT-1h.feather"))
    df_btc["date"] = pd.to_datetime(df_btc["date"])
    df_btc["btc_ema200"] = ta.EMA(df_btc, timeperiod=200)
    df_btc["btc_bull"] = (df_btc["close"] > df_btc["btc_ema200"]).astype(int)
    btc_map = dict(zip(df_btc["date"], df_btc["btc_bull"]))
    
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
        df["atr"] = ta.ATR(df, timeperiod=14)
        df["atr_pct"] = df["atr"] / df["close"]
        df["ema20"] = ta.EMA(df, timeperiod=20)
        df["ema50"] = ta.EMA(df, timeperiod=50)
        df["ema100"] = ta.EMA(df, timeperiod=100)
        df["rsi"] = ta.RSI(df, timeperiod=14)
        
        # Bollinger Bands & Keltner Channels
        std = df["close"].rolling(20).std()
        df["bb_upper"] = df["ema20"] + 2.0 * std
        df["bb_lower"] = df["ema20"] - 2.0 * std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["ema20"]
        df["kc_upper"] = df["ema20"] + 1.5 * df["atr"]
        df["kc_lower"] = df["ema20"] - 1.5 * df["atr"]
        
        # Squeeze: BB inside KC
        df["squeeze"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
        df["squeeze_prior_8"] = df["squeeze"].shift(1).rolling(8).max()
        
        # Parkinson Volatility
        safe_low = df["low"].clip(lower=1e-8)
        ratio = (df["high"] / safe_low).clip(lower=1.0)
        log_hl = np.log(ratio)
        p_var = (log_hl ** 2) / (4.0 * np.log(2.0))
        df["pv_fast"] = np.sqrt(p_var.rolling(10).mean())
        df["pv_slow"] = np.sqrt(p_var.rolling(30).mean())
        df["pvr"] = df["pv_fast"] / (df["pv_slow"] + 1e-9)
        
        # Donchian
        df["donch_high_20"] = df["high"].shift(1).rolling(20).max()
        df["donch_low_20"] = df["low"].shift(1).rolling(20).min()
        df["donch_mid_20"] = (df["donch_high_20"] + df["donch_low_20"]) / 2.0
        
        # Volume
        df["vol_sma"] = df["volume"].rolling(20).mean()
        df["rvol"] = df["volume"] / (df["vol_sma"] + 1e-9)
        
        # BTC macro
        df["btc_bull"] = df["date"].map(btc_map).fillna(0)
        
        entries = entry_fn(df)
        
        # Simulation
        in_trade = False
        entry_price = 0
        entry_idx = 0
        highest_price = 0
        stop_price = 0
        
        for i in range(1, len(df)):
            if not in_trade:
                if entries.iloc[i-1]:
                    in_trade = True
                    entry_price = df["open"].iloc[i]
                    entry_idx = i
                    highest_price = entry_price
            else:
                bars_held = i - entry_idx
                cur_high = df["high"].iloc[i]
                cur_low = df["low"].iloc[i]
                cur_close = df["close"].iloc[i]
                if cur_high > highest_price:
                    highest_price = cur_high
                    
                exit_signal, exit_price, reason = exit_fn(df, i, entry_price, highest_price, bars_held)
                if exit_signal:
                    ret = (exit_price - entry_price) / entry_price
                    ret_net = ret - 0.0052 # 0.52% Kraken roundtrip fee
                    all_trades.append({
                        "pair": pair,
                        "ret_gross": ret,
                        "ret_net": ret_net,
                        "bars": bars_held,
                        "reason": reason,
                    })
                    in_trade = False

    tdf = pd.DataFrame(all_trades)
    if len(tdf) == 0:
        print(f"[{name}] No trades generated")
        return
        
    wins = tdf[tdf["ret_net"] > 0]
    losses = tdf[tdf["ret_net"] <= 0]
    win_rate = len(wins) / len(tdf) * 100
    avg_net_ret = tdf["ret_net"].mean() * 100
    avg_gross_ret = tdf["ret_gross"].mean() * 100
    avg_win = wins["ret_net"].mean() * 100 if len(wins) > 0 else 0
    avg_loss = losses["ret_net"].mean() * 100 if len(losses) > 0 else 0
    monthly_trades = len(tdf) / 12.0
    
    # Portfolio monthly return with 6 open slots (16.6% per trade, compounding)
    # R_monthly = (1 + s * R_net)^(N_monthly) - 1
    # Simple approx: monthly_trades * 0.16 * avg_net_ret
    port_monthly_ret = monthly_trades * 0.16 * avg_net_ret
    profit_factor = abs(wins["ret_net"].sum() / losses["ret_net"].sum()) if len(losses) > 0 and losses["ret_net"].sum() != 0 else np.nan
    
    print(f"==================================================")
    print(f"Model: {name}")
    print(f"Total Trades: {len(tdf)} ({monthly_trades:.1f}/month)")
    print(f"Win Rate: {win_rate:.1f}% | Profit Factor: {profit_factor:.2f}")
    print(f"Avg Gross Ret: {avg_gross_ret:.2f}% | Avg Net Ret: {avg_net_ret:.2f}%")
    print(f"Avg Win: +{avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
    print(f"Portfolio Monthly Net Return (stake=16%): {port_monthly_ret:.2f}%")
    print(f"==================================================\n")

# Model 1: Dynamic Donchian Breakout + Squeeze Expansion + Trailing Stop
def entry_m1(df):
    return (
        (df["close"] > df["donch_high_20"]) &
        (df["squeeze_prior_8"] == 1) &
        (df["rvol"] > 1.3) &
        (df["close"] > df["ema50"]) &
        (df["btc_bull"] == 1) &
        (df["volume"] > 0)
    )

def exit_m1(df, i, entry_price, highest_price, bars_held):
    cur_low = df["low"].iloc[i]
    cur_close = df["close"].iloc[i]
    atr = df["atr"].iloc[i]
    
    # Initial Stop: 2 * ATR below entry
    init_sl = entry_price - 2.2 * atr
    if cur_low <= init_sl and highest_price < entry_price * 1.03:
        return True, init_sl, "init_sl"
        
    # Profit target tier 1: +5%
    # If profit >= 4.5%, activate tight trailing stop at highest_price - 1.8 * atr
    if highest_price >= entry_price * 1.045:
        trail_stop = highest_price - 1.8 * atr
        if cur_low <= trail_stop:
            return True, max(trail_stop, entry_price * 1.01), "trail_profit"
            
    # Breakdown below ema20 after 6 bars
    if bars_held >= 6 and cur_close < df["ema20"].iloc[i]:
        return True, cur_close, "ema20_break"
        
    # Hard timeout
    if bars_held >= 48:
        return True, cur_close, "timeout"
        
    return False, 0, None

# Model 2: Volatility Explosion + Relative Strength + Trailing Runner
def entry_m2(df):
    return (
        (df["close"] > df["kc_upper"]) &
        (df["pvr"] > 1.12) &
        (df["rvol"] > 1.4) &
        (df["close"] > df["ema100"]) &
        (df["rsi"] > 55) &
        (df["btc_bull"] == 1) &
        (df["volume"] > 0)
    )

def exit_m2(df, i, entry_price, highest_price, bars_held):
    cur_low = df["low"].iloc[i]
    cur_close = df["close"].iloc[i]
    atr = df["atr"].iloc[i]
    
    # Stoploss: 2.5 * ATR below entry
    init_sl = entry_price - 2.5 * atr
    if cur_low <= init_sl and highest_price < entry_price * 1.03:
        return True, init_sl, "init_sl"
        
    # Trailing Stop: once +5% reached, lock trailing 2.0 * atr
    if highest_price >= entry_price * 1.05:
        trail_stop = highest_price - 2.0 * atr
        if cur_low <= trail_stop:
            return True, trail_stop, "trail_profit"
            
    # Trend break
    if bars_held >= 12 and cur_close < df["donch_mid_20"].iloc[i]:
        return True, cur_close, "mid_break"
        
    if bars_held >= 60:
        return True, cur_close, "timeout"
        
    return False, 0, None

# Model 3: Momentum Impulse Continuation (Fast Invalidation + Fat Tail Runner)
def entry_m3(df):
    # Candle must be strong bullish bar closing in top 25% of range with volume
    candle_range = df["high"] - df["low"]
    bullish_bar = (df["close"] - df["low"]) > 0.75 * candle_range
    return (
        (df["close"] > df["donch_high_20"]) &
        bullish_bar &
        (df["rvol"] > 1.5) &
        (df["pvr"] > 1.10) &
        (df["close"] > df["ema50"]) &
        (df["btc_bull"] == 1) &
        (df["volume"] > 0)
    )

def exit_m3(df, i, entry_price, highest_price, bars_held):
    cur_low = df["low"].iloc[i]
    cur_close = df["close"].iloc[i]
    atr = df["atr"].iloc[i]
    
    # Invalidation Cut: if within 4 bars close drops below entry - 1.2 * ATR
    if bars_held <= 4 and cur_close < (entry_price - 1.2 * atr):
        return True, cur_close, "fast_invalidation"
        
    # Normal Stoploss: 2.0 * ATR
    if cur_low <= (entry_price - 2.0 * atr):
        return True, entry_price - 2.0 * atr, "sl"
        
    # Stepped Trailing Profit:
    # Tier 1: at +4%, stop moves to breakeven + 0.6% (covers fee!)
    profit_pct = (highest_price - entry_price) / entry_price
    if profit_pct >= 0.08: # Tier 2: at +8%, trail at highest - 2.5%
        trail = highest_price * 0.975
        if cur_low <= trail:
            return True, trail, "trail_high"
    elif profit_pct >= 0.04:
        trail = entry_price * 1.008 # breakeven + fee safe
        if cur_low <= trail:
            return True, trail, "be_lock"
            
    if bars_held >= 40:
        return True, cur_close, "timeout"
        
    return False, 0, None

test_model("M1: Squeeze Expansion Breakout", entry_m1, exit_m1)
test_model("M2: Volatility Explosion PVR", entry_m2, exit_m2)
test_model("M3: Momentum Impulse Continuation (Breakeven Lock + Runner)", entry_m3, exit_m3)
