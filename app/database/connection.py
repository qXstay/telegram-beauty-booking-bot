import sqlite3
from pathlib import Path

from app.database.schema import SCHEMA


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self.connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def init_schema(self) -> None:
        connection = self.connect()
        connection.executescript(SCHEMA)
        connection.commit()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
