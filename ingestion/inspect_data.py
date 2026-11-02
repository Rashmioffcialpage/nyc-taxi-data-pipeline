from pathlib import Path
import csv

import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def main():
    trip_path = RAW_DIR / "yellow_tripdata_2024-01.parquet"
    zone_path = RAW_DIR / "taxi_zone_lookup.csv"

    for path in (trip_path, zone_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing dataset: {path}")

    parquet_file = pq.ParquetFile(trip_path)

    print("TRIP DATA")
    print(f"File: {trip_path.name}")
    print(f"Rows: {parquet_file.metadata.num_rows:,}")
    print(f"Row groups: {parquet_file.num_row_groups}")

    print("\nCOLUMN SCHEMA")
    print(parquet_file.schema_arrow)

    print("\nFIRST THREE TRIPS")
    first_batch = next(parquet_file.iter_batches(batch_size=3), None)

    if first_batch is not None:
        for record in first_batch.to_pylist():
            print(record)

    with zone_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        zone_columns = reader.fieldnames
        zones = list(reader)

    print("\nTAXI ZONES")
    print(f"Rows: {len(zones):,}")
    print(f"Columns: {zone_columns}")

    for zone in zones[:3]:
        print(zone)


if __name__ == "__main__":
    main()