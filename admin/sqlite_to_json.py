"""
Export all SQLite table data to a JSON file.

Usage (from project root):
    python admin/sqlite_to_json.py
    python admin/sqlite_to_json.py --db path/to/custom.db --out admin/export.json
"""

import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from go_get_it.tables import TABLES

DEFAULT_DB = os.environ.get('DB_ROUTE')
DEFAULT_OUT = 'admin/db_export.json'


def export(db_path: str, out_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"Error: database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    export_data = {}
    total_rows = 0

    for table in TABLES:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = [dict(row) for row in cursor.fetchall()]
            export_data[table] = rows
            total_rows += len(rows)
            print(f"  {table}: {len(rows)} rows")
        except sqlite3.OperationalError:
            print(f"  {table}: skipped (table does not exist yet)")
            export_data[table] = []

    conn.close()

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"\nExported {total_rows} rows across {len(export_data)} tables → {out_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export SQLite DB to JSON')
    parser.add_argument('--db', default=DEFAULT_DB, help='Path to SQLite database file')
    parser.add_argument('--out', default=DEFAULT_OUT, help='Output JSON file path')
    args = parser.parse_args()

    print(f"Reading from: {args.db}")
    export(args.db, args.out)
