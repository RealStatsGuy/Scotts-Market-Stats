import sqlite3
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "market_stats.db"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "dashboard_data.csv"


def clean_column_name(name):
    return (
        name.lower()
        .replace("$", "dollar")
        .replace("%", "percent")
        .replace("/", "_per_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("__", "_")
        .strip("_")
    )


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            board,
            market_segment,
            inventory_type,
            geography_code,
            geography_name,
            property_type_code,
            property_type,
            metric_code,
            metric_name,
            frequency,
            year,
            month,
            value
        FROM market_stats
        ORDER BY
            geography_name,
            property_type,
            year,
            month,
            metric_name;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("No data found in market_stats.")
        return

    # Create proper date column for Google Sheets / dashboards
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )

    # Pivot metric rows into metric columns
    wide = (
        df.pivot_table(
            index=[
                "date",
                "year",
                "month",
                "board",
                "market_segment",
                "inventory_type",
                "geography_code",
                "geography_name",
                "property_type_code",
                "property_type",
                "frequency",
            ],
            columns="metric_name",
            values="value",
            aggfunc="first",
        )
        .reset_index()
    )

    wide.columns.name = None

    # Clean metric column names for dashboard use
    rename_map = {}
    for col in wide.columns:
        if col not in [
            "date",
            "year",
            "month",
            "board",
            "market_segment",
            "inventory_type",
            "geography_code",
            "geography_name",
            "property_type_code",
            "property_type",
            "frequency",
        ]:
            rename_map[col] = clean_column_name(col)

    wide = wide.rename(columns=rename_map)

    # Calculate months of inventory if possible
    if "total_inventory" in wide.columns and "unit_sales" in wide.columns:
        wide["months_of_inventory"] = wide.apply(
            lambda row: (
                row["total_inventory"] / row["unit_sales"]
                if pd.notna(row["total_inventory"])
                and pd.notna(row["unit_sales"])
                and row["unit_sales"] != 0
                else None
            ),
            axis=1,
        )

    wide = wide.sort_values(
        by=["geography_name", "property_type", "date"],
        ascending=[True, True, True],
    )

    wide.to_csv(OUTPUT_PATH, index=False)

    print(f"Exported dashboard data to: {OUTPUT_PATH}")
    print(f"Rows exported: {len(wide):,}")
    print(f"Columns exported: {len(wide.columns):,}")
    print()
    print("Columns:")
    for col in wide.columns:
        print(f" - {col}")


if __name__ == "__main__":
    main()