from fastapi import FastAPI, HTTPException
import sqlite3

app = FastAPI(
    title="Pick-to-Light API",
    description="API para controlar el sistema de localizador de almacenes",
    version="1.0.0"
)

def get_db_connection():
    conn = sqlite3.connect('almacen_ptl.db')
    # Esto permite acceder a las columnas por nombre en lugar de índices
    conn.row_factory = sqlite3.Row 
    return conn

# Buscar numero de parte 
@app.get("/")
def read_root():
    return {"status": "ok", "mensaje": "Servidor Pick-to-Light funcionando correctamente"}

@app.get("/inventario/{part_number}")
def buscar_ubicacion(part_number: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscamos el part_number uniendo la tabla inventario con ubicaciones
    query = """
        SELECT i.part_number, u.rack, u.columna, u.nivel, u.posicion, u.id_ubicacion
        FROM inventario i
        JOIN ubicaciones u ON i.id_ubicacion = u.id_ubicacion
        WHERE i.part_number = ?
    """
    
    # Ejecutamos la consulta
    cursor.execute(query, (part_number,))
    resultado = cursor.fetchone()
    conn.close()
    
    # Si no existe, devolvemos un error 404 (No encontrado)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"El SKU {part_number} no se encuentra en el almacén o la base de datos está vacía")
        
    # Si existe, lo devolvemos en formato JSON
    return dict(resultado)