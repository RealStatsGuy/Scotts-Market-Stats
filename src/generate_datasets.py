import csv
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_DIR = BASE_DIR / "config"
DATASETS_PATH = CONFIG_DIR / "datasets.csv"

GEOGRAPHIES_PATH = CONFIG_DIR / "geographies.csv"
METRICS_PATH = CONFIG_DIR / "metrics.csv"
PROPERTY_TYPES_PATH = CONFIG_DIR / "property_types.csv"


DATASET_FIELDS = [
    "enabled",
    "dataset_id",
    "board",
    "market_segment",
    "inventory_type",
    "geography_code",
    "geography_name",
    "property_type_code",
    "property_type",
    "nc_code",
    "metric_code",
    "metric",
    "frequency",
    "period",
    "status",
    "notes",
]


def is_enabled(value):
    return str(value).strip().upper() == "TRUE"


def slugify(value):
    value = str(value).strip().lower()
    value = re.sub(r"^[a-z]\d+\s*-\s*", "", value)  # H70 - Sardis -> Sardis
    value = re.sub(r"^[a-z]\s*-\s*", "", value)    # V - Vancouver -> Vancouver
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value


def read_enabled_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if is_enabled(row.get("enabled"))]


def generate_rows():
    geographies = read_enabled_rows(GEOGRAPHIES_PATH)
    metrics = read_enabled_rows(METRICS_PATH)
    property_types = read_enabled_rows(PROPERTY_TYPES_PATH)

    rows = []

    for geography in geographies:
        geography_slug = slugify(geography["geography_name"])

        for property_type in property_types:
            property_type_slug = slugify(property_type["property_type"])

            for metric in metrics:
                metric_code = metric["metric_code"].strip()

                dataset_id = f"{geography_slug}_{property_type_slug}_{metric_code}"

                rows.append({
                    "enabled": "TRUE",
                    "dataset_id": dataset_id,
                    "board": geography["source"].strip(),
                    "market_segment": geography["market_segment"].strip(),
                    "inventory_type": geography["inventory_type"].strip(),
                    "geography_code": geography["geography_code"].strip(),
                    "geography_name": geography["geography_name"].strip(),
                    "property_type_code": property_type["property_type_code"].strip(),
                    "property_type": property_type["property_type"].strip(),
                    "nc_code": property_type["nc_code"].strip(),
                    "metric_code": metric_code,
                    "metric": metric["metric"].strip(),
                    "frequency": "monthly",
                    "period": "100",
                    "status": "active",
                    "notes": "Generated from lookup tables.",
                })

    return rows


def write_datasets(rows):
    CONFIG_DIR.mkdir(exist_ok=True)

    with DATASETS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DATASET_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = generate_rows()
    write_datasets(rows)

    print(f"Generated {len(rows)} dataset rows")
    print(f"Wrote {DATASETS_PATH}")


if __name__ == "__main__":
    main()