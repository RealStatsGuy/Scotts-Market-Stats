import csv
from pathlib import Path

import requests


URL = "https://cadreb.stats.10kresearch.com/infoserv/sparks"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "cadreb_test_rows.csv"


HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://cadreb.stats.10kresearch.com",
    "referer": "https://cadreb.stats.10kresearch.com/stats/market",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "Mozilla/5.0",
}


DATA = {
    "op": "d",
    "view": "100",
    "period": "100",
    "calc": "monthly",
    "m": "asp",
    "dq": "5051#0=pt:32|",
    "min": "1",
    "ac": "23f79ac224ee4c04a83c5c91e36d37c5",
    "cid": "7ACDC6A1912E4002857EDDE61DC15F88",
    "s": "f150241ca0e546c39842eb8271942b8b",
}


def fetch_cadreb_data():
    response = requests.post(URL, headers=HEADERS, data=DATA, timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_response(data):
    labels = None
    rows = []

    for part in data.get("Payload", []):
        if part.get("Type") == "SERIES_CATEGORIES":
            labels = part.get("AxisLabels", [])

        if part.get("Type") == "SERIES_DATA":
            key = part.get("Key", "")
            geography_code = key.split("-")[1]
            geography_name = part.get("Name")
            values = part.get("Data", [])

            for month_label, value in zip(labels, values):
                month, year = month_label.split("-")

                rows.append({
                    "board": "CADREB",
                    "market_segment": "Resale",
                    "inventory_type": "Residential",
                    "geography_code": geography_code,
                    "geography_name": geography_name,
                    "property_type_code": "32",
                    "property_type": "Condo",
                    "metric_code": "asp",
                    "metric": "Average Sale Price",
                    "frequency": "monthly",
                    "year": int(year),
                    "month": int(month),
                    "value": value,
                })

    return rows


def save_rows_to_csv(rows):
    fieldnames = [
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


def main():
    data = fetch_cadreb_data()
    rows = normalize_response(data)
    save_rows_to_csv(rows)

    print(f"Rows saved: {len(rows)}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()