import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
import database as db
import algoritmo as alg

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PadelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pádel Manager - Auto Alineación")
        self.geometry("850x650") # Ventana más grande para la matriz de turnos

        self.tabview = ctk.CTkTabview(self, width=800, height=600)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_alineacion = self.tabview.add("Generar Alineación")
        self.tab_jugadoras = self.tabview.add("Gestión Jugadoras")
        self.tab_historial = self.tabview.add("Jornadas Pasadas")

        self.liga_seleccionada = ctk.StringVar(value="Bullpadel")
        
        # --- NUEVA LÓGICA DE TURNOS ---
        self.turnos = ["Sábado Mañana", "Sábado Tarde", "Domingo Mañana", "Domingo Tarde"]
        self.vars_disponibilidad = {} # Guardará {id: {'Sábado Mañana': var, ...}}
        
        self.opciones_resultado = [] 

        self.construir_pestaña_alineacion()
        self.construir_pestaña_jugadoras()
        self.construir_pestaña_historial()

    def actualizar_color_menu(self, seleccion, menu_widget):
        if seleccion == "Convocada":
            menu_widget.configure(fg_color="#28a745", button_color="#218838")
        elif seleccion == "Descartada":
            menu_widget.configure(fg_color="#dc3545", button_color="#c82333")
        else:
            menu_widget.configure(fg_color="gray", button_color="darkgray")

    # ==========================================
    # PESTAÑA 1: ALINEACIÓN Y MATRIZ DE TURNOS
    # ==========================================
    def construir_pestaña_alineacion(self):
        self.frame_izq = ctk.CTkFrame(self.tab_alineacion, width=420)
        self.frame_izq.pack(side="left", fill="y", padx=10, pady=10)
        
        frame_controles = ctk.CTkFrame(self.frame_izq, fg_color="transparent")
        frame_controles.pack(pady=10)
        
        ctk.CTkLabel(frame_controles, text="1. Liga:", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=5, pady=5)
        self.opciones_liga = ctk.CTkOptionMenu(frame_controles, values=["Bullpadel", "Interclubes"], variable=self.liga_seleccionada, width=120)
        self.opciones_liga.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_controles, text="2. Fecha:", font=("Arial", 14, "bold")).grid(row=1, column=0, padx=5, pady=5)
        self.entrada_fecha_actual = DateEntry(frame_controles, width=12, background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
        self.entrada_fecha_actual.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(self.frame_izq, text="3. Matriz de Disponibilidad:", font=("Arial", 16, "bold")).pack(pady=(15, 5))

        self.frame_lista = ctk.CTkScrollableFrame(self.frame_izq, width=380, height=300)
        self.frame_lista.pack(pady=5)
        self.cargar_lista_disponibilidad()

        ctk.CTkButton(self.frame_izq, text="Calcular Turno y Alineación", font=("Arial", 14, "bold"), command=self.evento_generar_alineacion).pack(pady=20)

        # --- COLUMNA DERECHA ---
        self.frame_der = ctk.CTkFrame(self.tab_alineacion, width=350)
        self.frame_der.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.titulo_resultados = ctk.CTkLabel(self.frame_der, text="Propuesta Automática", font=("Arial", 18, "bold"), text_color="gray")
        self.titulo_resultados.pack(pady=15)
        
        self.frame_resultados_lista = ctk.CTkScrollableFrame(self.frame_der, width=330, height=350)
        self.frame_resultados_lista.pack(pady=10)
        
        self.btn_aprobar = ctk.CTkButton(self.frame_der, text="Aprobar Alineación del Turno", fg_color="green", hover_color="darkgreen", command=self.evento_aprobar_alineacion)
        
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

        # Cabecera de la matriz
        frame_header = ctk.CTkFrame(self.frame_lista, fg_color="transparent")
        frame_header.pack(fill="x", pady=2)
        ctk.CTkLabel(frame_header, text="Jugadora", width=110, anchor="w", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        for t in ["S.Mañ", "S.Tar", "D.Mañ", "D.Tar"]:
            ctk.CTkLabel(frame_header, text=t, width=45, font=("Arial", 11, "bold")).pack(side="left", padx=2)

        for j in jugadoras:
            frame_fila = ctk.CTkFrame(self.frame_lista)
            frame_fila.pack(fill="x", pady=2)
            
            nombre_corto = j['nombre'] if len(j['nombre']) <= 11 else j['nombre'][:9] + ".."
            ctk.CTkLabel(frame_fila, text=nombre_corto, width=110, anchor="w").pack(side="left", padx=5)
            
            self.vars_disponibilidad[j['id']] = {}
            for turno in self.turnos:
                var = ctk.IntVar()
                chk = ctk.CTkCheckBox(frame_fila, text="", variable=var, width=45, checkbox_width=20, checkbox_height=20)
                chk.pack(side="left", padx=2)
                self.vars_disponibilidad[j['id']][turno] = var

    def evento_generar_alineacion(self):
        liga = self.liga_seleccionada.get()
        id_liga = 1 if liga == "Bullpadel" else 2 
        
        # Agrupamos los IDs según la matriz
        disponibilidad_turnos = {turno: [] for turno in self.turnos}
        for id_j, vars_turnos in self.vars_disponibilidad.items():
            for turno in self.turnos:
                if vars_turnos[turno].get() == 1:
                    disponibilidad_turnos[turno].append(id_j)
                            
        try:
            # 1. El algoritmo encuentra el mejor turno
            turno_ganador, ids_disponibles = alg.calcular_turno_ganador(disponibilidad_turnos)
            self.ids_disponibles_actuales = ids_disponibles
            
            # 2. El algoritmo ordena la justicia de ESE turno
            alineacion = alg.obtener_alineacion_ideal(id_liga, ids_disponibles)
            
            for widget in self.frame_resultados_lista.winfo_children():
                widget.destroy()
            self.opciones_resultado.clear()
                
            self.titulo_resultados.configure(text=f"Propuesta {liga}\n¡{turno_ganador} ({len(ids_disponibles)} disp.)!", text_color="#28a745")
            
            for i, j in enumerate(alineacion):
                frame_fila = ctk.CTkFrame(self.frame_resultados_lista)
                frame_fila.pack(fill="x", pady=2, padx=5)
                
                texto = f"{i+1}. {j['nombre']} ({j['posicion']})\nPartidos: {j['partidos_jugados']} | Descartes: {j['veces_descartada']}"
                ctk.CTkLabel(frame_fila, text=texto, font=("Arial", 12), justify="left").pack(side="left", padx=5)
                
                estado_sugerido = "Convocada" if i < 6 else "Descartada"
                var_estado = ctk.StringVar(value=estado_sugerido)
                
                menu = ctk.CTkOptionMenu(frame_fila, values=["Convocada", "Descartada", "No disponible"], variable=var_estado, width=110)
                menu.configure(command=lambda choice, m=menu: self.actualizar_color_menu(choice, m))
                menu.pack(side="right", padx=5)
                
                self.actualizar_color_menu(estado_sugerido, menu)
                self.opciones_resultado.append({"id": j['id'], "var": var_estado})
            
            self.btn_aprobar.pack(pady=15)
            self.label_feedback.configure(text="Revisa y guarda.", text_color="white")
            
        except Exception as e:
            self.label_feedback.configure(text=str(e), text_color="red")

    def evento_aprobar_alineacion(self):
        fecha = self.entrada_fecha_actual.get()
        liga = self.liga_seleccionada.get()
        id_liga = 1 if liga == "Bullpadel" else 2
        
        convocadas = [item for item in self.opciones_resultado if item['var'].get() == "Convocada"]
        descartadas = [item for item in self.opciones_resultado if item['var'].get() == "Descartada"]
        
        if len(convocadas) != 6:
            self.label_feedback.configure(text=f"Error: Has marcado {len(convocadas)}. ¡Deben ser 6!", text_color="red")
            return
            
        if db.existe_jornada(fecha, id_liga):
            respuesta = messagebox.askyesno("Jornada Existente", f"Ya existe una jornada el {fecha} para {liga}.\n¿Sobrescribir?")
            if not respuesta:
                return 
            db.eliminar_jornada(fecha, id_liga) 
            
        for c in convocadas:
            db.registrar_convocatoria(c['id'], id_liga, fecha, "Convocada")
        for d in descartadas:
            db.registrar_convocatoria(d['id'], id_liga, fecha, "Descartada")
            
        self.label_feedback.configure(text="¡Jornada guardada correctamente!", text_color="green")
        self.btn_aprobar.pack_forget()
        self.cargar_lista_jornadas()

    # ==========================================
    # PESTAÑA 2: GESTIÓN DE JUGADORAS (CRUD)
    # ==========================================
    def construir_pestaña_jugadoras(self):
        frame_nuevo = ctk.CTkFrame(self.tab_jugadoras, fg_color="transparent")
        frame_nuevo.pack(pady=10, fill="x", padx=20)

        self.entrada_nombre = ctk.CTkEntry(frame_nuevo, placeholder_text="Nombre de la jugadora", width=200)
        self.entrada_nombre.pack(side="left", padx=5)

        # NOMENCLATURA DEL EXCEL APLICADA AQUÍ
        self.opcion_posicion = ctk.CTkOptionMenu(frame_nuevo, values=["DERECHA", "REVES", "REVES/DERECHA"], width=150)
        self.opcion_posicion.pack(side="left", padx=5)

        ctk.CTkButton(frame_nuevo, text="+ Añadir", command=self.evento_guardar_jugadora).pack(side="left", padx=10)

        self.label_estado_jugadoras = ctk.CTkLabel(self.tab_jugadoras, text="")
        self.label_estado_jugadoras.pack(pady=5)

        self.frame_lista_gestion = ctk.CTkScrollableFrame(self.tab_jugadoras, width=600, height=400)
        self.frame_lista_gestion.pack(pady=5)

        self.cargar_lista_gestion_jugadoras()

    def evento_guardar_jugadora(self):
        nombre = self.entrada_nombre.get().strip() # <--- AQUÍ LE HEMOS QUITADO EL .upper()
        posicion = self.opcion_posicion.get()
        
        if not nombre:
            self.label_estado_jugadoras.configure(text="Error: Escribe un nombre", text_color="red")
            return
            
        db.agregar_jugadora(nombre, posicion)
        self.label_estado_jugadoras.configure(text=f"¡{nombre} añadida!", text_color="green")
        self.entrada_nombre.delete(0, 'end') 
        self.cargar_lista_gestion_jugadoras()
        self.cargar_lista_disponibilidad()

    def cargar_lista_gestion_jugadoras(self):
        for widget in self.frame_lista_gestion.winfo_children():
            widget.destroy()
            
        jugadoras = db.obtener_jugadoras()
        for j in jugadoras:
            frame_fila = ctk.CTkFrame(self.frame_lista_gestion)
            frame_fila.pack(fill="x", pady=2, padx=5)
            
            lbl_nombre = ctk.CTkLabel(frame_fila, text=f"{j['nombre']} ({j['posicion']})", width=250, anchor="w", font=("Arial", 14))
            lbl_nombre.pack(side="left", padx=15, pady=5)
            
            ctk.CTkButton(frame_fila, text="Borrar", fg_color="red", hover_color="darkred", width=70, command=lambda id_j=j['id'], nom=j['nombre']: self.evento_borrar_jugadora(id_j, nom)).pack(side="right", padx=5)
            
            ctk.CTkButton(frame_fila, text="Editar", width=70, command=lambda id_j=j['id'], nom=j['nombre'], pos=j['posicion']: self.abrir_edicion_jugadora(id_j, nom, pos)).pack(side="right", padx=5)

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
        
        ctk.CTkLabel(ventana, text="Modificar Datos", font=("Arial", 16, "bold")).pack(pady=15)
        
        entrada_nom = ctk.CTkEntry(ventana, width=200)
        entrada_nom.insert(0, nombre_actual)
        entrada_nom.pack(pady=10)
        
        var_pos = ctk.StringVar(value=posicion_actual)
        # NOMENCLATURA EXCEL EN EDICIÓN
        menu_pos = ctk.CTkOptionMenu(ventana, values=["DERECHA", "REVES", "REVES/DERECHA"], variable=var_pos, width=200)
        menu_pos.pack(pady=10)
        
        def guardar_cambios():
            nuevo_nom = entrada_nom.get().strip()
            nueva_pos = var_pos.get()
            if nuevo_nom:
                db.modificar_jugadora(id_jugadora, nuevo_nom, nueva_pos)
                self.cargar_lista_gestion_jugadoras()
                self.cargar_lista_disponibilidad()
                self.label_estado_jugadoras.configure(text=f"¡Datos actualizados!", text_color="green")
                ventana.destroy()
                
        # --- LÍNEA QUE TE FALTA AÑADIR (Fíjate que esté a esta misma altura) ---
        ctk.CTkButton(ventana, text="Guardar Cambios", command=guardar_cambios).pack(pady=15)

    # ==========================================
    # PESTAÑA 3: HISTORIAL 
    # ==========================================
    def construir_pestaña_historial(self):
        ctk.CTkButton(self.tab_historial, text="+ Añadir Jornada Pasada Manualmente", command=lambda: self.abrir_ventana_edicion("", 1, nueva=True)).pack(pady=15)
        self.frame_lista_jornadas = ctk.CTkScrollableFrame(self.tab_historial, width=600, height=400)
        self.frame_lista_jornadas.pack(pady=5)
        self.cargar_lista_jornadas()

    def cargar_lista_jornadas(self):
        for widget in self.frame_lista_jornadas.winfo_children():
            widget.destroy()
            
        jornadas = db.obtener_jornadas_guardadas()
        if not jornadas:
            ctk.CTkLabel(self.frame_lista_jornadas, text="No hay jornadas registradas.").pack(pady=20)
            return
            
        for j in jornadas:
            frame_fila = ctk.CTkFrame(self.frame_lista_jornadas)
            frame_fila.pack(fill="x", pady=2, padx=5)
            
            texto = f"📅 {j['fecha']}  |  🏆 {j['nombre_liga']}"
            ctk.CTkLabel(frame_fila, text=texto, font=("Arial", 14, "bold")).pack(side="left", padx=15, pady=10)
            
            ctk.CTkButton(frame_fila, text="Borrar", fg_color="red", hover_color="darkred", width=70, command=lambda f=j['fecha'], l=j['id_liga']: self.evento_eliminar_jornada(f, l)).pack(side="right", padx=5)
            
            ctk.CTkButton(frame_fila, text="Editar", width=70, command=lambda f=j['fecha'], l=j['id_liga']: self.abrir_ventana_edicion(f, l, nueva=False)).pack(side="right", padx=5)

    def evento_eliminar_jornada(self, fecha, id_liga):
        respuesta = messagebox.askyesno("Confirmar", f"¿Borrar todos los datos de la jornada del {fecha}?")
        if respuesta:
            db.eliminar_jornada(fecha, id_liga)
            self.cargar_lista_jornadas()

    def abrir_ventana_edicion(self, fecha, id_liga, nueva=False):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar Jornada" if not nueva else "Nueva Jornada Manual")
        ventana.geometry("500x550")
        ventana.attributes("-topmost", True)
        
        frame_top = ctk.CTkFrame(ventana, fg_color="transparent")
        frame_top.pack(pady=10)
        
        entrada_fecha = DateEntry(frame_top, width=15, background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
        entrada_fecha.pack(side="left", padx=5)
        
        var_liga = ctk.StringVar(value="Bullpadel" if id_liga == 1 else "Interclubes")
        menu_liga = ctk.CTkOptionMenu(frame_top, values=["Bullpadel", "Interclubes"], variable=var_liga, width=120)
        menu_liga.pack(side="left", padx=5)
        
        if not nueva:
            entrada_fecha.set_date(fecha)
            entrada_fecha.configure(state="disabled")
            menu_liga.configure(state="disabled")
            
        estados_previos = db.obtener_estado_jugadoras_jornada(fecha, id_liga) if not nueva else {}
        
        frame_lista = ctk.CTkScrollableFrame(ventana, width=450, height=350)
        frame_lista.pack(pady=10)
        
        jugadoras = db.obtener_jugadoras()
        opciones_estado = []
        
        for j in jugadoras:
            f_fila = ctk.CTkFrame(frame_lista)
            f_fila.pack(fill="x", pady=2)
            
            ctk.CTkLabel(f_fila, text=f"{j['nombre']} ({j['posicion']})", width=150, anchor="w").pack(side="left", padx=10)
            estado_guardado = estados_previos.get(j['id'], "No disponible")
            
            var_est = ctk.StringVar(value=estado_guardado)
            menu = ctk.CTkOptionMenu(f_fila, values=["No disponible", "Convocada", "Descartada"], variable=var_est, width=110)
            menu.configure(command=lambda choice, m=menu: self.actualizar_color_menu(choice, m))
            menu.pack(side="right", padx=10)
            
            self.actualizar_color_menu(estado_guardado, menu)
            opciones_estado.append({"id": j['id'], "var": var_est})
            
        def guardar_cambios():
            nueva_fecha = entrada_fecha.get()
            if not nueva_fecha:
                return
                
            n_liga = 1 if var_liga.get() == "Bullpadel" else 2
            
            num_convocadas = sum(1 for item in opciones_estado if item['var'].get() == "Convocada")
            if num_convocadas != 6:
                messagebox.showerror("Error", f"Debes marcar exactamente 6 jugadoras como 'Convocada'.\nActualmente: {num_convocadas}.")
                return 
            
            if nueva and db.existe_jornada(nueva_fecha, n_liga):
                respuesta = messagebox.askyesno("Conflicto", f"Ya existe una jornada el {nueva_fecha}.\n¿Sobrescribir?")
                if not respuesta:
                    return
                db.eliminar_jornada(nueva_fecha, n_liga)
            
            if not nueva:
                db.eliminar_jornada(fecha, id_liga)
                
            for item in opciones_estado:
                est = item['var'].get()
                if est != "No disponible":
                    db.registrar_convocatoria(item['id'], n_liga, nueva_fecha, est)
                    
            ventana.destroy()
            self.cargar_lista_jornadas()
            
        ctk.CTkButton(ventana, text="Guardar Cambios", fg_color="green", hover_color="darkgreen", command=guardar_cambios).pack(pady=10)

if __name__ == "__main__":
    # CRÍTICO: Si el archivo no existe, lo crea con sus tablas antes de arrancar la interfaz
    db.inicializar_db() 
    app = PadelApp()
    app.mainloop()