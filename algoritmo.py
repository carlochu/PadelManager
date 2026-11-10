import database as db

def logica_desempate(jugadora):
    """1. Menos partidos. 2. Fecha más antigua. 3. Más descartes previos."""
    p1_partidos = jugadora['partidos_jugados']
    p2_fecha = jugadora['ultima_convocatoria'] if jugadora['ultima_convocatoria'] else '0000-00-00'
    p3_descartes = -jugadora['veces_descartada']
    return (p1_partidos, p2_fecha, p3_descartes)

def calcular_turno_ganador(disponibilidad_turnos):
    """
    Analiza la matriz de turnos y devuelve el que tenga más jugadoras disponibles.
    disponibilidad_turnos = {'Sábado Mañana': [id1, id2], ...}
    """
    mejor_turno = None
    max_jugadoras = 0
    
    for turno, ids in disponibilidad_turnos.items():
        cantidad = len(ids)
        if cantidad > max_jugadoras:
            max_jugadoras = cantidad
            mejor_turno = turno
            
    if max_jugadoras < 6:
        raise ValueError(f"Imposible jugar. El mejor turno ({mejor_turno if mejor_turno else 'Ninguno'}) solo tiene {max_jugadoras} jugadoras disponibles.\n¡Necesitáis mínimo 6!")
        
    return mejor_turno, disponibilidad_turnos[mejor_turno]

def obtener_alineacion_ideal(id_liga, ids_disponibles):
    """Devuelve a las disponibles del turno ganador ordenadas por justicia."""
    estadisticas_completas = db.obtener_estadisticas_jugadoras(id_liga)
    disponibles = [j for j in estadisticas_completas if j['id'] in ids_disponibles]
    disponibles.sort(key=logica_desempate)
    return disponibles