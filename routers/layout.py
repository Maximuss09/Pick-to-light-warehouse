"""NEW: HTTP route for replacing inventory from an Excel layout file."""

import io

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openpyxl.worksheet.worksheet import Worksheet

from database import get_db_connection
from security import require_layout_upload_access, upload_security

router = APIRouter(tags=["layout"])


@router.post("/importar-layout")
async def importar_layout(
    archivo: UploadFile = File(...),
    authenticated_user: str = Depends(require_layout_upload_access),
):
    """Replace current inventory and locations using the approved Excel format."""
    filename = archivo.filename or ""
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato .xlsx")

    contenido = await archivo.read()
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
        sheet = workbook.active
        # NEW: reject workbooks whose active sheet cannot contain inventory rows.
        if not isinstance(sheet, Worksheet):
            raise ValueError("El Excel no contiene una hoja de trabajo valida")
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error al leer el Excel: {str(error)}")

    conn = get_db_connection()
    cursor = conn.cursor()
    ubicaciones_insertadas = 0
    inventario_insertado = 0

    try:
        # The import is a full replacement so re-uploading cannot create duplicate records.
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
    except Exception as error:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al importar el Excel: {str(error)}")
    finally:
        conn.close()

    return {
        "status": "success",
        "mensaje": (
            f"Carga completa. Se crearon {ubicaciones_insertadas} ubicaciones "
            f"y se asignaron {inventario_insertado} SKUs."
        ),
    }
