import customtkinter as ctk
from db.database import get_connection
from datetime import date, datetime


class IngresosView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._init_tabla()
        self._build()

    def _init_tabla(self):
        conn = get_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ingresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titular TEXT NOT NULL,
                tipo TEXT NOT NULL,
                monto INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                mes TEXT NOT NULL,
                nota TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _build(self):
        ctk.CTkLabel(
            self, text="💵 Ingresos",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(15, 5))

        self.resumen_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.resumen_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkButton(
            self, text="+ Agregar Ingreso", width=200,
            fg_color="#27ae60", hover_color="#1e8449",
            command=self._agregar
        ).pack(pady=(0, 10))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=("#e8e8e8", "#1a1a1a"))
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self._cargar()

    def _cargar(self):
        for w in self.resumen_frame.winfo_children():
            w.destroy()
        for w in self.scroll.winfo_children():
            w.destroy()

        conn = get_connection()
        mes_actual = date.today().strftime("%Y-%m")

        ingresos = conn.execute(
            "SELECT * FROM ingresos ORDER BY fecha DESC"
        ).fetchall()

        total_mes = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes = ?",
            (mes_actual,)
        ).fetchone()["t"]

        nico_mes = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes = ? AND titular = 'Nico'",
            (mes_actual,)
        ).fetchone()["t"]

        mama_mes = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes = ? AND titular = 'Mama'",
            (mes_actual,)
        ).fetchone()["t"]

        airbnb_mes = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes = ? AND tipo = 'Airbnb'",
            (mes_actual,)
        ).fetchone()["t"]

        extra_mes = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes = ? AND tipo = 'Extra'",
            (mes_actual,)
        ).fetchone()["t"]

        conn.close()

        tarjetas = [
            ("💵 Total este mes", f"${total_mes:,}",  "#2ecc71"),
            ("👤 Nico",           f"${nico_mes:,}",   "#00bcd4"),
            ("👩 Mamá",           f"${mama_mes:,}",   "#ce93d8"),
            ("🏠 Airbnb",         f"${airbnb_mes:,}", "#fbbf24"),
            ("⭐ Extras",          f"${extra_mes:,}",  "#f97316"),
        ]
        for titulo, valor, color in tarjetas:
            card = ctk.CTkFrame(self.resumen_frame, fg_color="#1e1e2e", corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=6, pady=5)
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=11),
                         text_color="#aaaaaa").pack(pady=(12, 2))
            ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=color).pack(pady=(0, 12))

        if not ingresos:
            ctk.CTkLabel(self.scroll,
                         text="Sin ingresos registrados — presioná '+ Agregar Ingreso'",
                         font=ctk.CTkFont(size=14), text_color="#555").pack(pady=40)
            return

        # Encabezados
        header = ctk.CTkFrame(self.scroll, fg_color="#1a1a2e")
        header.pack(fill="x", padx=5, pady=(0, 4))
        cols = [
            ("Titular", 100), ("Tipo", 120), ("Monto", 120),
            ("Fecha", 110), ("Mes", 90), ("Nota", 200), ("", 50),
        ]
        for texto, ancho in cols:
            ctk.CTkLabel(header, text=texto, font=ctk.CTkFont(weight="bold"),
                         width=ancho, anchor="w").pack(side="left", padx=6, pady=6)

        for ing in ingresos:
            self._fila(ing)

    def _fila(self, ing):
        color_titular = "#00bcd4" if ing["titular"] == "Nico" else "#ce93d8"
        fila = ctk.CTkFrame(self.scroll, fg_color="#1e1e1e", corner_radius=6)
        fila.pack(fill="x", padx=5, pady=3)

        try:
            dt = datetime.strptime(ing["fecha"], "%Y-%m-%d")
            fecha_txt = dt.strftime("%d/%m/%Y")
        except Exception:
            fecha_txt = ing["fecha"]

        def celda(texto, ancho, color="#e0e0e0", bold=False):
            ctk.CTkLabel(fila, text=str(texto),
                         font=ctk.CTkFont(weight="bold" if bold else "normal"),
                         width=ancho, anchor="w", text_color=color).pack(side="left", padx=6, pady=8)

        celda(ing["titular"],        100, color_titular, bold=True)
        celda(ing["tipo"],           120)
        celda(f"${ing['monto']:,}",  120, "#2ecc71", bold=True)
        celda(fecha_txt,             110)
        celda(ing["mes"],             90, "#aaaaaa")
        celda(ing["nota"] or "—",    200, "#aaaaaa")

        ctk.CTkButton(
            fila, text="🗑", width=40, height=30,
            fg_color="#7f1d1d", hover_color="#991b1b",
            command=lambda i=ing["id"]: self._eliminar(i)
        ).pack(side="left", padx=4, pady=6)

    def _agregar(self):
        win = ctk.CTkToplevel(self)
        win.title("Agregar Ingreso")
        win.geometry("400x480")
        win.grab_set()

        ctk.CTkLabel(win, text="💵 Nuevo Ingreso",
                     font=ctk.CTkFont(weight="bold", size=14)).pack(pady=15)

        ctk.CTkLabel(win, text="Titular:").pack()
        titular_var = ctk.StringVar(value="Nico")
        frame_til = ctk.CTkFrame(win, fg_color="transparent")
        frame_til.pack(pady=5)
        ctk.CTkRadioButton(frame_til, text="Nico", variable=titular_var,
                           value="Nico").pack(side="left", padx=15)
        ctk.CTkRadioButton(frame_til, text="Mamá", variable=titular_var,
                           value="Mama").pack(side="left", padx=15)

        ctk.CTkLabel(win, text="Tipo:").pack()
        tipo_var = ctk.StringVar(value="Sueldo")
        ctk.CTkOptionMenu(win, variable=tipo_var,
                          values=["Sueldo", "Airbnb", "Extra", "Otro"]
                          ).pack(pady=5)

        ctk.CTkLabel(win, text="Monto ($):").pack()
        entry_monto = ctk.CTkEntry(win, placeholder_text="ej: 750000", width=250)
        entry_monto.pack(pady=5)

        ctk.CTkLabel(win, text="Fecha (DD / MM / AAAA):").pack()
        ff = ctk.CTkFrame(win, fg_color="transparent")
        ff.pack(pady=5)
        hoy = date.today()

        e_dia = ctk.CTkEntry(ff, width=60, placeholder_text="DD")
        e_dia.insert(0, str(hoy.day).zfill(2))
        e_dia.pack(side="left", padx=4)

        e_mes = ctk.CTkEntry(ff, width=60, placeholder_text="MM")
        e_mes.insert(0, str(hoy.month).zfill(2))
        e_mes.pack(side="left", padx=4)

        e_anio = ctk.CTkEntry(ff, width=80, placeholder_text="AAAA")
        e_anio.insert(0, str(hoy.year))
        e_anio.pack(side="left", padx=4)

        ctk.CTkLabel(win, text="Nota (opcional):").pack()
        entry_nota = ctk.CTkEntry(win, placeholder_text="ej: Sueldo agosto", width=250)
        entry_nota.pack(pady=5)

        lbl_err = ctk.CTkLabel(win, text="", text_color="#e74c3c")
        lbl_err.pack()

        def guardar():
            try:
                monto = int(entry_monto.get().replace(".", "").replace(",", ""))
                fecha_iso = f"{e_anio.get()}-{e_mes.get().zfill(2)}-{e_dia.get().zfill(2)}"
                mes_str = f"{e_anio.get()}-{e_mes.get().zfill(2)}"
                conn = get_connection()
                conn.execute(
                    "INSERT INTO ingresos (titular, tipo, monto, fecha, mes, nota) VALUES (?,?,?,?,?,?)",
                    (titular_var.get(), tipo_var.get(), monto, fecha_iso, mes_str,
                     entry_nota.get() or None)
                )
                conn.commit()
                conn.close()
                win.destroy()
                self._cargar()
            except ValueError:
                lbl_err.configure(text="Monto inválido — solo números")

        ctk.CTkButton(win, text="Guardar", command=guardar,
                      fg_color="#27ae60", width=200).pack(pady=15)

    def _eliminar(self, ingreso_id):
        conn = get_connection()
        conn.execute("DELETE FROM ingresos WHERE id = ?", (ingreso_id,))
        conn.commit()
        conn.close()
        self._cargar()
