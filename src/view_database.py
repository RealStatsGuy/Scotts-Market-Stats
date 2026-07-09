import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "market_stats.db"


def main():
    if not DB_PATH.exists():
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 60)
    print("Scott's Market Stats Database")
    print("=" * 60)
    print()

    # --------------------------------------------------
    # Table counts
    # --------------------------------------------------

    print("TABLES")
    print("-" * 60)

    tables = [
        "market_stats",
        "import_runs",
    ]

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table:<20} {count:,} rows")

    print()

    # --------------------------------------------------
    # Latest import
    # --------------------------------------------------

    print("LATEST IMPORT")
    print("-" * 60)

    cur.execute("""
        SELECT
            import_id,
            started_at,
            finished_at,
            status,
            datasets_processed,
            rows_processed
        FROM import_runs
        ORDER BY import_id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if row:
        print(f"Import ID:          {row[0]}")
        print(f"Started:            {row[1]}")
        print(f"Finished:           {row[2]}")
        print(f"Status:             {row[3].upper()}")
        print(f"Datasets:           {row[4]}")
        print(f"Rows:               {row[5]:,}")

    print()

    # --------------------------------------------------
    # Dataset summary
    # --------------------------------------------------

    print("DATASETS")
    print("-" * 60)

    cur.execute("""
        SELECT
            board,
            geography_name,
            property_type,
            metric_name,
            COUNT(*),
            MIN(year || '-' || printf('%02d', month)),
            MAX(year || '-' || printf('%02d', month))
        FROM market_stats
        GROUP BY
            board,
            geography_name,
            property_type,
            metric_name
        ORDER BY
            geography_name,
            property_type,
            metric_name
    """)

    for row in cur.fetchall():
        board, geo, prop, metric, count, first, last = row

        print(f"{geo}")
        print(f"   Source:     {board}")
        print(f"   Property:   {prop}")
        print(f"   Metric:     {metric}")
        print(f"   Records:    {count}")
        print(f"   Date Range: {first} → {last}")
        print()

    conn.close()


if __name__ == "__main__":
    main()