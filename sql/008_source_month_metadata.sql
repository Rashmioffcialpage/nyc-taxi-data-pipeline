BEGIN;

ALTER TABLE raw.ingestion_files
ADD COLUMN IF NOT EXISTS source_month DATE;

UPDATE raw.ingestion_files
SET source_month = (
    SUBSTRING(
        source_file
        FROM '^yellow_tripdata_([0-9]{4}-(0[1-9]|1[0-2]))[.]parquet$'
    ) || '-01'
)::date
WHERE source_month IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM raw.ingestion_files
        WHERE source_month IS NULL
    ) THEN
        RAISE EXCEPTION 'Unrecognized source filename in import log';
    END IF;
END;
$$;

COMMIT;

ANALYZE raw.ingestion_files;