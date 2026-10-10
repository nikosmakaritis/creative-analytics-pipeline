from pathlib import Path

import duckdb

from creative_analytics.config import DATABASE_PATH, RAW_TABLES, VIEWS_DIR, WAREHOUSE_DIR


def build(database_path: Path = DATABASE_PATH) -> Path:
    database_path.unlink(missing_ok=True)
    with duckdb.connect(str(database_path)) as con:
        con.execute("CREATE SCHEMA raw")
        con.execute("CREATE SCHEMA analytics")
        for table in RAW_TABLES:
            source = (WAREHOUSE_DIR / f"{table}.parquet").as_posix()
            con.execute(f"CREATE TABLE raw.{table} AS SELECT * FROM read_parquet('{source}')")
            rows = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
            print(f"raw.{table}: {rows:,} rows")
        for view_file in sorted(VIEWS_DIR.glob("*.sql")):
            con.execute(view_file.read_text())
            print(f"analytics.{view_file.stem[3:]}: view")
    return database_path


def ensure_warehouse() -> Path:
    return DATABASE_PATH if DATABASE_PATH.exists() else build()


if __name__ == "__main__":
    build()
