import database as db
import os

print("1. Limpiando la base de datos para entorno de pruebas realista (5ª División)...")
if os.path.exists(db.DB_NAME):
    os.remove(db.DB_NAME)
db.inicializar_db()

# 10 jugadoras con 0.0 puntos base (los puntos saldrán 100% de las actas reales de Bullpadel)
jugadoras_prueba = [
    ("MARTA", "REVES"),          # ID 1
    ("CARLA", "REVES/DERECHA"),  # ID 2
    ("SOFIA", "REVES"),          # ID 3
    ("ANA", "REVES/DERECHA"),    # ID 4
    ("MERCHE", "REVES"),         # ID 5
    ("LAURA", "DERECHA/REVES"),  # ID 6
    ("DOLO", "DERECHA"),         # ID 7
    ("BEA", "DERECHA/REVES"),    # ID 8
    ("SARA", "DERECHA"),         # ID 9
    ("ELENA", "DERECHA")         # ID 10
]

print("2. Añadiendo las 10 jugadoras...")
for nombre, pos in jugadoras_prueba:
    db.agregar_jugadora(nombre, pos)

# =========================================================================
# JORNADA 1: BULLPADEL (id_liga = 1) -> VICTORIA 2-1 contra Club Pádel Turia
# =========================================================================
# - P1 (Laura y Marta): Ganan 6-4, 6-2 (2 sets) -> 800 pts + 80 bonus = 880 pts c/u
# - P2 (Dolo y Carla): Ganan 6-3, 4-6, 6-4 (3 sets) -> 560 pts + 80 bonus = 640 pts c/u
# - P3 (Bea y Sofia): Pierden 4-6, 3-6 -> 0 pts + 80 bonus = 80 pts c/u
# - Descartadas: Ana (4), Merche (5), Sara (9), Elena (10)
print("3. Registrando Acta Jornada 1 (Bullpadel - Victoria 2-1)...")
partidos_j1 = [
    {"num_pareja": 1, "id_drive": 6, "id_reves": 1, "rivales_pareja": "Gómez / Pérez", "s1_nos": 6, "s1_riv": 4, "s2_nos": 6, "s2_riv": 2, "s3_nos": None, "s3_riv": None, "ganado": 1},
    {"num_pareja": 2, "id_drive": 7, "id_reves": 2, "rivales_pareja": "Ruiz / Sanz", "s1_nos": 6, "s1_riv": 3, "s2_nos": 4, "s2_riv": 6, "s3_nos": 6, "s3_riv": 4, "ganado": 1},
    {"num_pareja": 3, "id_drive": 8, "id_reves": 3, "rivales_pareja": "Vidal / Camps", "s1_nos": 4, "s1_riv": 6, "s2_nos": 3, "s2_riv": 6, "s3_nos": None, "s3_riv": None, "ganado": 0}
]
db.guardar_acta_encuentro("2026-10-24", 1, "Club Pádel Turia", 1, partidos_j1, ids_descartadas=[4, 5, 9, 10])

# =========================================================================
# JORNADA 2: INTERCLUBES (id_liga = 2) -> VICTORIA 3-0 contra Sporting Picanya
# =========================================================================
# ¡IMPORTANTE!: Suma partidos jugados y descartes para rotación, pero 0 PUNTOS Bullpadel.
# - Juegan las que descansaron antes + 2 repetidas: Sara(9), Ana(4), Elena(10), Merche(5), Bea(8), Sofia(3)
# - Descartadas: Marta(1), Carla(2), Laura(6), Dolo(7)
print("4. Registrando Acta Jornada 2 (Interclubes - Victoria 3-0, 0 pts Bullpadel)...")
partidos_j2 = [
    {"num_pareja": 1, "id_drive": 9, "id_reves": 4, "rivales_pareja": "Pareja A", "s1_nos": 6, "s1_riv": 1, "s2_nos": 6, "s2_riv": 2, "s3_nos": None, "s3_riv": None, "ganado": 1},
    {"num_pareja": 2, "id_drive": 10, "id_reves": 5, "rivales_pareja": "Pareja B", "s1_nos": 7, "s1_riv": 5, "s2_nos": 6, "s2_riv": 4, "s3_nos": None, "s3_riv": None, "ganado": 1},
    {"num_pareja": 3, "id_drive": 8, "id_reves": 3, "rivales_pareja": "Pareja C", "s1_nos": 6, "s1_riv": 3, "s2_nos": 6, "s2_riv": 4, "s3_nos": None, "s3_riv": None, "ganado": 1}
]
db.guardar_acta_encuentro("2026-10-31", 2, "Sporting Picanya", 1, partidos_j2, ids_descartadas=[1, 2, 6, 7])

# =========================================================================
# JORNADA 3: BULLPADEL (id_liga = 1) -> DERROTA 1-2 contra Pádel Vedat
# =========================================================================
# - P1 (Laura y Marta): Pierden 5-7, 4-6 -> 0 pts (se quedan en 880 pts)
# - P2 (Dolo y Ana): Ganan 6-4, 6-4 (2 sets) -> +640 pts c/u (sin bonus equipo por derrota 1-2)
# - P3 (Sara y Merche): Pierden 6-2, 3-6, 4-6 -> 0 pts
# - Descartadas: Carla(2), Sofia(3), Bea(8), Elena(10)
print("5. Registrando Acta Jornada 3 (Bullpadel - Derrota 1-2)...")
partidos_j3 = [
    {"num_pareja": 1, "id_drive": 6, "id_reves": 1, "rivales_pareja": "Navarro / Gil", "s1_nos": 5, "s1_riv": 7, "s2_nos": 4, "s2_riv": 6, "s3_nos": None, "s3_riv": None, "ganado": 0},
    {"num_pareja": 2, "id_drive": 7, "id_reves": 4, "rivales_pareja": "Ortega / Soler", "s1_nos": 6, "s1_riv": 4, "s2_nos": 6, "s2_riv": 4, "s3_nos": None, "s3_riv": None, "ganado": 1},
    {"num_pareja": 3, "id_drive": 9, "id_reves": 5, "rivales_pareja": "Blasco / Mora", "s1_nos": 6, "s1_riv": 2, "s2_nos": 3, "s2_riv": 6, "s3_nos": 4, "s3_riv": 6, "ganado": 0}
]
db.guardar_acta_encuentro("2026-11-07", 1, "Pádel Vedat", 0, partidos_j3, ids_descartadas=[2, 3, 8, 10])

print("\n¡Datos inyectados! Resumen de puntos Bullpadel (5ª Div) calculados automáticamente:")
for j in db.obtener_jugadoras():
    print(f" - {j['nombre']:8} ({j['posicion']:13}) -> Total: {j['puntos']} pts")