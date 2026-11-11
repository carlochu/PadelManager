import sqlite3
import os

# 1. Buscamos la carpeta personal del usuario de Windows (ej. C:\Users\NombreMadre)
carpeta_usuario = os.path.expanduser("~")

# 2. Creamos una carpeta oculta o dedicada para los datos de la app
carpeta_app = os.path.join(carpeta_usuario, "PadelManager_Datos")

# 3. CRÍTICO: Obligamos a Windows a crear la carpeta si no existe ANTES de conectar SQLite
if not os.path.exists(carpeta_app):
    os.makedirs(carpeta_app)

# 4. Asignamos la ruta final
DB_NAME = os.path.join(carpeta_app, "padel_datos.db")

def conectar():
    """Establece la conexión con la base de datos SQLite."""
    return sqlite3.connect(DB_NAME)
    
# ... (El resto de tus funciones inicializar_db, agregar_jugadora, etc. siguen igual debajo)

def inicializar_db():
    """Crea la estructura de tablas la primera vez que se abre la app."""
    conexion = conectar()
    cursor = conexion.cursor()

    # 1. Tabla de Jugadoras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jugadoras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            posicion TEXT NOT NULL -- Esperamos 'Drive', 'Revés' o 'Comodín'
        )
    ''')

    # 2. Tabla de Ligas (Bullpadel e Interclubes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ligas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')

    # 3. Tabla de Convocatorias (El historial para el algoritmo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS convocatorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_jugadora INTEGER,
            id_liga INTEGER,
            fecha DATE NOT NULL,
            estado TEXT NOT NULL, -- Esperamos 'Convocada' o 'Descartada'
            FOREIGN KEY(id_jugadora) REFERENCES jugadoras(id),
            FOREIGN KEY(id_liga) REFERENCES ligas(id)
        )
    ''')

    # Insertamos las dos ligas automáticamente si no existen
    cursor.execute('INSERT OR IGNORE INTO ligas (nombre) VALUES ("Bullpadel"), ("Interclubes")')

    conexion.commit()
    conexion.close()
    print("Estructura de la base de datos creada/verificada con éxito.")


def agregar_jugadora(nombre, posicion):
    """Inserta una nueva jugadora en la base de datos."""
    conexion = conectar()
    cursor = conexion.cursor()
    # Usamos interrogaciones (?) para evitar inyecciones SQL y errores de sintaxis
    cursor.execute('INSERT INTO jugadoras (nombre, posicion) VALUES (?, ?)', (nombre, posicion))
    conexion.commit()
    conexion.close()

def obtener_jugadoras():
    """Devuelve una lista con todas las jugadoras."""
    conexion = conectar()
    # TRUCO: sqlite3.Row permite acceder a las columnas por su nombre (ej. jugadora['nombre'])
    # en lugar de por índices numéricos. Esto le facilitará mucho la vida al algoritmo luego.
    conexion.row_factory = sqlite3.Row 
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM jugadoras')
    
    # Convertimos los resultados directamente a una lista de diccionarios de Python
    jugadoras = [dict(row) for row in cursor.fetchall()]
    conexion.close()
    return jugadoras

def registrar_convocatoria(id_jugadora, id_liga, fecha, estado):
    """Guarda si una jugadora ha sido convocada o descartada en una fecha y liga concreta."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO convocatorias (id_jugadora, id_liga, fecha, estado) 
        VALUES (?, ?, ?, ?)
    ''', (id_jugadora, id_liga, fecha, estado))
    conexion.commit()
    conexion.close()

def obtener_jornadas_guardadas():
    """Devuelve la lista de fechas y ligas que ya tienen datos guardados en BD."""
    conexion = conectar()
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    # Agrupamos por fecha y liga para sacar el listado principal
    cursor.execute('''
        SELECT DISTINCT c.fecha, c.id_liga, l.nombre as nombre_liga
        FROM convocatorias c
        JOIN ligas l ON c.id_liga = l.id
        ORDER BY c.fecha DESC
    ''')
    jornadas = [dict(row) for row in cursor.fetchall()]
    conexion.close()
    return jornadas

def obtener_estado_jugadoras_jornada(fecha, id_liga):
    """Devuelve cómo estaba guardada cada jugadora en un partido concreto."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT id_jugadora, estado FROM convocatorias WHERE fecha = ? AND id_liga = ?', (fecha, id_liga))
    # Devolvemos un diccionario {id_jugadora: "estado"} para que la interfaz lo lea rapidísimo
    estados = {row[0]: row[1] for row in cursor.fetchall()}
    conexion.close()
    return estados

def eliminar_jornada(fecha, id_liga):
    """Borra todos los registros de una jornada concreta."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('DELETE FROM convocatorias WHERE fecha = ? AND id_liga = ?', (fecha, id_liga))
    conexion.commit()
    conexion.close()

def existe_jornada(fecha, id_liga):
    """Comprueba si ya hay datos guardados para esa fecha y liga en concreto."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT 1 FROM convocatorias WHERE fecha = ? AND id_liga = ? LIMIT 1', (fecha, id_liga))
    existe = cursor.fetchone() is not None
    conexion.close()
    return existe

def modificar_jugadora(id_jugadora, nombre, posicion):
    """Actualiza los datos de una jugadora existente."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('UPDATE jugadoras SET nombre = ?, posicion = ? WHERE id = ?', (nombre, posicion, id_jugadora))
    conexion.commit()
    conexion.close()

def eliminar_jugadora(id_jugadora):
    """Borra a la jugadora y todo su historial de convocatorias."""
    conexion = conectar()
    cursor = conexion.cursor()
    # 1. Borramos su historial para no dejar datos corruptos
    cursor.execute('DELETE FROM convocatorias WHERE id_jugadora = ?', (id_jugadora,))
    # 2. Borramos a la jugadora
    cursor.execute('DELETE FROM jugadoras WHERE id = ?', (id_jugadora,))
    conexion.commit()
    conexion.close()

# --- BLOQUE DE PRUEBA ---
# Este código solo se ejecuta si corremos este archivo directamente.
if __name__ == "__main__":
    inicializar_db()
    
    # 1. Limpiamos la tabla por si ejecutas el script varias veces (para no duplicar las de prueba)
    conexion = conectar()
    conexion.execute("DELETE FROM jugadoras") 
    conexion.execute("DELETE FROM sqlite_sequence WHERE name='jugadoras'") # Resetea el contador de IDs
    conexion.commit()
    conexion.close()
    
    # 2. Insertamos a las compañeras de tu madre
    agregar_jugadora("Marta", "Drive")
    agregar_jugadora("Laura", "Revés")
    agregar_jugadora("Ana", "Comodín")
    
    # 3. Extraemos y mostramos los datos
    lista_jugadoras = obtener_jugadoras()
    print("\n--- Lista de Jugadoras en la BD ---")
    for j in lista_jugadoras:
        print(f"ID: {j['id']} | Nombre: {j['nombre']} | Posición: {j['posicion']}")

def obtener_estadisticas_jugadoras(id_liga):
    """Obtiene a todas las jugadoras con sus cálculos de partidos y descartes para una liga."""
    conexion = conectar()
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    
    # Esta consulta SQL agrupa el historial. 
    # COALESCE convierte los valores nulos (cuando no tienen historial) en 0.
    consulta = '''
        SELECT 
            j.id, 
            j.nombre, 
            j.posicion,
            COALESCE(SUM(CASE WHEN c.estado = 'Convocada' THEN 1 ELSE 0 END), 0) AS partidos_jugados,
            MAX(CASE WHEN c.estado = 'Convocada' THEN c.fecha ELSE NULL END) AS ultima_convocatoria,
            COALESCE(SUM(CASE WHEN c.estado = 'Descartada' THEN 1 ELSE 0 END), 0) AS veces_descartada
        FROM jugadoras j
        LEFT JOIN convocatorias c ON j.id = c.id_jugadora AND c.id_liga = ?
        GROUP BY j.id, j.nombre, j.posicion
    '''
    cursor.execute(consulta, (id_liga,))
    estadisticas = [dict(row) for row in cursor.fetchall()]
    conexion.close()
    return estadisticas