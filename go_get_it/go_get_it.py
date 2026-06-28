import os
import sqlite3
from typing import Optional
from functions.functions import uuid
from db.seed import SEED, SEED_ROWS
from go_get_it.tables import TABLES
from db.config import DB_ROUTE


class SQLiteGoGetDB():
    """
    Go Get It is a simple wrapper around sqlite3 to make it easier to interact with the database. It provides methods to create the database, get all data from a table, get one data from a table, add new data to a table, update data in a table and delete data from a table.
    """
    DB_ROUTE = DB_ROUTE
    TABLES = TABLES
    SEED = SEED
    SEED_ROWS = SEED_ROWS

    def go_connect_db(self):
        return sqlite3.connect(self.DB_ROUTE)

    def _validate_table(self, table: str):
        if table not in self.TABLES:
            raise ValueError(f"Unknown table: {table}")

    def _validate_columns(self, table: str, columns):
        allowed = set(self.TABLES[table].keys())
        invalid = [column for column in columns if column not in allowed]
        if invalid:
            raise ValueError(f"Unknown columns for table '{table}': {', '.join(invalid)}")

    def _go_get_table_columns(self, cursor: sqlite3.Cursor, table: str):
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    def _go_sync_table_columns(self, cursor: sqlite3.Cursor, table: str, schema: dict):
        existing_columns = self._go_get_table_columns(cursor, table)
        added_columns = []

        for column, data_type in schema.items():
            if column not in existing_columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {data_type}")
                added_columns.append(column)

        return added_columns

    def _go_ensure_indexes(self, cursor: sqlite3.Cursor):
        index_statements = {
            'idx_user_username_nocase_unique': "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_username_nocase_unique ON user(username COLLATE NOCASE)",
            'idx_user_to_character_unique': "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_to_character_unique ON user_to_character(user_id, character_id)",
        }

        for index_name, statement in index_statements.items():
            try:
                cursor.execute(statement)
            except sqlite3.IntegrityError:
                print(f"[db] warning: could not create unique index '{index_name}' due to existing duplicate rows")

    def go_sync_schema(self):
        db = self.go_connect_db()
        cursor = db.cursor()
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

        for table in self.TABLES:
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table} ({", ".join([f"{key} {value}" for key, value in self.TABLES[table].items()])})''')

        # Commit changes and close the connection
        db.commit()
        db.close()

        self.go_sync_schema()

    def go_get_all(self, table: str, params: Optional[dict] = None, count: bool = False):
        """
        Goes and gets the data from the `table` you want
        """
        self._validate_table(table)
        db = self.go_connect_db()
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        safe_params = dict(params or {})
        if safe_params:
            self._validate_columns(table, safe_params.keys())
            where = ' AND '.join([f'{key} = ?' for key in safe_params.keys()])
            if count:
                cursor.execute(f"SELECT COUNT(*) as row_count FROM {table} WHERE {where}", tuple(safe_params.values()))
            else:
                cursor.execute(f"SELECT * FROM {table} WHERE {where}", tuple(safe_params.values()))
        else:
            if count:
                cursor.execute(f"SELECT COUNT(*) as row_count FROM {table}")
            else:
                cursor.execute(f"SELECT * FROM {table}")

        if count:
            row = cursor.fetchone()
            db.close()
            return int(row['row_count']) if row else 0

        data = cursor.fetchall()
        db.close()

        result = None
        if data:
            result = [dict(row) for row in data]

        return result

    def go_get_one(self, table: str, params: Optional[dict] = None):
        self._validate_table(table)
        db = self.go_connect_db()
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        safe_params = dict(params or {})
        if safe_params:
            self._validate_columns(table, safe_params.keys())
            where = ' AND '.join([f'{key} = ?' for key in safe_params.keys()])
            cursor.execute(f"SELECT * FROM {table} WHERE {where}", tuple(safe_params.values()))
        else:
            cursor.execute(f"SELECT * FROM {table} LIMIT 1")

        data = cursor.fetchone()
        db.close()

        result = None
        if data:
            result = dict(data)

        return result

    def go_add_new(self, table: str, data: dict):
        self._validate_table(table)
        payload = dict(data)
        if not payload:
            raise ValueError('go_add_new requires at least one column value')
        self._validate_columns(table, payload.keys())

        db = self.go_connect_db()
        cursor = db.cursor()
        insert = "INSERT INTO {table} ({keys}) VALUES ({values})".format(table=table, keys=", ".join(payload.keys()), values=", ".join(["?"] * len(payload.keys())))
        parameters = tuple(payload.values())
        try:
            cursor.execute(insert, parameters)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def go_update(self, table: str,  data: dict):
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

        update = "UPDATE {table} SET {keys} WHERE id = ?".format(
            table=table,
            keys=", ".join([f"{key} = ?" for key in update_data.keys()])
        )
        parameters = tuple(update_data.values()) + (_id,)
        cursor.execute(update, parameters)

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

        where = ' AND '.join([f'{key} = ?' for key in filters.keys()])
        delete = f"DELETE FROM {table} WHERE {where}"
        parameters = tuple(filters.values())
        cursor.execute(delete, parameters)

        db.commit()
        db.close()

    def go_delete_by(self, table: str, params: dict):
        """Delete all rows matching the given column=value pairs."""
        self._validate_table(table)
        safe_params = dict(params)
        if not safe_params:
            raise ValueError('go_delete_by requires at least one filter parameter')
        self._validate_columns(table, safe_params.keys())

        db = self.go_connect_db()
        cursor = db.cursor()

        where = ' AND '.join([f'{key} = ?' for key in safe_params.keys()])
        cursor.execute(f"DELETE FROM {table} WHERE {where}", tuple(safe_params.values()))

        db.commit()
        db.close()

    def go_seed_db(self):
        for table, seed in self.SEED.items():
            for data, field in seed.items():
                if not self.go_get_one(table, {field:data}):
                    self.go_add_new(table, {"id": uuid(), field:data})

        # Full-row seeds (e.g. admin user, user_to_character)
        for table, rows in self.SEED_ROWS.items():
            for row in rows:
                record = {field: value for value, field in row.items()}
                if not self.go_get_one(table, {"id": record["id"]}):
                    self.go_add_new(table, record)


def GoGetDB():
    if os.environ.get('DATABASE_URL'):
        from go_get_it.pg_backend import PostgreSQLGoGetDB
        return PostgreSQLGoGetDB()
    return SQLiteGoGetDB()








