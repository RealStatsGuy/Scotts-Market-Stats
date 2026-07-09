import sqlite3
from pathlib import Path


DB_FILE = Path("data") / "market_stats.db"


def format_value(value):
    if value is None:
        return "None"

    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def main():
    geography_code = "5009"        # CADREB
    property_type_code = "16"      # Single Family
    metric_code = "apsf"           # Average $/Sq Ft
    year = 2010
    month = 1

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    query = """
    SELECT
        geography_name,
        property_type,
        metric_code,
        year,
        month,
        value
    FROM market_stats
    WHERE geography_code = ?
      AND property_type_code = ?
      AND metric_code = ?
      AND year = ?
      AND month = ?
"""

    row = conn.execute(
        query,
        (
            geography_code,
            property_type_code,
            metric_code,
            year,
            month,
        ),
    ).fetchone()

    conn.close()

    if row is None:
        print("No matching row found.")
        print()
        print(f"geography_code: {geography_code}")
        print(f"property_type_code: {property_type_code}")
        print(f"Metric    : {row['metric_code']}")
        print(f"date: {year}-{month:02d}")
        return

    print(f"Geography : {row['geography_name']}")
    print(f"Property  : {row['property_type']}")
    print(f"Date      : {row['year']}-{row['month']:02d}")
    print(f"Value     : {format_value(row['value'])}")


if __name__ == "__main__":
    main()