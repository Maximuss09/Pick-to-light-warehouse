from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import sqlite3
import io
import openpyxl



app = FastAPI(
    title="Pick-to-Light API",
    description="API para controlar el sistema de localizador de almacenes",
    version="1.0.0"
)

class ChatMessage(BaseModel):
    message: str

class WebhookMessage(BaseModel):
    from_user: str
    message: str

def get_db_connection():
    conn = sqlite3.connect('almacen_ptl.db')
    # Esto permite acceder a las columnas por nombre en lugar de Ã­ndices
    conn.row_factory = sqlite3.Row 
    return conn

# Buscar numero de parte 
@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")

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
        raise HTTPException(status_code=404, detail=f"El SKU {part_number} no se encuentra en el almacen o la base de datos esta vacia")

    return resultado


# Inicio de input de chatbot
@app.post("/chatbot")
def chatbot(request: ChatMessage):
    part_number = request.message.strip()

    if not part_number:
        return {
            "reply": "Please send a part number to search."
        }

    resultado = buscar_part_number_en_db(part_number)

    if resultado is None:
        return {
            "reply": f"I could not find part number {part_number} in the warehouse."
        }

    return {
        "reply": (
            f"Part number {resultado['part_number']} is located at "
            f"Rack {resultado['rack']}, Column {resultado['columna']}, "
            f"Level {resultado['nivel']}, Position {resultado['posicion']} "
            f"(Location ID: {resultado['id_ubicacion']})."
        )
    }



# Simulacion local de un webhook de WhatsApp
@app.post("/webhook")
def webhook_whatsapp_local(request: WebhookMessage):
    chatbot_response = chatbot(ChatMessage(message=request.message))

    return {
        "from": request.from_user,
        "message_received": request.message,
        "reply": chatbot_response["reply"]
    }

    # 3. Endpoint para importar el archivo Excel (.xlsx)
@app.post("/importar-layout")
async def importar_layout(archivo: UploadFile = File(...)):
    # Validamos que sea un archivo Excel
    filename = archivo.filename or ""
    if not filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato .xlsx")
    
    # Leemos el contenido binario en memoria
    contenido = await archivo.read()
    
    try:
        # Cargamos el archivo Excel
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
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        
        # Validamos que la fila tenga al menos 6 columnas y que la UbicaciÃ³n (Ã­ndice 5) no estÃ© vacÃ­a
        if len(row) < 6 or row[5] is None or str(row[5]).strip() == "":
            continue
            
        # Ajustamos los Ã­ndices a la estructura limpia (0 a 5)
        part_number = str(row[0]).strip() if row[0] is not None else ""
        rack = str(row[1]).strip() if row[1] is not None else ""
        columna = str(row[2]).strip() if row[2] is not None else ""
        nivel = str(row[3]).strip() if row[3] is not None else ""
        posicion = str(row[4]).strip() if row[4] is not None else ""
        id_ubicacion = str(row[5]).strip()

        # Insertamos la ubicaciÃ³n.
        cursor.execute('''
        INSERT OR IGNORE INTO ubicaciones (id_ubicacion, rack, columna, nivel, posicion)
        VALUES (?, ?, ?, ?, ?)
        ''', (id_ubicacion, rack, columna, nivel, posicion))
        ubicaciones_insertadas += cursor.rowcount

        # Si hay un nÃºmero de parte, lo metemos al inventario
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


if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn

    docs_url = "http://127.0.0.1:8000/docs"
    threading.Timer(1.5, lambda: webbrowser.open(docs_url)).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
