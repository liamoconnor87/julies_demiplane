"""
Offline self-check for admin/postgres_to_sqlite.py - no database needed.

Run from the project root:
    python admin/test_postgres_to_sqlite.py

Exercises the two pieces that carry real logic: value coercion and the
PostgreSQL-shaped-dict -> SQLite-file conversion.
"""

import datetime
import decimal
import os
import sqlite3
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from admin.postgres_to_sqlite import _sqlite_value, write_sqlite


def check_value_coercion() -> None:
    """Every psycopg2 return type maps to something sqlite3 can bind."""
    assert _sqlite_value(True) == 1
    assert _sqlite_value(False) == 0
    assert _sqlite_value(None) is None
    assert _sqlite_value('jules') == 'jules'
    assert _sqlite_value(7) == 7
    assert _sqlite_value(datetime.datetime(2026, 1, 2, 3, 4, 5)) == '2026-01-02 03:04:05'
    assert _sqlite_value(decimal.Decimal('1.50')) == '1.50'
    generated = uuid.uuid4()
    assert _sqlite_value(generated) == str(generated)


def check_conversion() -> None:
    """write_sqlite builds a clean file matching the app schema each run."""
    workdir = tempfile.mkdtemp()
    db_path = os.path.join(workdir, 'snapshot.db')

    export = {'user': [{
        'id': 'a' * 32,
        'username': 'jules',
        'admin': True,
        'not_a_real_column': 'must be dropped',
    }]}

    write_sqlite(export, db_path)
    with sqlite3.connect(db_path) as conn:
        assert conn.execute('SELECT id, username, admin FROM "user"').fetchone() == ('a' * 32, 'jules', 1)

    # A second run replaces the file rather than appending - still one row.
    write_sqlite(export, db_path)
    with sqlite3.connect(db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM "user"').fetchone()[0] == 1


if __name__ == '__main__':
    check_value_coercion()
    check_conversion()
    print('self-check: PASS')
