import hashlib
import os
from pathlib import Path

import psycopg
from psycopg import sql
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRIP_FILE = (
    PROJECT_ROOT / "data/raw/yellow_tripdata_2024-01.parquet"
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://taxi:taxi_local_dev@127.0.0.1:5434/taxi_analytics",
)

BATCH_SIZE = 50_000

# Source Parquet column -> destination PostgreSQL column.
COLUMN_MAP = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "RatecodeID": "ratecode_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pickup_location_id",
    "DOLocationID": "dropoff_location_id",
    "payment_type": "payment_type",
    "fare_amount": "fare_amount",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge",
    "total_amount": "total_amount",
    "congestion_surcharge": "congestion_surcharge",
    "Airport_fee": "airport_fee",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    if not TRIP_FILE.is_file():
        raise FileNotFoundError(f"Missing dataset: {TRIP_FILE}")

    source_file = TRIP_FILE.name
    checksum = file_sha256(TRIP_FILE)
    parquet_file = pq.ParquetFile(TRIP_FILE)
    expected_rows = parquet_file.metadata.num_rows

    source_columns = list(COLUMN_MAP)
    missing = set(source_columns) - set(
        parquet_file.schema_arrow.names
    )

    if missing:
        raise ValueError(f"Missing Parquet columns: {sorted(missing)}")

    destination_columns = [
        "source_file",
        "source_row_number",
        *COLUMN_MAP.values(),
    ]

    copy_statement = sql.SQL(
        "COPY raw.yellow_trips ({}) FROM STDIN"
    ).format(
        sql.SQL(", ").join(
            sql.Identifier(column)
            for column in destination_columns
        )
    )

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            # Serialize imports of this source file.
            # The lock is released when the transaction ends.
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)",
                (source_file,),
            )

            cursor.execute(
                """
                SELECT file_sha256, row_count
                FROM raw.ingestion_files
                WHERE source_file = %s
                """,
                (source_file,),
            )
            existing = cursor.fetchone()

            if existing is not None:
                previous_checksum, previous_count = existing

                if previous_checksum != checksum:
                    raise RuntimeError(
                        "This filename was already imported with different "
                        "contents. Investigate before replacing its data."
                    )

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM raw.yellow_trips
                    WHERE source_file = %s
                    """,
                    (source_file,),
                )
                stored = cursor.fetchone()

                if stored is None or not (
                    stored[0] == previous_count == expected_rows
                ):
                    raise RuntimeError(
                        "Stored trip count does not match the import log."
                    )

                print(f"Skipped: {source_file}")
                print(f"Already imported: {previous_count:,} rows")
                return

            loaded_rows = 0

            with cursor.copy(copy_statement) as copy:
                for batch in parquet_file.iter_batches(
                    batch_size=BATCH_SIZE,
                    columns=source_columns,
                ):
                    columns = [
                        batch.column(index).to_pylist()
                        for index in range(batch.num_columns)
                    ]

                    for values in zip(*columns):
                        loaded_rows += 1
                        copy.write_row(
                            (source_file, loaded_rows, *values)
                        )

                    print(
                        f"Sent to database: "
                        f"{loaded_rows:,}/{expected_rows:,}",
                        flush=True,
                    )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM raw.yellow_trips
                WHERE source_file = %s
                """,
                (source_file,),
            )
            result = cursor.fetchone()

            if result is None or not (
                result[0] == loaded_rows == expected_rows
            ):
                raise RuntimeError(
                    "Row-count verification failed; import rolled back."
                )

            if file_sha256(TRIP_FILE) != checksum:
                raise RuntimeError(
                    "Source file changed during import; rolled back."
                )

            cursor.execute(
                """
                INSERT INTO raw.ingestion_files (
                    source_file,
                    file_sha256,
                    row_count
                )
                VALUES (%s, %s, %s)
                """,
                (source_file, checksum, loaded_rows),
            )

    # Successful connection-context exit commits the transaction.
    print(f"\nImport committed: {source_file}")
    print(f"Rows loaded: {loaded_rows:,}")


if __name__ == "__main__":
    main()