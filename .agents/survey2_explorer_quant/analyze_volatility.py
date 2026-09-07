import pandas as pd
import numpy as np
import os
import glob

data_dir = "/freqtrade/project/user_data/data/binance"
pairs = ["SOL", "NEAR", "FET", "HBAR", "ADA", "BTC", "ETH", "LINK", "INJ", "SUI"]

results = []

for pair in pairs:
    f_1h = os.path.join(data_dir, f"{pair}_USDT-1h.feather")
    f_15m = os.path.join(data_dir, f"{pair}_USDT-15m.feather")
    
    if not os.path.exists(f_1h):
        continue
        
    df_1h = pd.read_feather(f_1h)
    df_1h["date"] = pd.to_datetime(df_1h["date"])
    df_1h_2024 = df_1h[(df_1h["date"] >= "2024-01-01") & (df_1h["date"] <= "2024-12-31")].copy()
    
    # 1h candle range (High - Low) / Close
    range_1h = (df_1h_2024["high"] - df_1h_2024["low"]) / df_1h_2024["close"] * 100
    atr_1h = (df_1h_2024["high"] - df_1h_2024["low"]).rolling(14).mean() / df_1h_2024["close"] * 100
    
    # Parkinson volatility 1h
    ratio = (df_1h_2024["high"] / df_1h_2024["low"].clip(lower=1e-8)).clip(lower=1.0)
    log_hl = np.log(ratio)
    pv_1h = np.sqrt((log_hl ** 2) / (4.0 * np.log(2.0))) * 100
    
    # 15m if exists
    range_15m_val = None
    if os.path.exists(f_15m):
        df_15m = pd.read_feather(f_15m)
        df_15m["date"] = pd.to_datetime(df_15m["date"])
        df_15m_2024 = df_15m[(df_15m["date"] >= "2024-01-01") & (df_15m["date"] <= "2024-12-31")].copy()
        range_15m = (df_15m_2024["high"] - df_15m_2024["low"]) / df_15m_2024["close"] * 100
        range_15m_val = range_15m.median()
        
    results.append({
        "pair": pair,
        "median_1h_range_pct": range_1h.median(),
        "mean_1h_range_pct": range_1h.mean(),
        "p90_1h_range_pct": range_1h.quantile(0.90),
        "median_15m_range_pct": range_15m_val,
        "median_pv_1h_pct": pv_1h.median(),
        "fee_drag_taker_052_pct_of_1h_range": (0.52 / range_1h.median()) * 100,
        "fee_drag_taker_052_pct_of_15m_range": (0.52 / range_15m_val) * 100 if range_15m_val else None,
    })

res_df = pd.DataFrame(results)
print(res_df.to_string(index=False))
