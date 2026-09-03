import sqlite3
db = sqlite3.connect('/freqtrade/user_data/tradesv3.sqlite')
cur = db.cursor()
cur.execute("PRAGMA table_info(trades)")
cols = cur.fetchall()
print("Trades table columns:")
for col in cols:
    print(f"  {col[1]} ({col[2]})")
db.close()
