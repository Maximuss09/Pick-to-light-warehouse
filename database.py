"""NEW: SQLite connection and inventory-search functions for the backend."""

import sqlite3
from pathlib import Path
from typing import Any

# NEW: keep the database location in one module so tests can safely replace it.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "almacen_ptl.db"


def get_db_connection() -> sqlite3.Connection:
    """Return a database connection with named-column access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def buscar_part_number_en_db(part_number: str) -> dict[str, Any] | None:
    """Return one exact part-number location, or None when it does not exist."""
    cleaned_part_number = part_number.strip()
    conn = get_db_connection()
    try:
        resultado = conn.execute(
            """
            SELECT i.part_number, u.rack, u.columna, u.nivel, u.posicion, u.id_ubicacion
            FROM inventario i
            JOIN ubicaciones u ON i.id_ubicacion = u.id_ubicacion
            WHERE i.part_number = ?
            """,
            (cleaned_part_number,),
        ).fetchone()
    finally:
        conn.close()

    return dict(resultado) if resultado is not None else None
