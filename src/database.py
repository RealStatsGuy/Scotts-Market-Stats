import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data") / "market_stats.db"


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def initialize_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_stats (
            board TEXT NOT NULL,
            market_segment TEXT,
            inventory_type TEXT,
            geography_code TEXT NOT NULL,
            geography_name TEXT,
            property_type_code TEXT NOT NULL,
            property_type TEXT,
            metric_code TEXT NOT NULL,
            metric_name TEXT,
            frequency TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            value REAL,
            PRIMARY KEY (
                board,
                geography_code,
                property_type_code,
                metric_code,
                frequency,
                year,
                month
            )
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_runs (
            import_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            datasets_processed INTEGER DEFAULT 0,
            rows_processed INTEGER DEFAULT 0,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()


def dataset_exists(dataset):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM market_stats
        WHERE
            board = ?
            AND geography_code = ?
            AND property_type_code = ?
            AND metric_code = ?
            AND frequency = ?
    """, (
        dataset["board"],
        dataset["geography_code"],
        dataset["property_type_code"],
        dataset["metric_code"],
        dataset["frequency"],
    ))

    count = cur.fetchone()[0]

    conn.close()

    return count > 0


def start_import_run(notes=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO import_runs (
            started_at,
            status,
            notes
        )
        VALUES (?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        "running",
        notes,
    ))

    import_id = cur.lastrowid

    conn.commit()
    conn.close()

    return import_id


def finish_import_run(import_id, status, datasets_processed, rows_processed, notes=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE import_runs
        SET
            finished_at = ?,
            status = ?,
            datasets_processed = ?,
            rows_processed = ?,
            notes = ?
        WHERE import_id = ?
    """, (
        datetime.now().isoformat(timespec="seconds"),
        status,
        datasets_processed,
        rows_processed,
        notes,
        import_id,
    ))

    conn.commit()
    conn.close()


def upsert_market_stats(rows):
    conn = get_connection()
    cur = conn.cursor()

    cur.executemany("""
        INSERT INTO market_stats (
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
        )
        VALUES (
            :board,
            :market_segment,
            :inventory_type,
            :geography_code,
            :geography_name,
            :property_type_code,
            :property_type,
            :metric_code,
            :metric,
            :frequency,
            :year,
            :month,
            :value
        )
        ON CONFLICT (
            board,
            geography_code,
            property_type_code,
            metric_code,
            frequency,
            year,
            month
        )
        DO UPDATE SET
            market_segment = excluded.market_segment,
            inventory_type = excluded.inventory_type,
            geography_name = excluded.geography_name,
            property_type = excluded.property_type,
            metric_name = excluded.metric_name,
            value = excluded.value
    """, rows)

    conn.commit()
    conn.close()