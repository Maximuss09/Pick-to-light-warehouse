from fastapi import FastAPI, HTTPException, UploadFile, File
import sqlite3
import io
import openpyxl

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

    # 3. Endpoint para importar el archivo Excel (.xlsx)
@app.post("/importar-layout")
async def importar_layout(archivo: UploadFile = File(...)):
    # Validamos que sea un archivo Excel
    if not archivo.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato .xlsx")
    
    # Leemos el contenido binario en memoria
    contenido = await archivo.read()
    
    try:
        # Cargamos el archivo Excel
        workbook = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
        sheet = workbook.active
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el Excel: {str(e)}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    ubicaciones_insertadas = 0
    inventario_insertado = 0
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        
        # Validamos que la fila tenga al menos 6 columnas y que la Ubicación (índice 5) no esté vacía
        if len(row) < 6 or row[5] is None or str(row[5]).strip() == "":
            continue
            
        # Ajustamos los índices a la estructura limpia (0 a 5)
        part_number = str(row[0]).strip() if row[0] is not None else ""
        rack = str(row[1]).strip() if row[1] is not None else ""
        columna = str(row[2]).strip() if row[2] is not None else ""
        nivel = str(row[3]).strip() if row[3] is not None else ""
        posicion = str(row[4]).strip() if row[4] is not None else ""
        id_ubicacion = str(row[5]).strip()

        # Insertamos la ubicación.
        cursor.execute('''
        INSERT OR IGNORE INTO ubicaciones (id_ubicacion, rack, columna, nivel, posicion)
        VALUES (?, ?, ?, ?, ?)
        ''', (id_ubicacion, rack, columna, nivel, posicion))
        ubicaciones_insertadas += cursor.rowcount

        # Si hay un número de parte, lo metemos al inventario
        if part_number:
            cursor.execute('''
            INSERT INTO inventario (part_number, id_ubicacion)
            VALUES (?, ?)
            ''', (part_number, id_ubicacion))
            inventario_insertado += 1

    conn.commit()
    conn.close()
    
    return {
        "status": "success", 
        "mensaje": f"Carga completa. Se crearon {ubicaciones_insertadas} ubicaciones y se asignaron {inventario_insertado} SKUs."
    }