"""
Export the production PostgreSQL database (Neon) to a local snapshot.

Produces two files from a single read:
  - a JSON dump of every row in every table  (portable, diff-able backup)
  - a SQLite database file                   (drop-in for local development)

Usage (from project root):
    DATABASE_URL="postgresql://..." python admin/postgres_to_sqlite.py
    DATABASE_URL="postgresql://..." python admin/postgres_to_sqlite.py \
        --json backups/demiplane.json --db backups/demiplane.db

This is the reverse of admin/sqlite_to_json.py + admin/json_to_postgres.py. It
reuses the shared schema in go_get_it/tables.py, so the SQLite file it writes
has the same tables and columns SQLiteGoGetDB.go_create_db() would create.
"""

import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import psycopg2.errors
import psycopg2.extras

from go_get_it.tables import TABLES

DEFAULT_JSON = 'backups/demiplane.json'
DEFAULT_DB = 'backups/demiplane.db'


def read_postgres(url: str) -> dict[str, list[dict]]:
    """Read every row of every known table from PostgreSQL.

    Args:
        url: PostgreSQL connection string (the Neon DATABASE_URL).

    Returns:
        Mapping of table name -> list of row dicts. A table that does not exist
        in the source comes back as an empty list rather than raising, so a
        partially migrated database still exports cleanly (matches the
        table-missing handling in sqlite_to_json.py).
    """
    # Read-only session: this script must never be able to mutate production.
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True)

    export: dict[str, list[dict]] = {}
    total_rows = 0

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
        for table in TABLES:
            try:
                cursor.execute(f'SELECT * FROM "{table}"')
                rows = [dict(row) for row in cursor.fetchall()]
            except psycopg2.errors.UndefinedTable:
                # Postgres aborts the transaction on a failed statement; clear
                # it so the next table's SELECT can run.
                conn.rollback()
                rows = []
                print(f"  {table}: skipped (not in source)")
            else:
                print(f"  {table}: {len(rows)} rows")

            export[table] = rows
            total_rows += len(rows)

    conn.close()
    print(f"\nRead {total_rows} rows across {len(export)} tables from PostgreSQL")
    return export


def write_json(export: dict[str, list[dict]], out_path: str) -> None:
    """Write the export to a pretty-printed JSON file.

    Args:
        export: Output of read_postgres().
        out_path: Destination path; parent directories are created.

    default=str stringifies the types psycopg2 returns that JSON can't encode
    natively (datetime, Decimal, UUID) - same approach as sqlite_to_json.py.
    """
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(export, f, indent=2, default=str)
    print(f"Wrote JSON snapshot -> {out_path}")


def write_sqlite(export: dict[str, list[dict]], db_path: str) -> None:
    """Create a fresh SQLite database and load every exported row.

    Args:
        export: Output of read_postgres().
        db_path: Destination path; an existing file is replaced so each run is
            a clean snapshot, not an append.

    Tables are created from go_get_it/tables.py exactly as
    SQLiteGoGetDB.go_create_db() does. Per-row insert failures (e.g. a value
    that trips a UNIQUE constraint) are reported and skipped rather than
    aborting the whole snapshot.
    """
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for table, schema in TABLES.items():
        columns = ', '.join(f"{name} {dtype}" for name, dtype in schema.items())
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")

    loaded = 0
    skipped = 0
    for table, rows in export.items():
        allowed_columns = set(TABLES[table].keys())
        for row in rows:
            values = {k: _sqlite_value(v) for k, v in row.items() if k in allowed_columns}
            if not values:
                continue
            placeholders = ', '.join('?' * len(values))
            statement = f"INSERT INTO {table} ({', '.join(values)}) VALUES ({placeholders})"
            try:
                cursor.execute(statement, tuple(values.values()))
                loaded += 1
            except sqlite3.Error as exc:
                print(f"  {table} row {row.get('id', '?')}: skipped - {exc}")
                skipped += 1

    conn.commit()
    conn.close()

    summary = f"{loaded} rows" + (f", {skipped} skipped" if skipped else "")
    print(f"Wrote SQLite database ({summary}) -> {db_path}")


def _sqlite_value(value: object) -> object:
    """Coerce a PostgreSQL value into a type sqlite3 can bind.

    Args:
        value: A single column value as psycopg2 returned it.

    Returns:
        The value unchanged if sqlite3 accepts it (str/bytes/int/float/None),
        an int for bool, otherwise its str() form. The app's columns are all
        TEXT/INTEGER and it already reads dates and UUIDs back as strings, so
        stringifying here matches what SQLite mode expects.
    """
    if isinstance(value, bool):
        return int(value)
    if value is None or isinstance(value, (str, bytes, int, float)):
        return value
    return str(value)


def main() -> None:
    """Parse arguments, read PostgreSQL once, and write the requested outputs."""
    parser = argparse.ArgumentParser(
        description='Export the Neon PostgreSQL database to a JSON snapshot and a SQLite file',
    )
    parser.add_argument('--json', default=DEFAULT_JSON, dest='json_path',
                        help=f'Output JSON snapshot path (default: {DEFAULT_JSON})')
    parser.add_argument('--db', default=DEFAULT_DB, dest='db_path',
                        help=f'Output SQLite database path (default: {DEFAULT_DB})')
    parser.add_argument('--skip-json', action='store_true', help='Only write the SQLite file')
    parser.add_argument('--skip-db', action='store_true', help='Only write the JSON snapshot')
    args = parser.parse_args()

    url = os.environ.get('DATABASE_URL')
    if not url:
        sys.exit('Error: DATABASE_URL is not set (expected the Neon connection string).')

    export = read_postgres(url)
    if not args.skip_json:
        write_json(export, args.json_path)
    if not args.skip_db:
        write_sqlite(export, args.db_path)


if __name__ == '__main__':
    main()
