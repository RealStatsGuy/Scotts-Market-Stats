import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "market_stats.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
SELECT
    geography_name,
    property_type,
    metric_name,
    year,
    month,
    value
FROM market_stats
WHERE
    geography_code = '5051'
    AND property_type_code = '64'
    AND metric_code = 'asp'
    AND year = 2010
    AND month = 3
""")

row = cur.fetchone()

if row:
    print(f"Geography : {row[0]}")
    print(f"Property  : {row[1]}")
    print(f"Metric    : {row[2]}")
    print(f"Date      : {row[3]}-{row[4]:02d}")
    print(f"Value     : {row[5]:,.0f}")
else:
    print("No matching record found.")

conn.close()