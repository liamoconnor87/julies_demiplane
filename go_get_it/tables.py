from typing import Optional

from misc.tables import APP_TABLES

_id = "TEXT(32) PRIMARY KEY"

def _text(limit: Optional[int] = None):
    if limit is None:
        limit = 255
    return f"TEXT({limit})"

# _integer = "INTEGER"
# _mediumtext = "MEDIUMTEXT"
# _fk = "TEXT"
_boolean = "INTEGER NOT NULL DEFAULT 0"

TABLES = {
    "user": {
        "id": _id,
        "username": f"{_text(30)} UNIQUE",
        "password_hash": _text(256),
        "created_at": _text(),
        "admin": _boolean,
    },
    **APP_TABLES,
}
