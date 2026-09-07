import re

with open("user_data/logs/comparison_backtest.log", "r") as f:
    text = f.read()

lines = text.splitlines()
results = []
in_summary = False

for line in lines:
    if "STRATEGY SUMMARY" in line:
        in_summary = True
    elif in_summary and "└" in line:
        in_summary = False
        
    if in_summary and "│" in line and not "Strategy" in line and not "┳" in line and not "┡" in line:
        parts = [p.strip() for p in line.split("│") if p.strip()]
        if len(parts) >= 7:
            # │ WTE_btc200 │ 195 │ 34 0 161 17.4 │ 60.12 │ 901.856 │ 5 days, 14:24:00 │ 8.42% │
            strat = parts[0]
            trades = parts[1]
            winrate = parts[2].split()[-1]
            tot_profit_pct = parts[3]
            tot_profit = parts[4]
            max_dd = parts[6]
            results.append((strat, trades, tot_profit, tot_profit_pct, winrate, max_dd))

with open("user_data/logs/comparison_results.md", "w") as f:
    f.write("| Strategy | Trades | Tot Profit USDT | Tot Profit % | Win % | Max Drawdown |\n")
    f.write("|---|---|---|---|---|---|\n")
    for res in results:
        f.write(f"| {res[0]} | {res[1]} | {res[2]} | {res[3]} | {res[4]} | {res[5]} |\n")
