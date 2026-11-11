import sqlite3
import os

carpeta_usuario = os.path.expanduser("~")
carpeta_app = os.path.join(carpeta_usuario, "PadelManager_Datos")
if not os.path.exists(carpeta_app):
    os.makedirs(carpeta_app)
DB_NAME = os.path.join(carpeta_app, "padel_datos.db")

def conectar():
    return sqlite3.connect(DB_NAME)

def inicializar_db():
    conexion = conectar()
    cursor = conexion.cursor()
    
    # Tabla limpia sin puntos manuales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jugadoras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            posicion TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jornadas (
            fecha TEXT,
            id_liga INTEGER,
            rival TEXT DEFAULT '',
            ganado INTEGER DEFAULT -1,
            PRIMARY KEY (fecha, id_liga)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS convocatorias (
            id_jugadora INTEGER,
            fecha_jornada TEXT,
            id_liga INTEGER,
            estado TEXT,
            FOREIGN KEY (id_jugadora) REFERENCES jugadoras(id),
            FOREIGN KEY (fecha_jornada, id_liga) REFERENCES jornadas(fecha, id_liga)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partidos_acta (
            fecha_jornada TEXT,
            id_liga INTEGER,
            num_pareja INTEGER,
            id_drive INTEGER,
            id_reves INTEGER,
            Rivales_nombres TEXT DEFAULT '',
            s1_nos INTEGER, s1_riv INTEGER,
            s2_nos INTEGER, s2_riv INTEGER,
            s3_nos INTEGER, s3_riv INTEGER,
            ganado INTEGER DEFAULT -1,
            PRIMARY KEY (fecha_jornada, id_liga, num_pareja),
            FOREIGN KEY (fecha_jornada, id_liga) REFERENCES jornadas(fecha, id_liga)
        )
    ''')
    conexion.commit()
    conexion.close()

# --- FUNCIONES DE JUGADORAS BLINDADAS ---

def agregar_jugadora(nombre, posicion):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO jugadoras (nombre, posicion) VALUES (?, ?)", (nombre, posicion))
        conexion.commit()
        return True
    except sqlite3.IntegrityError:
        return False 
    finally:
        conexion.close()

def modificar_jugadora(id_jugadora, nombre, posicion):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE jugadoras SET nombre = ?, posicion = ? WHERE id = ?", (nombre, posicion, id_jugadora))
        exito = cursor.rowcount > 0
        conexion.commit()
        return exito
    except Exception:
        return False
    finally:
        conexion.close()

def eliminar_jugadora(id_jugadora):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM jugadoras WHERE id = ?", (id_jugadora,))
    cursor.execute("DELETE FROM convocatorias WHERE id_jugadora = ?", (id_jugadora,))
    conexion.commit()
    conexion.close()

# --- FUNCIONES DE JORNADAS, ACTAS Y ESTADÍSTICAS ---

def existe_jornada(fecha, id_liga):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT 1 FROM jornadas WHERE fecha = ? AND id_liga = ?", (fecha, id_liga))
    existe = cursor.fetchone() is not None
    conexion.close()
    return existe

def eliminar_jornada(fecha, id_liga):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM partidos_acta WHERE fecha_jornada = ? AND id_liga = ?", (fecha, id_liga))
    cursor.execute("DELETE FROM convocatorias WHERE fecha_jornada = ? AND id_liga = ?", (fecha, id_liga))
    cursor.execute("DELETE FROM jornadas WHERE fecha = ? AND id_liga = ?", (fecha, id_liga))
    conexion.commit()
    conexion.close()

def registrar_convocatoria(id_jugadora, id_liga, fecha, estado):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("INSERT OR IGNORE INTO jornadas (fecha, id_liga) VALUES (?, ?)", (fecha, id_liga))
    cursor.execute("INSERT INTO convocatorias (id_jugadora, fecha_jornada, id_liga, estado) VALUES (?, ?, ?, ?)",(id_jugadora, fecha, id_liga, estado))
    conexion.commit()
    conexion.close()

def guardar_alineacion_completa(fecha, id_liga, parejas, suplentes):
    """Guarda de forma atómica la convocatoria y deja pre-creada el acta con las Parejas 1, 2 y 3."""
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT OR IGNORE INTO jornadas (fecha, id_liga, rival, ganado) VALUES (?, ?, '', -1)", (fecha, id_liga))
        
        for i, p in enumerate(parejas):
            num_p = i + 1
            id_d = p['drive']['id']
            id_r = p['reves']['id']
            cursor.execute("INSERT INTO convocatorias (id_jugadora, fecha_jornada, id_liga, estado) VALUES (?, ?, ?, 'Convocada')", (id_d, fecha, id_liga))
            cursor.execute("INSERT INTO convocatorias (id_jugadora, fecha_jornada, id_liga, estado) VALUES (?, ?, ?, 'Convocada')", (id_r, fecha, id_liga))
            cursor.execute('''
                INSERT INTO partidos_acta (fecha_jornada, id_liga, num_pareja, id_drive, id_reves)
                VALUES (?, ?, ?, ?, ?)
            ''', (fecha, id_liga, num_p, id_d, id_r))
            
        for s in suplentes:
            cursor.execute("INSERT INTO convocatorias (id_jugadora, fecha_jornada, id_liga, estado) VALUES (?, ?, ?, 'Descartada')", (s['id'], fecha, id_liga))
            
        conexion.commit()
        return True
    except Exception as e:
        print("Error guardando alineación:", e)
        return False
    finally:
        conexion.close()

def guardar_acta_encuentro(fecha, id_liga, rival, ganado_encuentro, lista_partidos, ids_descartadas=None):
    """Guarda el acta completa (sets, parejas, rivales y victoria) y sincroniza las convocatorias."""
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        
        cursor.execute('''
            INSERT INTO jornadas (fecha, id_liga, rival, ganado)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fecha, id_liga) DO UPDATE SET rival = excluded.rival, ganado = excluded.ganado
        ''', (fecha, id_liga, rival, ganado_encuentro))
        
        cursor.execute("DELETE FROM partidos_acta WHERE fecha_jornada = ? AND id_liga = ?", (fecha, id_liga))
        
        ids_titulares = []
        for p in lista_partidos:
            ids_titulares.extend([p['id_drive'], p['id_reves']])
            cursor.execute('''
                INSERT INTO partidos_acta (
                    fecha_jornada, id_liga, num_pareja, id_drive, id_reves, Rivales_nombres,
                    s1_nos, s1_riv, s2_nos, s2_riv, s3_nos, s3_riv, ganado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fecha, id_liga, p['num_pareja'], p['id_drive'], p['id_reves'], p.get('rivales_pareja', ''),
                p['s1_nos'], p['s1_riv'], p['s2_nos'], p['s2_riv'], p['s3_nos'], p['s3_riv'], p['ganado']
            ))
            
        # Sincronizar convocatorias para que las estadísticas de rotación estén siempre al día
        if ids_descartadas is None:
            cursor.execute("SELECT id_jugadora FROM convocatorias WHERE fecha_jornada = ? AND id_liga = ? AND estado = 'Descartada'", (fecha, id_liga))
            ids_descartadas = [r[0] for r in cursor.fetchall() if r[0] not in ids_titulares]
            
        cursor.execute("DELETE FROM convocatorias WHERE fecha_jornada = ? AND id_liga = ?", (fecha, id_liga))
        for id_t in ids_titulares:
            if id_t:
                cursor.execute("INSERT INTO convocatorias (id_jugadora, fecha_jornada, id_liga, estado) VALUES (?, ?, ?, 'Convocada')", (id_t, fecha, id_liga))
        for id_d in ids_descartadas:
            if id_d and id_d not in ids_titulares:
                cursor.execute("INSERT INTO convocatorias (id_jugadora, fecha_jornada, id_liga, estado) VALUES (?, ?, ?, 'Descartada')", (id_d, fecha, id_liga))
                
        conexion.commit()
        return True
    except Exception as e:
        print("Error guardando acta:", e)
        return False
    finally:
        conexion.close()

def obtener_acta_encuentro(fecha, id_liga):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT rival, ganado FROM jornadas WHERE fecha = ? AND id_liga = ?", (fecha, id_liga))
    fila_j = cursor.fetchone()
    if not fila_j:
        conexion.close()
        return None
        
    cursor.execute('''
        SELECT num_pareja, id_drive, id_reves, Rivales_nombres, s1_nos, s1_riv, s2_nos, s2_riv, s3_nos, s3_riv, ganado
        FROM partidos_acta WHERE fecha_jornada = ? AND id_liga = ? ORDER BY num_pareja ASC
    ''', (fecha, id_liga))
    filas_p = cursor.fetchall()
    
    partidos = []
    for fp in filas_p:
        partidos.append({
            "num_pareja": fp[0], "id_drive": fp[1], "id_reves": fp[2], "rivales_pareja": fp[3] or "",
            "s1_nos": fp[4], "s1_riv": fp[5], "s2_nos": fp[6], "s2_riv": fp[7], "s3_nos": fp[8], "s3_riv": fp[9],
            "ganado": fp[10]
        })
        
    # Si era una jornada antigua sin parejas asignadas todavía, repartimos las 6 convocadas en P1, P2 y P3
    if not partidos:
        cursor.execute("SELECT id_jugadora FROM convocatorias WHERE fecha_jornada = ? AND id_liga = ? AND estado = 'Convocada'", (fecha, id_liga))
        convocadas = [r[0] for r in cursor.fetchall()]
        for i in range(3):
            id_d = convocadas[i*2] if len(convocadas) > i*2 else None
            id_r = convocadas[i*2+1] if len(convocadas) > i*2+1 else None
            partidos.append({
                "num_pareja": i+1, "id_drive": id_d, "id_reves": id_r, "rivales_pareja": "",
                "s1_nos": None, "s1_riv": None, "s2_nos": None, "s2_riv": None, "s3_nos": None, "s3_riv": None,
                "ganado": -1
            })
            
    cursor.execute("SELECT id_jugadora FROM convocatorias WHERE fecha_jornada = ? AND id_liga = ? AND estado = 'Descartada'", (fecha, id_liga))
    descartadas = [r[0] for r in cursor.fetchall()]
    conexion.close()
    
    return {
        "rival": fila_j[0] or "",
        "ganado": fila_j[1] if fila_j[1] is not None else -1,
        "partidos": partidos,
        "descartadas": descartadas
    }

def obtener_jornadas_guardadas():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT fecha, id_liga, rival, ganado FROM jornadas ORDER BY fecha DESC")
    filas = cursor.fetchall()
    conexion.close()
    res = []
    for f in filas:
        res.append({
            "fecha": f[0],
            "id_liga": f[1],
            "nombre_liga": "Bullpadel" if f[1] == 1 else "Interclubes",
            "rival": f[2] if f[2] else "Sin rival asignado",
            "ganado": f[3] if f[3] is not None else -1
        })
    return res

def calcular_puntos_bullpadel_actas(factor_division=0.80):
    """Calcula los puntos ganados en actas EXCLUSIVAMENTE de Bullpadel (id_liga = 1) para 5ª División (80%)."""
    conexion = conectar()
    cursor = conexion.cursor()
    
    # Obtenemos todas las jornadas de Bullpadel (id_liga = 1)
    cursor.execute("SELECT fecha, ganado FROM jornadas WHERE id_liga = 1")
    jornadas_bp = cursor.fetchall()
    
    puntos_acumulados = {}
    
    for fecha, ganado_encuentro in jornadas_bp:
        cursor.execute('''
            SELECT num_pareja, id_drive, id_reves, s1_nos, s1_riv, s2_nos, s2_riv, s3_nos, s3_riv, ganado
            FROM partidos_acta WHERE fecha_jornada = ? AND id_liga = 1
        ''', (fecha,))
        partidos = cursor.fetchall()
        
        for p in partidos:
            num_p, id_d, id_r, s1n, s1r, s2n, s2r, s3n, s3r, ganado_p = p
            
            # Contar cuántos sets se disputaron realmente
            sets_jugados = 0
            for sn, sr in [(s1n, s1r), (s2n, s2r), (s3n, s3r)]:
                if sn is not None and sr is not None and (sn > 0 or sr > 0):
                    sets_jugados += 1
                    
            pts_partido = 0
            if ganado_p == 1:
                if num_p == 1:
                    pts_partido = 1000 if sets_jugados == 2 else 900
                elif num_p == 2:
                    pts_partido = 800 if sets_jugados == 2 else 700
                elif num_p == 3:
                    pts_partido = 600 if sets_jugados == 2 else 500
                    
            # Bonus de +100 puntos a las 6 titulares si el equipo ganó el enfrentamiento
            bonus_equipo = 100 if ganado_encuentro == 1 else 0
            pts_totales_jornada = round((pts_partido + bonus_equipo) * factor_division, 1)
            
            for id_jug in (id_d, id_r):
                if id_jug:
                    puntos_acumulados[id_jug] = puntos_acumulados.get(id_jug, 0.0) + pts_totales_jornada
                    
    conexion.close()
    return puntos_acumulados

def obtener_jugadoras():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, posicion FROM jugadoras ORDER BY nombre")
    filas = cursor.fetchall()
    conexion.close()
    
    pts_actas = calcular_puntos_bullpadel_actas()
    return [{
        "id": f[0],
        "nombre": f[1],
        "posicion": f[2],
        "puntos": round(pts_actas.get(f[0], 0.0), 1)
    } for f in filas]

def obtener_estadisticas_jugadoras(id_liga=None):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, posicion FROM jugadoras")
    jugadoras = cursor.fetchall()
    
    pts_actas = calcular_puntos_bullpadel_actas()
    estadisticas = []
    
    for jug in jugadoras:
        id_j = jug[0]
        cursor.execute("SELECT COUNT(*) FROM convocatorias WHERE id_jugadora = ? AND estado = 'Convocada'", (id_j,))
        jugados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM convocatorias WHERE id_jugadora = ? AND estado = 'Descartada'", (id_j,))
        descartes = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(fecha_jornada) FROM convocatorias WHERE id_jugadora = ? AND estado = 'Convocada'", (id_j,))
        ultima = cursor.fetchone()[0]
        
        estadisticas.append({
            "id": id_j,
            "nombre": jug[1],
            "posicion": jug[2],
            "puntos": round(pts_actas.get(id_j, 0.0), 1),
            "partidos_jugados": jugados,
            "veces_descartada": descartes,
            "ultima_convocatoria": ultima
        })
    conexion.close()
    return estadisticas