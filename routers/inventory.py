"""NEW: HTTP routes for warehouse part-number searches."""

from fastapi import APIRouter, HTTPException

from database import buscar_part_number_en_db

router = APIRouter(tags=["inventory"])


@router.get("/inventario/{part_number}")
def buscar_ubicacion(part_number: str):
    """Return the location for one part number, or a 404 response."""
    resultado = buscar_part_number_en_db(part_number)
    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail=f"El SKU {part_number} no se encuentra en el almacen o la base de datos esta vacia",
        )
    return resultado
