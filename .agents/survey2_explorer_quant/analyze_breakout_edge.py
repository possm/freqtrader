import pandas as pd
import numpy as np
import os
import talib.abstract as ta

data_dir = "/freqtrade/project/user_data/data/binance"
pairs = ["SOL", "NEAR", "FET", "HBAR", "ADA", "LINK", "INJ", "SUI", "ARB", "TIA", "OP", "RENDER", "STX"]

def analyze_strategy_edge(timeframe="1h", donchian_p=20, keltner_mult=1.5, pvr_thresh=1.1, rvol_thresh=1.5, tp_pct=0.05, sl_pct=0.025, max_hold=24):
    all_trades = []
    
    # Load BTC 1h for macro filter
    btc_file = os.path.join(data_dir, f"BTC_USDT-{timeframe}.feather")
    df_btc = pd.read_feather(btc_file)
    df_btc["date"] = pd.to_datetime(df_btc["date"])
    df_btc["btc_ema100"] = ta.EMA(df_btc, timeperiod=100)
    df_btc["btc_bull"] = (df_btc["close"] > df_btc["btc_ema100"]).astype(int)
    btc_map = dict(zip(df_btc["date"], df_btc["btc_bull"]))
    
    for pair in pairs:
        fpath = os.path.join(data_dir, f"{pair}_USDT-{timeframe}.feather")
        if not os.path.exists(fpath):
            continue
        df = pd.read_feather(fpath)
        df["date"] = pd.to_datetime(df["date"])
        # Filter to 2024
        df = df[(df["date"] >= "2024-01-01") & (df["date"] <= "2024-12-31")].reset_index(drop=True)
        if len(df) < 200:
            continue
            
        # Indicators
        safe_low = df["low"].clip(lower=1e-8)
        ratio = (df["high"] / safe_low).clip(lower=1.0)
        log_hl = np.log(ratio)
        p_var = (log_hl ** 2) / (4.0 * np.log(2.0))
        df["pv_fast"] = np.sqrt(p_var.rolling(10).mean())
        df["pv_slow"] = np.sqrt(p_var.rolling(30).mean())
        df["pvr"] = df["pv_fast"] / (df["pv_slow"] + 1e-9)
        
        df["donchian_high"] = df["high"].shift(1).rolling(donchian_p).max()
        df["atr"] = ta.ATR(df, timeperiod=14)
        df["ema20"] = ta.EMA(df, timeperiod=20)
        df["keltner_upper"] = df["ema20"] + keltner_mult * df["atr"]
        df["vol_sma"] = df["volume"].rolling(20).mean()
        df["rvol"] = df["volume"] / (df["vol_sma"] + 1e-9)
        df["ema_trend"] = ta.EMA(df, timeperiod=100)
        df["btc_bull"] = df["date"].map(btc_map).fillna(0)
        
        # Squeeze indicator (BB inside Keltner)
        std = df["close"].rolling(20).std()
        df["bb_upper"] = df["ema20"] + 2.0 * std
        df["bb_lower"] = df["ema20"] - 2.0 * std
        df["keltner_lower"] = df["ema20"] - keltner_mult * df["atr"]
        df["squeeze_on"] = (df["bb_lower"] > df["keltner_lower"]) & (df["bb_upper"] < df["keltner_upper"])
        df["squeeze_prior_5"] = df["squeeze_on"].shift(1).rolling(5).max()
        
        # Entry conditions:
        # 1. Breakout above donchian high or keltner upper
        # 2. PVR > threshold
        # 3. RVOL > threshold
        # 4. Above trend EMA
        # 5. BTC bull
        entry_mask = (
            (df["close"] > df["donchian_high"]) &
            (df["close"] > df["keltner_upper"]) &
            (df["pvr"] > pvr_thresh) &
            (df["rvol"] > rvol_thresh) &
            (df["close"] > df["ema_trend"]) &
            (df["btc_bull"] == 1) &
            (df["volume"] > 0)
        )
        
        # Simulate simple trade execution
        in_trade = False
        entry_price = 0
        entry_idx = 0
        
        for i in range(1, len(df)):
            if not in_trade:
                if entry_mask.iloc[i-1]: # Enter on open of candle i
                    in_trade = True
                    entry_price = df["open"].iloc[i]
                    entry_idx = i
            else:
                bars_held = i - entry_idx
                cur_high = df["high"].iloc[i]
                cur_low = df["low"].iloc[i]
                cur_close = df["close"].iloc[i]
                
                # Check TP
                hit_tp = (cur_high - entry_price) / entry_price >= tp_pct
                # Check SL
                hit_sl = (cur_low - entry_price) / entry_price <= -sl_pct
                # Check Max Hold
                time_exit = bars_held >= max_hold
                
                if hit_tp or hit_sl or time_exit:
                    if hit_tp and not hit_sl:
                        exit_p = entry_price * (1.0 + tp_pct)
                        reason = "tp"
                    elif hit_sl and not hit_tp:
                        exit_p = entry_price * (1.0 - sl_pct)
                        reason = "sl"
                    elif hit_tp and hit_sl:
                        # conservative: assume sl hit first
                        exit_p = entry_price * (1.0 - sl_pct)
                        reason = "sl"
                    else:
                        exit_p = cur_close
                        reason = "timeout"
                        
                    ret = (exit_p - entry_price) / entry_price
                    # Deduct Kraken taker fee 0.52% roundtrip
                    ret_net = ret - 0.0052
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
        print("No trades generated")
        return
        
    wins = tdf[tdf["ret_net"] > 0]
    losses = tdf[tdf["ret_net"] <= 0]
    win_rate = len(wins) / len(tdf) * 100
    avg_net_ret = tdf["ret_net"].mean() * 100
    avg_gross_ret = tdf["ret_gross"].mean() * 100
    avg_win = wins["ret_net"].mean() * 100 if len(wins) > 0 else 0
    avg_loss = losses["ret_net"].mean() * 100 if len(losses) > 0 else 0
    monthly_trades = len(tdf) / 12.0
    
    # Portfolio monthly return assuming 6 max trades (s = 0.16)
    port_monthly_ret = monthly_trades * 0.16 * avg_net_ret
    
    print(f"--- Config: TF={timeframe}, Donch={donchian_p}, TP={tp_pct*100}%, SL={sl_pct*100}%, MaxHold={max_hold} ---")
    print(f"Total Trades: {len(tdf)} ({monthly_trades:.1f}/month)")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg Gross Return: {avg_gross_ret:.2f}% | Avg Net Return: {avg_net_ret:.2f}%")
    print(f"Avg Win: +{avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
    print(f"Expected Portfolio Monthly Net Return (at 16% stake): {port_monthly_ret:.2f}%\n")

# Test configurations
for donch in [16, 20, 24]:
    for tp in [0.045, 0.06, 0.08]:
        for sl in [0.02, 0.025]:
            analyze_strategy_edge(timeframe="1h", donchian_p=donch, keltner_mult=1.4, pvr_thresh=1.10, rvol_thresh=1.4, tp_pct=tp, sl_pct=sl, max_hold=36)
