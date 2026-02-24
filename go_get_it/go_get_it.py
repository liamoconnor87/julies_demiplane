import sqlite3
from typing import Optional
from functions.functions import uuid
from go_get_it.seed import SEED
from go_get_it.tables import TABLES
from misc.config import DB_ROUTE


class GoGetDB():
    """
    Go Get It is a simple wrapper around sqlite3 to make it easier to interact with the database. It provides methods to create the database, get all data from a table, get one data from a table, add new data to a table, update data in a table and delete data from a table.
    """
    DB_ROUTE = DB_ROUTE
    TABLES = TABLES
    SEED = SEED

    def go_connect_db(self):
        return sqlite3.connect(self.DB_ROUTE)

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

    def go_sync_schema(self):
        db = self.go_connect_db()
        cursor = db.cursor()
        applied_updates = {}

        for table, schema in self.TABLES.items():
            added_columns = self._go_sync_table_columns(cursor, table, schema)
            if added_columns:
                applied_updates[table] = added_columns

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
        db = self.go_connect_db()
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        if params is not None:
            cursor.execute(f"SELECT * FROM {table} WHERE {' AND '.join([f'{key} = ?' for key in params.keys()])}", tuple(params.values()))
        else:
            cursor.execute(f"SELECT * FROM {table}")

        data = cursor.fetchall()
        db.close()

        result = None
        if data:
            result = [dict(row) for row in data]
            if count:
                result = len(result)

        return result

    def go_get_one(self, table: str, params: dict = {}):
        db = self.go_connect_db()
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM {table} WHERE {' AND '.join([f'{key} = ?' for key in params.keys()])}", tuple(params.values()))
        data = cursor.fetchone()
        db.close()

        result = None
        if data:
            result = dict(data)

        return result

    def go_add_new(self, table: str, data: dict):
        db = self.go_connect_db()
        cursor = db.cursor()
        insert = "INSERT INTO {table} ({keys}) VALUES ({values})".format(table=table, keys=", ".join(data.keys()), values=", ".join(["?"] * len(data.keys())))
        parameters = tuple(data.values())
        cursor.execute(insert, parameters)

        db.commit()
        db.close()

    def go_update(self, table: str,  data: dict):
        db = self.go_connect_db()
        cursor = db.cursor()

        _id = data.pop("id")
        update = "UPDATE {table} SET {keys} WHERE id = ?".format(
            table=table,
            keys=", ".join([f"{key} = ?" for key in data.keys()])
        )
        parameters = tuple(data.values()) + (_id,)
        cursor.execute(update, parameters)

        db.commit()
        db.close()

    def go_delete_it(self, table: str, data: dict):
        db = self.go_connect_db()
        cursor = db.cursor()

        _id = data.pop("id")
        delete = "DELETE FROM {table} WHERE id = ?".format(table=table)
        parameters = (_id,)
        cursor.execute(delete, parameters)

        db.commit()
        db.close()

    def go_seed_db(self):
        for table, seed in self.SEED.items():
            for data, field in seed.items():
                if not self.go_get_one(table, {field:data}):
                    self.go_add_new(table, {"id": uuid(), field:data})








