import re

with open("user_data/logs/comparison_backtest.log", "r") as f:
    text = f.read()

lines = text.splitlines()
results = []
strats = ["WTE_btc200 (4h - baseline)", "WTE_btc200_2h_sl5 (2h + 5% sl)"]
strat_idx = 0

in_main_report = False

for line in lines:
    if "BACKTESTING REPORT" in line:
        in_main_report = True
    elif "LEFT OPEN TRADES REPORT" in line:
        in_main_report = False
        
    if in_main_report and "│     TOTAL │" in line:
        parts = [p.strip() for p in line.split("│")]
        trades = parts[2]
        avg_profit = parts[3]
        tot_profit = parts[4]
        tot_profit_pct = parts[5]
        winrate = parts[7].split()[-1] if len(parts) > 7 else ""
        
        if strat_idx < len(strats):
            results.append((strats[strat_idx], trades, avg_profit, tot_profit, tot_profit_pct, winrate))
            strat_idx += 1

with open("user_data/logs/comparison_results.md", "w") as f:
    f.write("| Strategy | Trades | Avg Profit % | Tot Profit USDT | Tot Profit % | Win % |\n")
    f.write("|---|---|---|---|---|---|\n")
    for res in results:
        f.write(f"| {res[0]} | {res[1]} | {res[2]} | {res[3]} | {res[4]} | {res[5]} |\n")
