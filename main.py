from typing import Any
import io
import os
import sqlite3

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel
import openpyxl

from typing import Optional

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
    # Esto permite acceder a las columnas por nombre en lugar de indices.
    conn.row_factory = sqlite3.Row
    return conn


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


# New: shared chatbot reply builder used by /chatbot, /webhook-test, and WhatsApp webhook.
def generar_respuesta_chatbot(message: str):
    part_number = message.strip()

    if not part_number:
        return "Please send a part number to search."

    resultado = buscar_part_number_en_db(part_number)

    if resultado is None:
        return f"I could not find part number {part_number} in the warehouse."

    return (
        f"Part number {resultado['part_number']} is located at "
        f"Rack {resultado['rack']}, Column {resultado['columna']}, "
        f"Level {resultado['nivel']}, Position {resultado['posicion']} "
        f"(Location ID: {resultado['id_ubicacion']})."
    )


@app.get("/inventario/{part_number}")
def buscar_ubicacion(part_number: str):
    resultado = buscar_part_number_en_db(part_number)

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail=f"El SKU {part_number} no se encuentra en el almacen o la base de datos esta vacia"
        )

    return resultado


@app.post("/chatbot")
def chatbot(request: ChatMessage):
    return {
        "reply": generar_respuesta_chatbot(request.message)
    }


# New: simple local webhook test route before connecting real WhatsApp.
@app.post("/webhook-test")
def webhook_whatsapp_local(request: WebhookMessage):
    return {
        "from": request.from_user,
        "message_received": request.message,
        "reply": generar_respuesta_chatbot(request.message)
    }


# New: parser for real WhatsApp Cloud API webhook payloads.
def extraer_mensaje_whatsapp(payload: dict[str, Any]):
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
    except (KeyError, IndexError, TypeError):
        return None

    if message.get("type") != "text":
        return None

    from_user = message.get("from")
    text_body = message.get("text", {}).get("body")

    if not from_user or text_body is None:
        return None

    return {
        "from_user": from_user,
        "message": text_body
    }


# New: Meta webhook verification endpoint for WhatsApp Cloud API setup.
@app.get("/webhook", response_class=PlainTextResponse)
def verificar_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "pick-to-light-dev-token")

    if mode == "subscribe" and token == verify_token and challenge:
        return challenge

    raise HTTPException(status_code=403, detail="Invalid webhook verification token")


# New: receives real WhatsApp webhook events and returns the local chatbot reply for now.
@app.post("/webhook")
async def recibir_webhook_whatsapp(request: Request):
    payload = await request.json()
    mensaje = extraer_mensaje_whatsapp(payload)

    if mensaje is None:
        return {
            "status": "ignored",
            "reason": "No supported WhatsApp text message found."
        }

    return {
        "status": "received",
        "from": mensaje["from_user"],
        "message_received": mensaje["message"],
        "reply": generar_respuesta_chatbot(mensaje["message"])
    }


@app.post("/importar-layout")
async def importar_layout(archivo: UploadFile = File(...)):
    # Validamos que sea un archivo Excel.
    filename = archivo.filename or ""
    if not filename.endswith('.xlsx'):
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

    for row in sheet.iter_rows(min_row=2, values_only=True):
        # Validamos que la fila tenga al menos 6 columnas y que la ubicacion no este vacia.
        if len(row) < 6 or row[5] is None or str(row[5]).strip() == "":
            continue

        part_number = str(row[0]).strip() if row[0] is not None else ""
        rack = str(row[1]).strip() if row[1] is not None else ""
        columna = str(row[2]).strip() if row[2] is not None else ""
        nivel = str(row[3]).strip() if row[3] is not None else ""
        posicion = str(row[4]).strip() if row[4] is not None else ""
        id_ubicacion = str(row[5]).strip()

        cursor.execute('''
        INSERT OR IGNORE INTO ubicaciones (id_ubicacion, rack, columna, nivel, posicion)
        VALUES (?, ?, ?, ?, ?)
        ''', (id_ubicacion, rack, columna, nivel, posicion))
        ubicaciones_insertadas += cursor.rowcount

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

#----------------------------------------------------------------------------------------------

# NEW ENDPOINT FOR CREATION AND MODIFICATION OF LOACTION
class LocationRequest(BaseModel):
    rack: int
    columna: int
    nivel: str
    posicion: str
    part_number: Optional[str] = None

@app.get ("/nomenclature-option")







#------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn

    docs_url = "http://127.0.0.1:8000/docs"
    print(f"Open docs here: {docs_url}")
    threading.Timer(1.5, lambda: webbrowser.open(docs_url)).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
