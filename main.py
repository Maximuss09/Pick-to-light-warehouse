import io
import sqlite3
from pathlib import Path

import openpyxl
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# NEW: use paths relative to this file so the site reliably finds its database and assets.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "almacen_ptl.db"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Pick-to-Light API",
    description="API para controlar el sistema de localizador de almacenes",
    version="1.0.0",
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    # Esto permite acceder a las columnas por nombre en lugar de indices.
    conn.row_factory = sqlite3.Row
    return conn


# NEW: expose the browser assets used by the Pick-to-Light website.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def read_root():
    # NEW: the root URL now opens the warehouse search page instead of FastAPI docs.
    return FileResponse(STATIC_DIR / "index.html")


def buscar_part_number_en_db(part_number: str):
    part_number = part_number.strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT i.part_number, u.rack, u.columna, u.nivel, u.posicion, u.id_ubicacion
        FROM inventario i
        JOIN ubicaciones u ON i.id_ubicacion = u.id_ubicacion
        WHERE i.part_number = ?
    """
    cursor.execute(query, (part_number,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado is None:
        return None

    return dict(resultado)


@app.get("/inventario/{part_number}")
def buscar_ubicacion(part_number: str):
    resultado = buscar_part_number_en_db(part_number)

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail=f"El SKU {part_number} no se encuentra en el almacen o la base de datos esta vacia",
        )

    return resultado


@app.post("/importar-layout")
async def importar_layout(archivo: UploadFile = File(...)):
    # NEW: this endpoint is used by the website to replace the current inventory from Excel.
    filename = archivo.filename or ""
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato .xlsx")

    contenido = await archivo.read()
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
        sheet = workbook.active
        if sheet is None:
            raise ValueError("El Excel no contiene una hoja activa")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el Excel: {str(e)}")

    conn = get_db_connection()
    cursor = conn.cursor()
    ubicaciones_insertadas = 0
    inventario_insertado = 0

    try:
        # NEW: replace old records so re-uploading the same layout cannot create duplicates.
        cursor.execute("DELETE FROM inventario")
        cursor.execute("DELETE FROM ubicaciones")

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) < 6 or row[5] is None or str(row[5]).strip() == "":
                continue

            part_number = str(row[0]).strip() if row[0] is not None else ""
            rack = str(row[1]).strip() if row[1] is not None else ""
            columna = str(row[2]).strip() if row[2] is not None else ""
            nivel = str(row[3]).strip() if row[3] is not None else ""
            posicion = str(row[4]).strip() if row[4] is not None else ""
            id_ubicacion = str(row[5]).strip()

            cursor.execute(
                """
                INSERT INTO ubicaciones (id_ubicacion, rack, columna, nivel, posicion)
                VALUES (?, ?, ?, ?, ?)
                """,
                (id_ubicacion, rack, columna, nivel, posicion),
            )
            ubicaciones_insertadas += 1

            if part_number:
                cursor.execute(
                    "INSERT INTO inventario (part_number, id_ubicacion) VALUES (?, ?)",
                    (part_number, id_ubicacion),
                )
                inventario_insertado += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al importar el Excel: {str(e)}")
    finally:
        conn.close()

    return {
        "status": "success",
        "mensaje": (
            f"Carga completa. Se crearon {ubicaciones_insertadas} ubicaciones "
            f"y se asignaron {inventario_insertado} SKUs."
        ),
    }


if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn

    # NEW: start the browser on the warehouse website; API documentation remains at /docs.
    site_url = "http://127.0.0.1:8000"
    print(f"Open Pick-to-Light here: {site_url}")
    threading.Timer(1.5, lambda: webbrowser.open(site_url)).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
