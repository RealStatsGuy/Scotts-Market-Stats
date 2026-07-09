import sqlite3
from pathlib import Path

DB = Path("data/market_stats.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("\nTABLES")
print("-" * 50)

tables = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name;
""").fetchall()

for (table,) in tables:
    print(f"\n{table}")
    print("-" * 50)

    columns = cur.execute(f"PRAGMA table_info({table});").fetchall()

    for col in columns:
        print(col)

conn.close()