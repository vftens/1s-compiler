"""
Shared database connection helper for all runtime modules.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    """Open erp.db and return a connection with row_factory set."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. "
            "Run the server at least once to initialise erp.db."
        )
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
