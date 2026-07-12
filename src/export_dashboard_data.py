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

    try:
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

    finally:
        conn.close()

    if df.empty:
        print("No data found in market_stats.")
        return

    # Create a proper monthly date column.
    df["date"] = pd.to_datetime(
        df["year"].astype(str)
        + "-"
        + df["month"].astype(str).str.zfill(2)
        + "-01",
        errors="coerce",
    )

    # Convert database values to numeric.
    # Invalid or missing values become blank.
    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    # Pivot metric rows into separate metric columns.
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

    identifier_columns = [
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
    ]

    # Convert metric names into Python-friendly technical names.
    metric_rename_map = {
        column: clean_column_name(column)
        for column in wide.columns
        if column not in identifier_columns
    }

    wide = wide.rename(columns=metric_rename_map)

    # Calculate Months of Inventory.
    if "total_inventory" in wide.columns and "unit_sales" in wide.columns:
        inventory = pd.to_numeric(
            wide["total_inventory"],
            errors="coerce",
        )

        sales = pd.to_numeric(
            wide["unit_sales"],
            errors="coerce",
        )

        # Zero sales produces a blank Months of Inventory value.
        wide["months_of_inventory"] = (
            inventory / sales.where(sales != 0)
        )

    # Sort chronologically before calculating rolling averages.
    series_sort_columns = [
        "board",
        "market_segment",
        "inventory_type",
        "geography_code",
        "property_type_code",
        "frequency",
        "date",
    ]

    wide = wide.sort_values(
        by=series_sort_columns,
        ascending=True,
    ).reset_index(drop=True)

    # Remove geography prefixes:
    # F70 - Abbotsford becomes Abbotsford.
    # V - Vancouver becomes Vancouver.
    wide["geography_name"] = (
        wide["geography_name"]
        .astype(str)
        .str.replace(r"^[^-]+ - ", "", regex=True)
        .str.strip()
    )

    # Rename columns for Google Sheets and dashboard presentation.
    presentation_rename_map = {
        "date": "Date",
        "year": "Year",
        "month": "Month",
        "board": "Board",
        "market_segment": "Market Segment",
        "inventory_type": "Inventory Type",
        "geography_code": "Area Code",
        "geography_name": "Area",
        "property_type_code": "Property Type Code",
        "property_type": "Property Type",
        "frequency": "Frequency",
        "percent_original_price": "% Original Price",
        "average_dollar_per_sq_ft": "Price / Sq Ft",
        "average_days_on_market": "Days on Market",
        "average_sale_price": "Sale Price",
        "new_listings": "New Listings",
        "sell_through_rate": "Sell Through Rate",
        "total_inventory": "Inventory",
        "unit_sales": "Sales",
        "months_of_inventory": "Months of Inventory",
    }

    wide = wide.rename(columns=presentation_rename_map)

    # Fields that uniquely identify one continuous market series.
    rolling_group_columns = [
        "Board",
        "Market Segment",
        "Inventory Type",
        "Area Code",
        "Property Type Code",
        "Frequency",
    ]

    dashboard_metrics = [
        "% Original Price",
        "Price / Sq Ft",
        "Days on Market",
        "Sale Price",
        "New Listings",
        "Sell Through Rate",
        "Inventory",
        "Sales",
        "Months of Inventory",
    ]

    existing_metrics = [
        metric
        for metric in dashboard_metrics
        if metric in wide.columns
    ]

    # Ensure every metric is numeric before rolling calculations.
    for metric in existing_metrics:
        wide[metric] = pd.to_numeric(
            wide[metric],
            errors="coerce",
        )

    # Create a separate three-month rolling-average column
    # for every exported metric.
    for metric in existing_metrics:
        rolling_column = f"{metric} 3-Month"

        wide[rolling_column] = (
            wide.groupby(
                rolling_group_columns,
                dropna=False,
                sort=False,
            )[metric]
            .transform(
                lambda series: series.rolling(
                    window=3,
                    min_periods=3,
                ).mean()
            )
        )

    # Keep identifier columns first.
    identifier_output_columns = [
        "Date",
        "Year",
        "Month",
        "Board",
        "Market Segment",
        "Inventory Type",
        "Area Code",
        "Area",
        "Property Type Code",
        "Property Type",
        "Frequency",
    ]

    # Put each monthly metric directly beside its three-month version.
    metric_output_columns = []

    for metric in existing_metrics:
        metric_output_columns.extend(
            [
                metric,
                f"{metric} 3-Month",
            ]
        )

    preferred_columns = (
        identifier_output_columns
        + metric_output_columns
    )

    existing_preferred_columns = [
        column
        for column in preferred_columns
        if column in wide.columns
    ]

    remaining_columns = [
        column
        for column in wide.columns
        if column not in existing_preferred_columns
    ]

    wide = wide[
        existing_preferred_columns
        + remaining_columns
    ]

    # Final export order.
    wide = wide.sort_values(
        by=[
            "Area",
            "Property Type",
            "Date",
        ],
        ascending=[
            True,
            True,
            True,
        ],
    ).reset_index(drop=True)

    wide.to_csv(
        OUTPUT_PATH,
        index=False,
        date_format="%Y-%m-%d",
    )

    print(f"Exported dashboard data to: {OUTPUT_PATH}")
    print(f"Rows exported: {len(wide):,}")
    print(f"Columns exported: {len(wide.columns):,}")

    print()
    print("Columns:")

    for column in wide.columns:
        print(f" - {column}")

    print()
    print("Areas:")

    for area in sorted(wide["Area"].dropna().unique()):
        print(f" - {area}")


if __name__ == "__main__":
    main()