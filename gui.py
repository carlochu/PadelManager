import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
from PIL import Image
import database as db
import algoritmo as alg

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PadelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pádel Manager - Auto Alineación y Actas")
        self.geometry("1100x800")

        # ➔ AÑADIR ICONO DE LA APLICACIÓN
        try:
            # Asegúrate de tener una imagen llamada 'padel_icon.png' en la misma carpeta
            self.iconbitmap() # Limpia por si acaso
            self.iconphoto(False, ctk.CTkImage(light_image=Image.open("padel_icon.png"), dark_image=Image.open("padel_icon.png"), size=(32, 32)))
        except Exception as e:
            pass # Si no encuentra el archivo o falta Pillow, arranca sin petares
        
        try:
            self.state('zoomed')
        except Exception:
            try:
                self.attributes('-zoomed', True)
            except Exception:
                pass

        self.tabview = ctk.CTkTabview(self) 
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_alineacion = self.tabview.add("Generar Alineación")
        self.tab_jugadoras = self.tabview.add("Gestión Jugadoras")
        self.tab_historial = self.tabview.add("Actas y Jornadas")

        self.liga_seleccionada = ctk.StringVar(value="Bullpadel")
        self.turnos = ["Sábado Mañana", "Sábado Tarde", "Domingo Mañana", "Domingo Tarde"]
        self.vars_disponibilidad = {}
        
        self.parejas_actuales = []
        self.suplentes_actuales = []
        self.sustituciones_actuales = {}

        self.construir_pestaña_alineacion()
        self.construir_pestaña_jugadoras()
        self.construir_pestaña_historial()

    # ==========================================
    # PESTAÑA 1: ALINEACIÓN Y MATRIZ DE TURNOS
    # ==========================================
    def construir_pestaña_alineacion(self):
        self.frame_izq = ctk.CTkFrame(self.tab_alineacion)
        self.frame_izq.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        frame_controles = ctk.CTkFrame(self.frame_izq, fg_color="transparent")
        frame_controles.pack(pady=10)
        
        ctk.CTkLabel(frame_controles, text="1. Liga:", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=5, pady=5)
        self.opciones_liga = ctk.CTkOptionMenu(frame_controles, values=["Bullpadel", "Interclubes"], variable=self.liga_seleccionada, width=120)
        self.opciones_liga.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_controles, text="2. Fecha:", font=("Arial", 14, "bold")).grid(row=1, column=0, padx=5, pady=5)
        self.entrada_fecha_actual = DateEntry(frame_controles, width=12, background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
        self.entrada_fecha_actual.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(self.frame_izq, text="3. Matriz de Disponibilidad:", font=("Arial", 16, "bold")).pack(pady=(15, 5))

        self.frame_lista = ctk.CTkScrollableFrame(self.frame_izq) 
        self.frame_lista.pack(pady=5, fill="both", expand=True)
        self.cargar_lista_disponibilidad()

        ctk.CTkButton(self.frame_izq, text="Calcular Turno y Alineación", font=("Arial", 14, "bold"), command=self.evento_generar_alineacion).pack(pady=20)

        # --- COLUMNA DERECHA ---
        self.frame_der = ctk.CTkFrame(self.tab_alineacion)
        self.frame_der.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.titulo_resultados = ctk.CTkLabel(self.frame_der, text="Propuesta Automática", font=("Arial", 18, "bold"), text_color="gray")
        self.titulo_resultados.pack(pady=15)
        
        self.frame_resultados_lista = ctk.CTkScrollableFrame(self.frame_der)
        self.frame_resultados_lista.pack(pady=10, fill="both", expand=True)
        
        self.btn_aprobar = ctk.CTkButton(self.frame_der, text="Aprobar y Crear Acta del Encuentro", fg_color="green", hover_color="darkgreen", font=("Arial", 14, "bold"), command=self.evento_aprobar_alineacion)
        
        self.label_feedback = ctk.CTkLabel(self.frame_der, text="")
        self.label_feedback.pack(pady=5)

    def cargar_lista_disponibilidad(self):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()
        self.vars_disponibilidad.clear()

        jugadoras = db.obtener_jugadoras()
        if not jugadoras:
            ctk.CTkLabel(self.frame_lista, text="Añade jugadoras en 'Gestión Jugadoras'.").pack(pady=10)
            return

        # Cabecera amplia con nombres de turno completos
        frame_header = ctk.CTkFrame(self.frame_lista, fg_color="transparent")
        frame_header.pack(fill="x", pady=4)
        ctk.CTkLabel(frame_header, text="Jugadora (Posición)", width=240, anchor="w", font=("Arial", 13, "bold")).pack(side="left", padx=10)
        
        for t in ["Sáb. Mañana", "Sáb. Tarde", "Dom. Mañana", "Dom. Tarde"]:
            ctk.CTkLabel(frame_header, text=t, width=95, font=("Arial", 12, "bold")).pack(side="left", padx=4)

        # Filas con el nombre entero y su posición entre paréntesis
        for j in jugadoras:
            frame_fila = ctk.CTkFrame(self.frame_lista)
            frame_fila.pack(fill="x", pady=3, padx=4)
            
            texto_jugadora = f"{j['nombre']}  ({j['posicion']})"
            ctk.CTkLabel(frame_fila, text=texto_jugadora, width=240, anchor="w", font=("Arial", 13)).pack(side="left", padx=10, pady=4)
            
            self.vars_disponibilidad[j['id']] = {}
            for turno in self.turnos:
                var = ctk.IntVar()
                # Contenedor del mismo ancho que el título (95px) para que el checkbox quede centrado bajo su columna
                f_chk = ctk.CTkFrame(frame_fila, width=95, height=28, fg_color="transparent")
                f_chk.pack_propagate(False)
                f_chk.pack(side="left", padx=4)
                
                chk = ctk.CTkCheckBox(f_chk, text="", variable=var, width=24, checkbox_width=22, checkbox_height=22)
                chk.place(relx=0.5, rely=0.5, anchor="center")
                
                self.vars_disponibilidad[j['id']][turno] = var

    def crear_fila_jugadora(self, parent_frame, j, estado_sugerido, lado=""):
        frame_fila = ctk.CTkFrame(parent_frame, fg_color="transparent")
        frame_fila.pack(fill="x", pady=2)
        
        prefijo = f"[{lado}] " if lado else ""
        es_bullpadel = (getattr(self, "liga_actual", "Bullpadel") == "Bullpadel")
        pts = j.get('puntos', 0)
        partidos = j.get('partidos_jugados', 0)
        descartes = j.get('veces_descartada', 0)
        
        info_pos_pts = f"{j['posicion']} | {pts}pts" if es_bullpadel else f"{j['posicion']}"
        texto_linea1 = f"{prefijo}{j['nombre']} ({info_pos_pts})"
        texto_linea2 = f"Partidos: {partidos} | Descartes: {descartes}"
        
        frame_textos = ctk.CTkFrame(frame_fila, fg_color="transparent")
        frame_textos.pack(side="left", padx=5)
        
        ctk.CTkLabel(frame_textos, text=texto_linea1, font=("Arial", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame_textos, text=texto_linea2, font=("Arial", 10, "italic"), text_color="lightgray").pack(anchor="w")
        
        color_badge = "#28a745" if estado_sugerido == "Convocada" else "#dc3545"
        lbl_badge = ctk.CTkLabel(frame_fila, text=estado_sugerido, fg_color=color_badge, text_color="white", corner_radius=6, width=95, height=24, font=("Arial", 11, "bold"))
        lbl_badge.pack(side="right", padx=8)

    def evento_generar_alineacion(self):
        liga = self.liga_seleccionada.get()
        id_liga = 1 if liga == "Bullpadel" else 2 
        
        disponibilidad_turnos = {turno: [] for turno in self.turnos}
        for id_j, vars_turnos in self.vars_disponibilidad.items():
            for turno in self.turnos:
                if vars_turnos[turno].get() == 1:
                    disponibilidad_turnos[turno].append(id_j)
                            
        try:
            turno_ganador, ids_disponibles = alg.calcular_turno_ganador(disponibilidad_turnos)
            resultado = alg.obtener_alineacion_ideal(id_liga, ids_disponibles)
            
            self.parejas_actuales = resultado["parejas"]
            self.suplentes_actuales = resultado["suplentes"]
            self.sustituciones_actuales = resultado["sustituciones"]
            self.turno_ganador_texto = turno_ganador
            self.liga_actual = liga
            
            self.pintar_resultados()
            
        except Exception as e:
            self.label_feedback.configure(text=str(e), text_color="red")

    def pintar_resultados(self):
        for widget in self.frame_resultados_lista.winfo_children():
            widget.destroy()
            
        es_bullpadel = (self.liga_actual == "Bullpadel")
        self.titulo_resultados.configure(text=f"Propuesta {self.liga_actual}\n¡{self.turno_ganador_texto}!", text_color="#28a745")
        
        for i, pareja in enumerate(self.parejas_actuales):
            f_pareja = ctk.CTkFrame(self.frame_resultados_lista, fg_color="#1f538d", corner_radius=10)
            f_pareja.pack(fill="x", pady=5, padx=5)
            
            titulo = f"Pareja {i+1} (Suma: {pareja['puntos_suma']} pts)" if es_bullpadel else f"Pareja {i+1}"
            ctk.CTkLabel(f_pareja, text=titulo, font=("Arial", 12, "bold"), text_color="white").pack(pady=4)
            
            self.crear_fila_jugadora(f_pareja, pareja['drive'], "Convocada", "Drive")
            self.crear_fila_jugadora(f_pareja, pareja['reves'], "Convocada", "Revés")
        
        if self.suplentes_actuales:
            titulo_banquillo = "Banquillo Inteligente (Rotación)" if es_bullpadel else "Banquillo (Cambios por Posición)"
            ctk.CTkLabel(self.frame_resultados_lista, text=titulo_banquillo, font=("Arial", 12, "bold"), text_color="orange").pack(pady=(15, 2))
            
            for suplente in self.suplentes_actuales:
                f_suplente = ctk.CTkFrame(self.frame_resultados_lista, fg_color="transparent")
                f_suplente.pack(fill="x", pady=2, padx=5)
                
                self.crear_fila_jugadora(f_suplente, suplente, "Descartada")
                
                ops = self.sustituciones_actuales.get(suplente['id'], [])
                if ops:
                    etiqueta_menu = "- Elegir Sustitución Legal -" if es_bullpadel else "- Cambiar por Posición -"
                    textos_ops = [etiqueta_menu] + [op["texto"] for op in ops]
                    var_swap = ctk.StringVar(value=etiqueta_menu)
                    
                    def realizar_cambio(seleccion, s=suplente, opciones=ops, etq=etiqueta_menu):
                        if seleccion == etq: return
                        op_elegida = next((op for op in opciones if op["texto"] == seleccion), None)
                        if op_elegida:
                            self.ejecutar_sustitucion(s, op_elegida["sale"], op_elegida["lado"], op_elegida["idx"])
                            
                    menu_swap = ctk.CTkOptionMenu(f_suplente, values=textos_ops, variable=var_swap, width=260, fg_color="#d35400", button_color="#ba4a00")
                    menu_swap.configure(command=realizar_cambio)
                    menu_swap.pack(pady=5, padx=25, anchor="w")
                else:
                    msg_error = "No encaja legalmente en ninguna pareja." if es_bullpadel else "Incompatible por posición (Drive/Revés)."
                    ctk.CTkLabel(f_suplente, text=msg_error, font=("Arial", 10, "italic"), text_color="red").pack(anchor="w", padx=25)
                    
        self.btn_aprobar.pack(pady=15)
        self.label_feedback.configure(text="Usa el botón naranja para intercambiar suplentes antes de aprobar.", text_color="lightgray")

    def ejecutar_sustitucion(self, entra_jugadora, sale_jugadora, lado, idx_pareja):
        es_bullpadel = (self.liga_actual == "Bullpadel")
        self.suplentes_actuales = [s for s in self.suplentes_actuales if s['id'] != entra_jugadora['id']]
        self.suplentes_actuales.append(sale_jugadora)
        self.parejas_actuales[idx_pareja][lado] = entra_jugadora
        
        d = self.parejas_actuales[idx_pareja]["drive"]
        r = self.parejas_actuales[idx_pareja]["reves"]
        self.parejas_actuales[idx_pareja]["puntos_suma"] = d.get('puntos', 0) + r.get('puntos', 0)
        
        if es_bullpadel:
            self.parejas_actuales.sort(key=lambda x: x["puntos_suma"], reverse=True)
        
        self.sustituciones_actuales = alg.calcular_sustituciones(self.parejas_actuales, self.suplentes_actuales, validar_puntos=es_bullpadel)
        self.pintar_resultados()

    def evento_aprobar_alineacion(self):
        fecha = self.entrada_fecha_actual.get()
        liga = getattr(self, "liga_actual", self.liga_seleccionada.get())
        id_liga = 1 if liga == "Bullpadel" else 2
        
        if len(self.parejas_actuales) != 3:
            self.label_feedback.configure(text="Error: No hay 3 parejas formadas.", text_color="red")
            return
            
        if db.existe_jornada(fecha, id_liga):
            respuesta = messagebox.askyesno("Jornada Existente", f"Ya existe un encuentro el {fecha} para {liga}.\n¿Deseas sobrescribir la alineación y el acta?")
            if not respuesta:
                return 
            db.eliminar_jornada(fecha, id_liga) 
            
        exito = db.guardar_alineacion_completa(fecha, id_liga, self.parejas_actuales, self.suplentes_actuales)
        if exito and db.existe_jornada(fecha, id_liga):
            self.label_feedback.configure(text="¡Alineación y Acta pre-creadas y verificadas en base de datos!", text_color="green")
            self.btn_aprobar.pack_forget()
            self.cargar_lista_jornadas()
            messagebox.showinfo("Guardado Verificado", f"La alineación de {liga} para el {fecha} se ha guardado correctamente.\n\nPuedes anotar el rival y los sets cuando juguéis en la pestaña 'Actas y Jornadas'.")
        else:
            self.label_feedback.configure(text="Error crítico al guardar en la base de datos.", text_color="red")

    # ==========================================
    # PESTAÑA 2: GESTIÓN DE JUGADORAS (CRUD)
    # ==========================================
    def construir_pestaña_jugadoras(self):
        frame_nuevo = ctk.CTkFrame(self.tab_jugadoras, fg_color="transparent")
        frame_nuevo.pack(pady=10, fill="x", padx=20)

        self.entrada_nombre = ctk.CTkEntry(frame_nuevo, placeholder_text="Nombre jugadora", width=220)
        self.entrada_nombre.pack(side="left", padx=5)

        self.opcion_posicion = ctk.CTkOptionMenu(frame_nuevo, values=["DERECHA", "REVES", "DERECHA/REVES", "REVES/DERECHA"], width=160)
        self.opcion_posicion.pack(side="left", padx=5)

        ctk.CTkButton(frame_nuevo, text="+ Añadir Jugadora", command=self.evento_guardar_jugadora).pack(side="left", padx=10)

        self.label_estado_jugadoras = ctk.CTkLabel(self.tab_jugadoras, text="")
        self.label_estado_jugadoras.pack(pady=5)

        self.frame_lista_gestion = ctk.CTkScrollableFrame(self.tab_jugadoras)
        self.frame_lista_gestion.pack(pady=5, fill="both", expand=True)

        self.cargar_lista_gestion_jugadoras()

    def evento_guardar_jugadora(self):
        nombre = self.entrada_nombre.get().strip()
        posicion = self.opcion_posicion.get()
        
        if not nombre:
            self.label_estado_jugadoras.configure(text="Error: El nombre no puede estar vacío.", text_color="red")
            return
            
        exito = db.agregar_jugadora(nombre, posicion)
        if exito:
            self.label_estado_jugadoras.configure(text=f"¡{nombre} añadida correctamente!", text_color="green")
            self.entrada_nombre.delete(0, 'end')
            self.cargar_lista_gestion_jugadoras()
            self.cargar_lista_disponibilidad()
        else:
            self.label_estado_jugadoras.configure(text=f"Error: Ya existe una jugadora llamada '{nombre}'.", text_color="red")

    def cargar_lista_gestion_jugadoras(self):
        for widget in self.frame_lista_gestion.winfo_children():
            widget.destroy()
            
        jugadoras = db.obtener_jugadoras()
        for j in jugadoras:
            frame_fila = ctk.CTkFrame(self.frame_lista_gestion)
            frame_fila.pack(fill="x", pady=2, padx=5)
            
            lbl_nombre = ctk.CTkLabel(frame_fila, text=f"{j['nombre']} ({j['posicion']})  |  Ranking Bullpadel: {j['puntos']} pts", width=450, anchor="w", font=("Arial", 14))
            lbl_nombre.pack(side="left", padx=15, pady=5)
            
            ctk.CTkButton(frame_fila, text="Borrar", fg_color="red", hover_color="darkred", width=70, command=lambda id_j=j['id'], nom=j['nombre']: self.evento_borrar_jugadora(id_j, nom)).pack(side="right", padx=5)
            ctk.CTkButton(frame_fila, text="Editar", width=80, command=lambda id_j=j['id'], nom=j['nombre'], pos=j['posicion']: self.abrir_edicion_jugadora(id_j, nom, pos)).pack(side="right", padx=5)

    def evento_borrar_jugadora(self, id_jugadora, nombre):
        respuesta = messagebox.askyesno("Confirmar Borrado", f"¿Seguro que quieres borrar a {nombre}?\nPerderá todo su historial.")
        if respuesta:
            db.eliminar_jugadora(id_jugadora)
            self.cargar_lista_gestion_jugadoras()
            self.cargar_lista_disponibilidad()
            self.label_estado_jugadoras.configure(text=f"Jugadora {nombre} eliminada.", text_color="orange")

    def abrir_edicion_jugadora(self, id_jugadora, nombre_actual, posicion_actual):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Editando a {nombre_actual}")
        ventana.geometry("300x250")
        ventana.attributes("-topmost", True)
        
        ctk.CTkLabel(ventana, text="Modificar Datos", font=("Arial", 16, "bold")).pack(pady=10)
        
        ctk.CTkLabel(ventana, text="Nombre:").pack()
        entrada_nom = ctk.CTkEntry(ventana, width=200)
        entrada_nom.insert(0, nombre_actual)
        entrada_nom.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Posición:").pack()
        var_pos = ctk.StringVar(value=posicion_actual)
        menu_pos = ctk.CTkOptionMenu(ventana, values=["DERECHA", "REVES", "DERECHA/REVES", "REVES/DERECHA"], variable=var_pos, width=200)
        menu_pos.pack(pady=5)
        
        lbl_feedback = ctk.CTkLabel(ventana, text="")
        lbl_feedback.pack()
        
        def guardar_cambios():
            nuevo_nom = entrada_nom.get().strip()
            nueva_pos = var_pos.get()
            if not nuevo_nom: return
                
            exito = db.modificar_jugadora(id_jugadora, nuevo_nom, nueva_pos)
            if exito:
                self.cargar_lista_gestion_jugadoras()
                self.cargar_lista_disponibilidad()
                self.label_estado_jugadoras.configure(text=f"¡Datos de {nuevo_nom} actualizados!", text_color="green")
                ventana.destroy()
            else:
                lbl_feedback.configure(text="Error al guardar.", text_color="red")
                
        ctk.CTkButton(ventana, text="Guardar Cambios", command=guardar_cambios).pack(pady=10)

    # ==========================================
    # PESTAÑA 3: ACTAS Y JORNADAS PASADAS
    # ==========================================
    def construir_pestaña_historial(self):
        ctk.CTkButton(
            self.tab_historial,
            text="+ Registrar Nueva Acta / Jornada Manual",
            font=("Arial", 14, "bold"),
            command=lambda: self.abrir_ventana_acta("", 1, nueva=True)
        ).pack(pady=15)
        
        self.frame_lista_jornadas = ctk.CTkScrollableFrame(self.tab_historial)
        self.frame_lista_jornadas.pack(pady=5, fill="both", expand=True)
        
        self.cargar_lista_jornadas()

    def cargar_lista_jornadas(self):
        for widget in self.frame_lista_jornadas.winfo_children():
            widget.destroy()
            
        jornadas = db.obtener_jornadas_guardadas()
        if not jornadas:
            ctk.CTkLabel(self.frame_lista_jornadas, text="No hay encuentros registrados todavía.").pack(pady=20)
            return
            
        for j in jornadas:
            frame_fila = ctk.CTkFrame(self.frame_lista_jornadas)
            frame_fila.pack(fill="x", pady=4, padx=8)
            
            if j['ganado'] == 1:
                est_txt = "VICTORIA"
                est_col = "#28a745"
            elif j['ganado'] == 0:
                est_txt = "DERROTA"
                est_col = "#dc3545"
            else:
                est_txt = "PENDIENTE DE RESULTADO"
                est_col = "gray"
                
            texto = f"📅 {j['fecha']}  |  🏆 {j['nombre_liga']}  |  🆚 Rival: {j['rival']}"
            ctk.CTkLabel(frame_fila, text=texto, font=("Arial", 14, "bold")).pack(side="left", padx=15, pady=10)
            
            ctk.CTkLabel(frame_fila, text=est_txt, fg_color=est_col, text_color="white", corner_radius=6, width=170, height=26, font=("Arial", 11, "bold")).pack(side="left", padx=10)
            
            ctk.CTkButton(frame_fila, text="Borrar", fg_color="red", hover_color="darkred", width=75, command=lambda f=j['fecha'], l=j['id_liga']: self.evento_eliminar_jornada(f, l)).pack(side="right", padx=5)
            ctk.CTkButton(frame_fila, text="Ver / Editar Acta", width=130, command=lambda f=j['fecha'], l=j['id_liga']: self.abrir_ventana_acta(f, l, nueva=False)).pack(side="right", padx=5)

    def evento_eliminar_jornada(self, fecha, id_liga):
        respuesta = messagebox.askyesno("Confirmar", f"¿Borrar todos los datos y el acta de la jornada del {fecha}?")
        if respuesta:
            db.eliminar_jornada(fecha, id_liga)
            self.cargar_lista_jornadas()
            self.cargar_lista_gestion_jugadoras()

    def evaluar_ganador_partido(self, s1_n, s1_r, s2_n, s2_r, s3_n, s3_r):
        """Evalúa los sets jugados. Devuelve (1: Ganado, 0: Perdido, -1: Incompleto, sets_nos, sets_riv)."""
        sets_nos = 0
        sets_riv = 0
        for sn, sr in [(s1_n, s1_r), (s2_n, s2_r), (s3_n, s3_r)]:
            if sn is not None and sr is not None:
                if sn > sr: sets_nos += 1
                elif sr > sn: sets_riv += 1
        if sets_nos >= 2:
            return 1, sets_nos, sets_riv
        elif sets_riv >= 2:
            return 0, sets_nos, sets_riv
        return -1, sets_nos, sets_riv

    def abrir_ventana_acta(self, fecha, id_liga, nueva=False):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Acta del Encuentro y Marcadores" if not nueva else "Registrar Nueva Acta")
        ventana.geometry("950x820")
        ventana.attributes("-topmost", True)
        
        # Validación estricta para que las casillas de sets solo admitan 1 dígito numérico (0-9)
        def validar_un_digito(texto):
            return texto == "" or (len(texto) == 1 and texto.isdigit())
        vcmd = (ventana.register(validar_un_digito), '%P')
        
        # --- CABECERA DEL ENCUENTRO ---
        frame_top = ctk.CTkFrame(ventana)
        frame_top.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(frame_top, text="Fecha:", font=("Arial", 13, "bold")).pack(side="left", padx=(10, 5), pady=10)
        entrada_fecha = DateEntry(frame_top, width=12, background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
        entrada_fecha.pack(side="left", padx=5)
        
        ctk.CTkLabel(frame_top, text="Liga:", font=("Arial", 13, "bold")).pack(side="left", padx=(15, 5))
        var_liga = ctk.StringVar(value="Bullpadel" if id_liga == 1 else "Interclubes")
        menu_liga = ctk.CTkOptionMenu(frame_top, values=["Bullpadel", "Interclubes"], variable=var_liga, width=120)
        menu_liga.pack(side="left", padx=5)
        
        ctk.CTkLabel(frame_top, text="Equipo Rival:", font=("Arial", 13, "bold")).pack(side="left", padx=(15, 5))
        entrada_rival = ctk.CTkEntry(frame_top, placeholder_text="Ej: Club Pádel Turia", width=220)
        entrada_rival.pack(side="left", padx=5)
        
        lbl_veredicto_global = ctk.CTkLabel(frame_top, text="ENCUENTRO PENDIENTE", fg_color="gray", text_color="white", corner_radius=8, width=210, height=32, font=("Arial", 13, "bold"))
        lbl_veredicto_global.pack(side="right", padx=15)
        
        datos_acta = db.obtener_acta_encuentro(fecha, id_liga) if not nueva else None
        if not nueva and datos_acta:
            entrada_fecha.set_date(fecha)
            entrada_fecha.configure(state="disabled")
            menu_liga.configure(state="disabled")
            entrada_rival.insert(0, datos_acta["rival"])
            
        jugadoras_db = db.obtener_jugadoras()
        mapa_id_a_texto = {j['id']: f"{j['nombre']} ({j['puntos']} pts)" for j in jugadoras_db}
        mapa_texto_a_id = {f"{j['nombre']} ({j['puntos']} pts)": j['id'] for j in jugadoras_db}
        mapa_id_a_pts = {j['id']: j['puntos'] for j in jugadoras_db}
        opciones_jugadoras = ["- Seleccionar -"] + list(mapa_texto_a_id.keys())
        
        # --- CONTENEDOR DE LAS 3 PAREJAS Y MINITABLAS DE SETS ---
        frame_cuerpo = ctk.CTkScrollableFrame(ventana)
        frame_cuerpo.pack(fill="both", expand=True, padx=15, pady=5)
        
        controles_partidos = []
        
        for idx in range(3):
            num_p = idx + 1
            datos_p = datos_acta["partidos"][idx] if (datos_acta and len(datos_acta["partidos"]) > idx) else {
                "num_pareja": num_p, "id_drive": None, "id_reves": None, "rivales_pareja": "",
                "s1_nos": None, "s1_riv": None, "s2_nos": None, "s2_riv": None, "s3_nos": None, "s3_riv": None
            }
            
            f_card = ctk.CTkFrame(frame_cuerpo, border_width=2, border_color="#1f538d", corner_radius=10)
            f_card.pack(fill="x", pady=8, padx=5)
            
            # Cabecera de la Pareja
            f_head = ctk.CTkFrame(f_card, fg_color="#1f538d", corner_radius=8)
            f_head.pack(fill="x", padx=2, pady=2)
            
            lbl_titulo_p = ctk.CTkLabel(f_head, text=f"PAREJA {num_p}", font=("Arial", 14, "bold"), text_color="white")
            lbl_titulo_p.pack(side="left", padx=15, pady=6)
            
            lbl_estado_p = ctk.CTkLabel(f_head, text="Pendiente", fg_color="gray", text_color="white", corner_radius=6, width=140, font=("Arial", 12, "bold"))
            lbl_estado_p.pack(side="right", padx=15, pady=6)
            
            # Contenido: Izquierda (Selección Jugadoras y Rivales) | Derecha (Minitabla Set 1, Set 2, Set 3)
            f_content = ctk.CTkFrame(f_card, fg_color="transparent")
            f_content.pack(fill="x", padx=10, pady=8)
            
            f_izq_p = ctk.CTkFrame(f_content, fg_color="transparent")
            f_izq_p.pack(side="left", fill="both", expand=True, padx=5)
            
            ctk.CTkLabel(f_izq_p, text="Jugadora Drive:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=3, padx=5)
            var_d = ctk.StringVar(value=mapa_id_a_texto.get(datos_p["id_drive"], "- Seleccionar -"))
            menu_d = ctk.CTkOptionMenu(f_izq_p, values=opciones_jugadoras, variable=var_d, width=210)
            menu_d.grid(row=0, column=1, pady=3, padx=5)
            
            ctk.CTkLabel(f_izq_p, text="Jugadora Revés:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=3, padx=5)
            var_r = ctk.StringVar(value=mapa_id_a_texto.get(datos_p["id_reves"], "- Seleccionar -"))
            menu_r = ctk.CTkOptionMenu(f_izq_p, values=opciones_jugadoras, variable=var_r, width=210)
            menu_r.grid(row=1, column=1, pady=3, padx=5)
            
            ctk.CTkLabel(f_izq_p, text="Rivales (opcional):", font=("Arial", 12)).grid(row=2, column=0, sticky="w", pady=3, padx=5)
            ent_riv_p = ctk.CTkEntry(f_izq_p, placeholder_text="Nombres pareja rival", width=210)
            ent_riv_p.grid(row=2, column=1, pady=3, padx=5)
            if datos_p.get("rivales_pareja"):
                ent_riv_p.insert(0, datos_p["rivales_pareja"])
                
            # --- MINITABLA DE SETS (UN SOLO DÍGITO) ---
            f_tabla = ctk.CTkFrame(f_content)
            f_tabla.pack(side="right", padx=15, pady=2)
            
            ctk.CTkLabel(f_tabla, text="", width=110).grid(row=0, column=0, padx=5, pady=2)
            ctk.CTkLabel(f_tabla, text="Set 1", font=("Arial", 12, "bold"), width=50).grid(row=0, column=1, padx=4, pady=2)
            ctk.CTkLabel(f_tabla, text="Set 2", font=("Arial", 12, "bold"), width=50).grid(row=0, column=2, padx=4, pady=2)
            ctk.CTkLabel(f_tabla, text="Set 3", font=("Arial", 12, "bold"), width=50).grid(row=0, column=3, padx=4, pady=2)
            
            ctk.CTkLabel(f_tabla, text="Nuestras Jugadoras", font=("Arial", 12, "bold"), anchor="w").grid(row=1, column=0, padx=8, pady=4, sticky="w")
            ctk.CTkLabel(f_tabla, text="Rivales", font=("Arial", 12, "bold"), anchor="w", text_color="orange").grid(row=2, column=0, padx=8, pady=4, sticky="w")
            
            vars_sets = {}
            for s_idx, clave_s in enumerate(["s1", "s2", "s3"], start=1):
                v_nos = ctk.StringVar(value="" if datos_p[f"{clave_s}_nos"] is None else str(datos_p[f"{clave_s}_nos"]))
                v_riv = ctk.StringVar(value="" if datos_p[f"{clave_s}_riv"] is None else str(datos_p[f"{clave_s}_riv"]))
                
                e_nos = ctk.CTkEntry(f_tabla, textvariable=v_nos, width=42, height=32, justify="center", font=("Arial", 15, "bold"), validate="key", validatecommand=vcmd)
                e_nos.grid(row=1, column=s_idx, padx=4, pady=3)
                
                e_riv = ctk.CTkEntry(f_tabla, textvariable=v_riv, width=42, height=32, justify="center", font=("Arial", 15, "bold"), validate="key", validatecommand=vcmd)
                e_riv.grid(row=2, column=s_idx, padx=4, pady=3)
                
                vars_sets[f"{clave_s}_nos"] = v_nos
                vars_sets[f"{clave_s}_riv"] = v_riv
                
            controles_partidos.append({
                "num_pareja": num_p,
                "var_d": var_d,
                "var_r": var_r,
                "ent_riv_p": ent_riv_p,
                "vars_sets": vars_sets,
                "lbl_titulo_p": lbl_titulo_p,
                "lbl_estado_p": lbl_estado_p
            })

        # --- FUNCIÓN DE RECÁLCULO AUTOMÁTICO DE PUNTOS Y VICTORIAS EN TIEMPO REAL ---
        # --- FUNCIÓN DE RECÁLCULO AUTOMÁTICO CON REGLAMENTO OFICIAL BULLPADEL ---
        # --- FUNCIÓN DE RECÁLCULO AUTOMÁTICO (5ª DIVISIÓN BULLPADEL vs INTERCLUBES) ---
        def recalcular_marcadores(*args):
            partidos_ganados = 0
            partidos_perdidos = 0
            pts_equipo_nos = 0
            pts_equipo_riv = 0
            valores_pareja_bp = {1: 8, 2: 5, 3: 4}
            factor_5a_div = 0.80 # 5ª División = 80% de los puntos base
            es_bull = (var_liga.get() == "Bullpadel")
            
            for cp in controles_partidos:
                num_p = cp['num_pareja']
                id_d = mapa_texto_a_id.get(cp["var_d"].get())
                id_r = mapa_texto_a_id.get(cp["var_r"].get())
                suma_pts = round((mapa_id_a_pts.get(id_d, 0.0) if id_d else 0.0) + (mapa_id_a_pts.get(id_r, 0.0) if id_r else 0.0), 1)
                
                if es_bull:
                    val_eq = valores_pareja_bp[num_p]
                    cp["lbl_titulo_p"].configure(text=f"PAREJA {num_p} [Vale {val_eq} pts equipo]  |  Ranking Pareja: {suma_pts} pts")
                else:
                    cp["lbl_titulo_p"].configure(text=f"PAREJA {num_p} (Modo Interclubes - Sin puntos ranking)")
                    
                def leer_digito(v):
                    txt = v.get().strip()
                    return int(txt) if txt.isdigit() else None
                    
                vs = cp["vars_sets"]
                s1n, s1r = leer_digito(vs["s1_nos"]), leer_digito(vs["s1_riv"])
                s2n, s2r = leer_digito(vs["s2_nos"]), leer_digito(vs["s2_riv"])
                s3n, s3r = leer_digito(vs["s3_nos"]), leer_digito(vs["s3_riv"])
                
                ganado_p, sets_n, sets_r = self.evaluar_ganador_partido(s1n, s1r, s2n, s2r, s3n, s3r)
                cp["ganado_calculado"] = ganado_p
                sets_totales = sets_n + sets_r
                
                if ganado_p == 1:
                    partidos_ganados += 1
                    pts_equipo_nos += valores_pareja_bp[num_p]
                    if es_bull:
                        pts_base_p = {1: (1000 if sets_totales == 2 else 900), 2: (800 if sets_totales == 2 else 700), 3: (600 if sets_totales == 2 else 500)}[num_p]
                        pts_indiv = int(pts_base_p * factor_5a_div)
                        cp["lbl_estado_p"].configure(text=f"GANADO {sets_n}-{sets_r} (+{pts_indiv} pts)", fg_color="#28a745", width=175)
                    else:
                        cp["lbl_estado_p"].configure(text=f"GANADO ({sets_n}-{sets_r})", fg_color="#28a745", width=140)
                elif ganado_p == 0:
                    partidos_perdidos += 1
                    pts_equipo_riv += valores_pareja_bp[num_p]
                    cp["lbl_estado_p"].configure(text=f"PERDIDO ({sets_n}-{sets_r})", fg_color="#dc3545", width=140)
                else:
                    cp["lbl_estado_p"].configure(text=f"Pendiente ({sets_n}-{sets_r})", fg_color="gray", width=140)
                    
            if partidos_ganados >= 2:
                bonus_5a = int(100 * factor_5a_div)
                extra_txt = f" | Pts PTL: {pts_equipo_nos}-{pts_equipo_riv} (+{bonus_5a} bonus)" if es_bull else ""
                lbl_veredicto_global.configure(text=f"🏆 GANADO {partidos_ganados}-{partidos_perdidos}{extra_txt}", fg_color="#28a745", width=290)
                ventana.ganado_global = 1
            elif partidos_perdidos >= 2:
                extra_txt = f" | Pts PTL: {pts_equipo_nos}-{pts_equipo_riv}" if es_bull else ""
                lbl_veredicto_global.configure(text=f"❌ PERDIDO {partidos_ganados}-{partidos_perdidos}{extra_txt}", fg_color="#dc3545", width=260)
                ventana.ganado_global = 0
            else:
                lbl_veredicto_global.configure(text=f"⏳ PENDIENTE ({partidos_ganados}-{partidos_perdidos})", fg_color="gray", width=210)
                ventana.ganado_global = -1

        # Conectar todos los selectores y casillas al recalculador en vivo
        var_liga.trace_add("write", recalcular_marcadores)
        for cp in controles_partidos:
            cp["var_d"].trace_add("write", recalcular_marcadores)
            cp["var_r"].trace_add("write", recalcular_marcadores)
            for v_set in cp["vars_sets"].values():
                v_set.trace_add("write", recalcular_marcadores)
                
        recalcular_marcadores()

        # --- BOTÓN DE GUARDADO VERIFICADO ---
        def guardar_acta():
            f_guardar = entrada_fecha.get()
            l_guardar = 1 if var_liga.get() == "Bullpadel" else 2
            rival_str = entrada_rival.get().strip()
            
            ids_seleccionados = []
            lista_partidos_db = []
            
            for cp in controles_partidos:
                id_d = mapa_texto_a_id.get(cp["var_d"].get())
                id_r = mapa_texto_a_id.get(cp["var_r"].get())
                if not id_d or not id_r:
                    messagebox.showerror("Faltan Jugadoras", f"Debes seleccionar las 2 jugadoras de la Pareja {cp['num_pareja']}.", parent=ventana)
                    return
                ids_seleccionados.extend([id_d, id_r])
                
                def a_int(v):
                    t = v.get().strip()
                    return int(t) if t.isdigit() else None
                    
                vs = cp["vars_sets"]
                lista_partidos_db.append({
                    "num_pareja": cp["num_pareja"],
                    "id_drive": id_d,
                    "id_reves": id_r,
                    "rivales_pareja": cp["ent_riv_p"].get().strip(),
                    "s1_nos": a_int(vs["s1_nos"]), "s1_riv": a_int(vs["s1_riv"]),
                    "s2_nos": a_int(vs["s2_nos"]), "s2_riv": a_int(vs["s2_riv"]),
                    "s3_nos": a_int(vs["s3_nos"]), "s3_riv": a_int(vs["s3_riv"]),
                    "ganado": cp.get("ganado_calculado", -1)
                })
                
            if len(set(ids_seleccionados)) != 6:
                messagebox.showerror("Jugadora Duplicada", "Una misma jugadora no puede estar repetida en dos posiciones o parejas distintas.", parent=ventana)
                return
                
            if nueva and db.existe_jornada(f_guardar, l_guardar):
                if not messagebox.askyesno("Conflicto", f"Ya existe un acta el {f_guardar} para esa liga.\n¿Sobrescribir?", parent=ventana):
                    return
                    
            descartadas_previas = datos_acta["descartadas"] if datos_acta else None
            exito = db.guardar_acta_encuentro(f_guardar, l_guardar, rival_str, getattr(ventana, "ganado_global", -1), lista_partidos_db, descartadas_previas)
            
            if exito and db.existe_jornada(f_guardar, l_guardar):
                messagebox.showinfo("Acta Guardada", "El acta del encuentro y los marcadores se han guardado y verificado correctamente.", parent=ventana)
                ventana.destroy()
                self.cargar_lista_jornadas()
            else:
                messagebox.showerror("Error", "No se pudo verificar el guardado en la base de datos.", parent=ventana)

        ctk.CTkButton(ventana, text="Guardar Acta y Resultados", fg_color="green", hover_color="darkgreen", font=("Arial", 15, "bold"), height=40, command=guardar_acta).pack(pady=12)

if __name__ == "__main__":
    db.inicializar_db() 
    app = PadelApp()
    app.mainloop()