import sqlite3

def inicializar_base_datos():
    # Conectar a la base de datos (creará el archivo si no existe)
    conn = sqlite3.connect('almacen_ptl.db')
    cursor = conn.cursor()

    # 1. Crear tabla de ubicaciones físicas y hardware
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ubicaciones (
        id_ubicacion TEXT PRIMARY KEY,
        rack INTEGER,
        columna INTEGER,
        nivel TEXT,
        posicion TEXT,
        ip_controlador TEXT, -- IP del microcontrolador (ESP32/WLED)
        led_asignado INTEGER -- Número de LED en la tira
    )
    ''')

    # 2. Crear tabla de inventario (relaciona el PartNumber con la Ubicacion)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventario (
        part_number TEXT,
        id_ubicacion TEXT,
        FOREIGN KEY(id_ubicacion) REFERENCES ubicaciones(id_ubicacion)
    )
    ''')

    print("Base de datos 'almacen_ptl.db' y tablas vacías creadas correctamente.")

    # Guardar cambios y cerrar
    conn.commit()
    conn.close()

if __name__ == "__main__":
    inicializar_base_datos()