import sqlite3

import pytest

from src.config import DB_PATH


@pytest.fixture(scope="session")
def db():
    """Read-only connection to the generated synthetic database."""
    if not DB_PATH.exists():
        pytest.fail("Database not found. Run: python -m src.generate_data")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


@pytest.fixture
def scratch(db):
    """Throwaway in-memory copy, so constraint tests never touch the real database."""
    mem = sqlite3.connect(":memory:")
    db.backup(mem)
    mem.execute("PRAGMA foreign_keys = ON")
    yield mem
    mem.close()
