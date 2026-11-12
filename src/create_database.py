"""Builds the empty SQLite database from schema.sql (synthetic PoC)."""
import sqlite3
from pathlib import Path
from src.config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def create_database(reset: bool = True) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()
    print(f"Database created: {DB_PATH}")


if __name__ == "__main__":
    create_database()
