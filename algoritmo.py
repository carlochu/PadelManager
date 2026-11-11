import database as db

def logica_desempate(jugadora):
    """1. Menos partidos. 2. Fecha antigua. 3. Más descartes."""
    p1_partidos = jugadora['partidos_jugados']
    p2_fecha = jugadora['ultima_convocatoria'] if jugadora['ultima_convocatoria'] else '0000-00-00'
    p3_descartes = -jugadora['veces_descartada']
    return (p1_partidos, p2_fecha, p3_descartes)

def calcular_turno_ganador(disponibilidad_turnos):
    mejor_turno = None
    max_jugadoras = 0
    for turno, ids in disponibilidad_turnos.items():
        cantidad = len(ids)
        if cantidad > max_jugadoras:
            max_jugadoras = cantidad
            mejor_turno = turno
    if max_jugadoras < 6:
        raise ValueError(f"Imposible jugar. El mejor turno solo tiene {max_jugadoras} jugadoras disponibles.")
    return mejor_turno, disponibilidad_turnos[mejor_turno]

def evaluar_pareja(j1, j2):
    """Evalúa si dos jugadoras encajan y devuelve (j_drive, j_reves, afinidad)."""
    def aptitud(pos, lado):
        if lado == "Drive":
            if pos == "DERECHA": return 1
            if pos in ["DERECHA/REVES", "REVES/DERECHA"]: return 0 # Híbridas se adaptan
            return -99 # REVES puro no puede jugar aquí
        else:
            if pos == "REVES": return 1
            if pos in ["DERECHA/REVES", "REVES/DERECHA"]: return 0
            return -99

    score_A = aptitud(j1['posicion'], "Drive") + aptitud(j2['posicion'], "Revés")
    score_B = aptitud(j2['posicion'], "Drive") + aptitud(j1['posicion'], "Revés")

    if score_A < 0 and score_B < 0:
        return None # Incompatible
        
    # Preferencia natural de las híbridas (Drive vs Revés)
    if j1['posicion'] == "DERECHA/REVES" and j2['posicion'] == "REVES/DERECHA": score_A += 2
    if j2['posicion'] == "DERECHA/REVES" and j1['posicion'] == "REVES/DERECHA": score_B += 2

    return (j1, j2, score_A) if score_A >= score_B else (j2, j1, score_B)

def generar_alineacion_parejas(jugadoras_titulares, ordenar_por_puntos=True):
    mejor_distribucion = None
    mejor_afinidad = -999
    j = jugadoras_titulares
    
    # Generar las 15 combinaciones posibles de 3 parejas buscando la máxima comodidad de lado
    for p1_idx in range(1, 6):
        pareja1 = (j[0], j[p1_idx])
        resto = [j[i] for i in range(1, 6) if i != p1_idx]
        for p2_idx in range(1, 4):
            pareja2 = (resto[0], resto[p2_idx])
            resto_final = [resto[i] for i in range(1, 4) if i != p2_idx]
            pareja3 = (resto_final[0], resto_final[1])
            
            ev1 = evaluar_pareja(pareja1[0], pareja1[1])
            ev2 = evaluar_pareja(pareja2[0], pareja2[1])
            ev3 = evaluar_pareja(pareja3[0], pareja3[1])
            
            if ev1 and ev2 and ev3:
                afinidad = ev1[2] + ev2[2] + ev3[2]
                if afinidad > mejor_afinidad:
                    mejor_afinidad = afinidad
                    mejor_distribucion = [ev1, ev2, ev3]
                    
    if not mejor_distribucion:
        raise ValueError("Imposible cuadrar las posiciones de las 6 titulares (faltan jugadoras de Drive o Revés).")
        
    parejas = [{"drive": d, "reves": r, "puntos_suma": d.get('puntos', 0) + r.get('puntos', 0)} for d, r, _ in mejor_distribucion]
    
    # Si es Bullpadel ordenamos de mayor a menor; en Interclubes se queda por orden natural de rotación
    if ordenar_por_puntos:
        parejas.sort(key=lambda x: x["puntos_suma"], reverse=True)
    return parejas

def calcular_sustituciones(parejas, suplentes, validar_puntos=True):
    """Calcula los cambios válidos. En Interclubes solo exige compatibilidad de posición (Drive/Revés)."""
    opciones_suplentes = {}
    puntos_actuales = [p["puntos_suma"] for p in parejas]
    
    for suplente in suplentes:
        opciones = []
        for i, pareja in enumerate(parejas):
            titular_d, titular_r = pareja["drive"], pareja["reves"]
            
            # Prueba suplente en Drive
            if evaluar_pareja(suplente, titular_r):
                es_valido = True
                if validar_puntos:
                    test_puntos = list(puntos_actuales)
                    test_puntos[i] = suplente.get('puntos', 0) + titular_r.get('puntos', 0)
                    es_valido = (test_puntos[0] >= test_puntos[1] >= test_puntos[2])
                if es_valido:
                    opciones.append({
                        "texto": f"Cambiar por {titular_d['nombre']} (P{i+1} Drive)",
                        "sale": titular_d,
                        "lado": "drive",
                        "idx": i
                    })
                    
            # Prueba suplente en Revés
            if evaluar_pareja(titular_d, suplente):
                es_valido = True
                if validar_puntos:
                    test_puntos = list(puntos_actuales)
                    test_puntos[i] = titular_d.get('puntos', 0) + suplente.get('puntos', 0)
                    es_valido = (test_puntos[0] >= test_puntos[1] >= test_puntos[2])
                if es_valido:
                    opciones.append({
                        "texto": f"Cambiar por {titular_r['nombre']} (P{i+1} Revés)",
                        "sale": titular_r,
                        "lado": "reves",
                        "idx": i
                    })
                    
        opciones_suplentes[suplente['id']] = opciones
    return opciones_suplentes

def obtener_alineacion_ideal(id_liga, ids_disponibles):
    estadisticas = db.obtener_estadisticas_jugadoras(id_liga)
    disponibles = sorted([j for j in estadisticas if j['id'] in ids_disponibles], key=logica_desempate)
    
    titulares = disponibles[:6]
    suplentes = disponibles[6:]
    
    es_bullpadel = (id_liga == 1)
    parejas = generar_alineacion_parejas(titulares, ordenar_por_puntos=es_bullpadel)
    sustituciones = calcular_sustituciones(parejas, suplentes, validar_puntos=es_bullpadel)
    
    return {"parejas": parejas, "suplentes": suplentes, "sustituciones": sustituciones}