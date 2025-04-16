import sqlite3
from typing import Optional
from functions.functions import uuid
from go_get_it.seed import SEED
from go_get_it.tables import TABLES
from misc.config import DB_ROUTE


class Database():
    """
    Does various things to do with the database
    """
    def __init__(self):
        self.db_route = DB_ROUTE
        self.tables = TABLES
        self.seed = SEED
        pass

    def go_connect_db(self):
        return sqlite3.connect(self.db_route)

    def go_create_db(self):
        db = self.go_connect_db()
        cursor = db.cursor()

        for table in self.tables:
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table} ({", ".join([f"{key} {value}" for key, value in self.tables[table].items()])})''')

        # Commit changes and close the connection
        db.commit()
        db.close()

    def go_get_all(self, table: str, params: Optional[dict] = None, count: bool = False):
        """
        Goes and gets the data from the `table` you want
        """
        data= []
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
        for table, seed in self.seed.items():
            for data, field in seed.items():
                if not self.go_get_one(table, {field:data}):
                    self.go_add_new(table, {"id": uuid(), field:data})








