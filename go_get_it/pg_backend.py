import os
import re
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.errors

from functions.functions import uuid
from misc.seed import SEED, SEED_ROWS
from go_get_it.tables import TABLES


def _pg_type(t: str) -> str:
    t = re.sub(r'TEXT\(\d+\)', 'TEXT', t.upper())
    return t.replace('MEDIUMTEXT', 'TEXT')


class PostgreSQLGoGetDB():
    TABLES = TABLES
    SEED = SEED
    SEED_ROWS = SEED_ROWS

    @staticmethod
    def _qt(table: str) -> str:
        return f'"{table}"'

    def go_connect_db(self):
        return psycopg2.connect(os.environ['DATABASE_URL'])

    def _validate_table(self, table: str):
        if table not in self.TABLES:
            raise ValueError(f"Unknown table: {table}")

    def _validate_columns(self, table: str, columns):
        allowed = set(self.TABLES[table].keys())
        invalid = [col for col in columns if col not in allowed]
        if invalid:
            raise ValueError(f"Unknown columns for table '{table}': {', '.join(invalid)}")

    def _go_get_table_columns(self, cursor, table: str):
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s AND table_schema = 'public'",
            (table,)
        )
        return {row['column_name'] for row in cursor.fetchall()}

    def _go_sync_table_columns(self, cursor, table: str, schema: dict):
        existing_columns = self._go_get_table_columns(cursor, table)
        added_columns = []

        for column, data_type in schema.items():
            if column not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE {self._qt(table)} ADD COLUMN IF NOT EXISTS {column} {_pg_type(data_type)}"
                )
                added_columns.append(column)

        return added_columns

    def _go_ensure_indexes(self, cursor):
        index_statements = {
            'idx_user_username_nocase_unique': (
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_user_username_nocase_unique '
                'ON "user"(lower(username))'
            ),
            'idx_user_to_character_unique': (
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_user_to_character_unique '
                'ON "user_to_character"(user_id, character_id)'
            ),
        }

        for index_name, statement in index_statements.items():
            try:
                cursor.execute(statement)
            except psycopg2.errors.UniqueViolation:
                print(f"[db] warning: could not create unique index '{index_name}' due to existing duplicate rows")

    def go_sync_schema(self):
        db = self.go_connect_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        applied_updates = {}

        for table, schema in self.TABLES.items():
            added_columns = self._go_sync_table_columns(cursor, table, schema)
            if added_columns:
                applied_updates[table] = added_columns

        self._go_ensure_indexes(cursor)

        db.commit()
        db.close()

        for table, columns in applied_updates.items():
            print(f"[db] schema sync: added columns to '{table}': {', '.join(columns)}")

    def go_create_db(self):
        db = self.go_connect_db()
        cursor = db.cursor()

        for table, schema in self.TABLES.items():
            columns_sql = ', '.join([f"{col} {_pg_type(dtype)}" for col, dtype in schema.items()])
            cursor.execute(f'CREATE TABLE IF NOT EXISTS {self._qt(table)} ({columns_sql})')

        db.commit()
        db.close()

        self.go_sync_schema()

    def go_get_all(self, table: str, params: Optional[dict] = None, count: bool = False):
        self._validate_table(table)
        db = self.go_connect_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        safe_params = dict(params or {})
        if safe_params:
            self._validate_columns(table, safe_params.keys())
            where = ' AND '.join([f'{key} = %s' for key in safe_params.keys()])
            if count:
                cursor.execute(f"SELECT COUNT(*) as row_count FROM {self._qt(table)} WHERE {where}", tuple(safe_params.values()))
            else:
                cursor.execute(f"SELECT * FROM {self._qt(table)} WHERE {where}", tuple(safe_params.values()))
        else:
            if count:
                cursor.execute(f"SELECT COUNT(*) as row_count FROM {self._qt(table)}")
            else:
                cursor.execute(f"SELECT * FROM {self._qt(table)}")

        if count:
            row = cursor.fetchone()
            db.close()
            return int(row['row_count']) if row else 0

        data = cursor.fetchall()
        db.close()

        return [dict(row) for row in data] if data else None

    def go_get_one(self, table: str, params: Optional[dict] = None):
        self._validate_table(table)
        db = self.go_connect_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        safe_params = dict(params or {})
        if safe_params:
            self._validate_columns(table, safe_params.keys())
            where = ' AND '.join([f'{key} = %s' for key in safe_params.keys()])
            cursor.execute(f"SELECT * FROM {self._qt(table)} WHERE {where}", tuple(safe_params.values()))
        else:
            cursor.execute(f"SELECT * FROM {self._qt(table)} LIMIT 1")

        data = cursor.fetchone()
        db.close()

        return dict(data) if data else None

    def go_add_new(self, table: str, data: dict):
        self._validate_table(table)
        payload = dict(data)
        if not payload:
            raise ValueError('go_add_new requires at least one column value')
        self._validate_columns(table, payload.keys())

        db = self.go_connect_db()
        cursor = db.cursor()
        keys = ', '.join(payload.keys())
        placeholders = ', '.join(['%s'] * len(payload))
        insert = f"INSERT INTO {self._qt(table)} ({keys}) VALUES ({placeholders})"
        try:
            cursor.execute(insert, tuple(payload.values()))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def go_update(self, table: str, data: dict):
        self._validate_table(table)
        payload = dict(data)
        if 'id' not in payload:
            raise ValueError("go_update requires an 'id' key")

        _id = payload['id']
        update_data = {key: value for key, value in payload.items() if key != 'id'}
        if not update_data:
            return
        self._validate_columns(table, update_data.keys())

        db = self.go_connect_db()
        cursor = db.cursor()
        set_clause = ', '.join([f"{key} = %s" for key in update_data.keys()])
        update = f"UPDATE {self._qt(table)} SET {set_clause} WHERE id = %s"
        cursor.execute(update, tuple(update_data.values()) + (_id,))
        db.commit()
        db.close()

    def go_delete_it(self, table: str, data: dict):
        self._validate_table(table)
        filters = dict(data)
        if 'id' not in filters:
            raise ValueError("go_delete_it requires an 'id' key")
        self._validate_columns(table, filters.keys())

        db = self.go_connect_db()
        cursor = db.cursor()
        where = ' AND '.join([f'{key} = %s' for key in filters.keys()])
        cursor.execute(f"DELETE FROM {self._qt(table)} WHERE {where}", tuple(filters.values()))
        db.commit()
        db.close()

    def go_delete_by(self, table: str, params: dict):
        self._validate_table(table)
        safe_params = dict(params)
        if not safe_params:
            raise ValueError('go_delete_by requires at least one filter parameter')
        self._validate_columns(table, safe_params.keys())

        db = self.go_connect_db()
        cursor = db.cursor()
        where = ' AND '.join([f'{key} = %s' for key in safe_params.keys()])
        cursor.execute(f"DELETE FROM {self._qt(table)} WHERE {where}", tuple(safe_params.values()))
        db.commit()
        db.close()

    def go_seed_db(self):
        for table, seed in self.SEED.items():
            for data, field in seed.items():
                if not self.go_get_one(table, {field: data}):
                    self.go_add_new(table, {"id": uuid(), field: data})

        for table, rows in self.SEED_ROWS.items():
            for row in rows:
                record = {field: value for value, field in row.items()}
                if not self.go_get_one(table, {"id": record["id"]}):
                    self.go_add_new(table, record)
