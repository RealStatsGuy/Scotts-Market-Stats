import csv
import json
from pathlib import Path

import requests

from src.database import (
    dataset_exists,
    finish_import_run,
    initialize_database,
    start_import_run,
    upsert_market_stats,
)


URL = "https://cadreb.stats.10kresearch.com/infoserv/sparks"

CONFIG_FILE = Path("config") / "datasets.csv"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "cadreb_test_rows.csv"
DEBUG_FILE = OUTPUT_DIR / "cadreb_debug_zero_rows.json"

FULL_HISTORY_PERIOD = "100"
INCREMENTAL_PERIOD = "36"


HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://cadreb.stats.10kresearch.com",
    "referer": "https://cadreb.stats.10kresearch.com/stats/market",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "Mozilla/5.0",
}


BASE_DATA = {
    "op": "d",
    "view": "100",
    "calc": "monthly",
    "min": "1",
    "ac": "23f79ac224ee4c04a83c5c91e36d37c5",
    "cid": "7ACDC6A1912E4002857EDDE61DC15F88",
    "s": "f150241ca0e546c39842eb8271942b8b",
}


def load_datasets():
    with CONFIG_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        return [
            row
            for row in reader
            if row["enabled"].strip().upper() == "TRUE"
        ]


def get_request_period(dataset):
    return dataset.get("period") or FULL_HISTORY_PERIOD


def build_request_data(dataset):
    data = BASE_DATA.copy()

    data["period"] = get_request_period(dataset)
    data["m"] = dataset["metric_code"]

    nc_code = dataset.get("nc_code", "").strip()

    filters = [f"pt:{dataset['property_type_code']}"]

    if nc_code:
        filters.append(f"nc:{nc_code}")

    filter_text = ",".join(filters)

    data["dq"] = (
        f"{dataset['geography_code']}#{nc_code or 0}="
        f"{filter_text}|"
    )

    return data


def fetch_cadreb_data(dataset):
    request_data = build_request_data(dataset)

    response = requests.post(
        URL,
        headers=HEADERS,
        data=request_data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json(), request_data, response.status_code


def summarize_payload(data):
    payload = data.get("Payload", [])

    return [
        {
            "type": part.get("Type"),
            "name": part.get("Name"),
            "key": part.get("Key"),
            "metric_name": part.get("MetricName"),
            "no_data_message": part.get("NoDataMessage"),
            "data_points": len(part.get("Data", [])) if isinstance(part.get("Data"), list) else None,
            "axis_labels": len(part.get("AxisLabels", [])) if isinstance(part.get("AxisLabels"), list) else None,
        }
        for part in payload
    ]


def normalize_response(data, dataset):
    labels = None
    rows = []

    for part in data.get("Payload", []):
        if part.get("Type") == "SERIES_CATEGORIES":
            labels = part.get("AxisLabels", [])

        if part.get("Type") == "SERIES_DATA":
            values = part.get("Data", [])

            if labels is None:
                raise ValueError("SERIES_DATA found before SERIES_CATEGORIES.")

            for month_label, value in zip(labels, values):
                month, year = month_label.split("-")

                rows.append({
                    "dataset_id": dataset["dataset_id"],
                    "board": dataset["board"],
                    "market_segment": dataset["market_segment"],
                    "inventory_type": dataset["inventory_type"],
                    "geography_code": dataset["geography_code"],
                    "geography_name": part.get("Name") or dataset["geography_name"],
                    "property_type_code": dataset["property_type_code"],
                    "property_type": dataset["property_type"],
                    "metric_code": dataset["metric_code"],
                    "metric": dataset["metric"],
                    "frequency": dataset["frequency"],
                    "year": int(year),
                    "month": int(month),
                    "value": value,
                })

    return rows


def save_rows_to_csv(rows):
    fieldnames = [
        "dataset_id",
        "board",
        "market_segment",
        "inventory_type",
        "geography_code",
        "geography_name",
        "property_type_code",
        "property_type",
        "metric_code",
        "metric",
        "frequency",
        "year",
        "month",
        "value",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_debug_zero_rows(debug_rows):
    with DEBUG_FILE.open("w", encoding="utf-8") as file:
        json.dump(debug_rows, file, indent=2)


def main():
    initialize_database()

    import_id = start_import_run("CADREB connector run")

    datasets_processed = 0
    all_rows = []
    errors = []
    zero_row_debug = []

    try:
        datasets = load_datasets()

        print(f"Datasets loaded from config: {len(datasets)}")
        print()

        for dataset in datasets:
            dataset_id = dataset["dataset_id"]
            request_period = get_request_period(dataset)

            print(f"Fetching: {dataset_id} ({request_period} months)")

            try:
                data, request_data, status_code = fetch_cadreb_data(dataset)
                rows = normalize_response(data, dataset)

                print(f"Rows received: {len(rows)}")

                if len(rows) == 0:
                    print("ZERO ROWS - writing debug details")
                    print(f"dq: {request_data.get('dq')}")
                    print(f"metric: {request_data.get('m')}")
                    print(f"http: {status_code}")
                    print(f"payload summary: {summarize_payload(data)}")

                    zero_row_debug.append({
                        "dataset_id": dataset_id,
                        "geography_name": dataset.get("geography_name"),
                        "property_type": dataset.get("property_type"),
                        "metric": dataset.get("metric"),
                        "request": request_data,
                        "http_status": status_code,
                        "payload_summary": summarize_payload(data),
                        "raw_response": data,
                    })

                datasets_processed += 1
                all_rows.extend(rows)

            except Exception as error:
                error_message = f"{dataset_id}: {error}"
                errors.append(error_message)
                print(f"FAILED: {error_message}")

        if all_rows:
            upsert_market_stats(all_rows)
            save_rows_to_csv(all_rows)

        if zero_row_debug:
            save_debug_zero_rows(zero_row_debug)

        status = "success" if not errors else "partial_success"
        notes = "Run completed successfully." if not errors else " | ".join(errors)

        finish_import_run(
            import_id=import_id,
            status=status,
            datasets_processed=datasets_processed,
            rows_processed=len(all_rows),
            notes=notes,
        )

        print()
        print(f"Datasets processed: {datasets_processed}")
        print(f"Total rows saved to SQLite: {len(all_rows)}")
        print(f"CSV debug output: {OUTPUT_FILE}")
        print(f"Zero-row debug output: {DEBUG_FILE}")
        print("Database file: data/market_stats.db")

        if errors:
            print()
            print("Errors:")
            for error in errors:
                print(f"- {error}")

    except Exception as error:
        finish_import_run(
            import_id=import_id,
            status="failed",
            datasets_processed=datasets_processed,
            rows_processed=len(all_rows),
            notes=str(error),
        )

        raise


if __name__ == "__main__":
    main()