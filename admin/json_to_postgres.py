"""
Import JSON export into a PostgreSQL database (e.g. Neon).

Creates all tables, seeds class data, then inserts every row from the JSON.
Safe to re-run — skips rows whose id already exists.

Usage (from project root):
    DATABASE_URL="postgresql://..." python admin/json_to_postgres.py
    DATABASE_URL="postgresql://..." python admin/json_to_postgres.py --input admin/db_export.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import psycopg2.extras

from go_get_it.pg_backend import PostgreSQLGoGetDB

DEFAULT_INPUT = 'db/db_export.json'


def import_data(input_path: str) -> None:
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("Error: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"Error: input file not found at {input_path}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    db_instance = PostgreSQLGoGetDB()

    print("Creating tables...")
    db_instance.go_create_db()

    print("Seeding class data...")
    db_instance.go_seed_db()

    print(f"\nImporting rows from {input_path}...")

    db = psycopg2.connect(url)
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    total_inserted = 0
    total_skipped = 0

    for table, rows in data.items():
        if not rows:
            print(f"  {table}: no rows")
            continue

        inserted = 0
        skipped = 0

        for row in rows:
            if not row:
                continue

            cursor.execute(f'SELECT id FROM "{table}" WHERE id = %s', (row['id'],))
            if cursor.fetchone():
                skipped += 1
                continue

            keys = ', '.join(row.keys())
            placeholders = ', '.join(['%s'] * len(row))
            sql = f'INSERT INTO "{table}" ({keys}) VALUES ({placeholders})'
            try:
                cursor.execute(sql, tuple(row.values()))
                inserted += 1
            except Exception as e:
                print(f"  {table} row {row.get('id', '?')}: ERROR — {e}")
                db.rollback()
                continue

        db.commit()
        total_inserted += inserted
        total_skipped += skipped
        print(f"  {table}: {inserted} inserted, {skipped} skipped")

    cursor.close()
    db.close()

    print(f"\nDone — {total_inserted} rows inserted, {total_skipped} already existed.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import JSON export into PostgreSQL')
    parser.add_argument('--input', default=DEFAULT_INPUT, help='Path to JSON export file')
    args = parser.parse_args()

    import_data(args.input)