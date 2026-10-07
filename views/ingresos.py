import customtkinter as ctk
from db.database import get_connection
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from services.resumen import resumen_mes


class IngresosView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._init_tabla()
        self.mes_filtro = date.today().strftime("%Y-%m")
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
                nota TEXT,
                recurrente INTEGER DEFAULT 0
            )
        ''')
        try:
            conn.execute("ALTER TABLE ingresos ADD COLUMN recurrente INTEGER DEFAULT 0")
        except Exception:
            pass
        conn.commit()
        conn.close()

    def _build(self):
        # ── HEADER ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 8))

        ctk.CTkLabel(header, text="💵  Ingresos",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#ffffff").pack(side="left")

        ctk.CTkButton(header, text="＋ Agregar", width=120, height=36,
                      corner_radius=18,
                      fg_color="#27ae60", hover_color="#1e8449",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self._agregar).pack(side="right", padx=(6, 0))

        ctk.CTkButton(header, text="🔄  Recurrentes", width=140, height=36,
                      corner_radius=18,
                      fg_color="#1a3a5c", hover_color="#1a5276",
                      font=ctk.CTkFont(size=13),
                      command=self._proponer_recurrentes).pack(side="right", padx=6)

        # Filtro mes
        filtro = ctk.CTkFrame(self, fg_color="transparent")
        filtro.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(filtro, text="Período:", font=ctk.CTkFont(size=12),
                     text_color="#888888").pack(side="left", padx=(0, 8))
        hoy = date.today()
        self.meses = [(hoy.replace(day=1) - relativedelta(months=i)).strftime("%Y-%m")
                      for i in range(12)]
        self.mes_var = ctk.StringVar(value=self.mes_filtro)
        ctk.CTkOptionMenu(filtro, variable=self.mes_var, values=self.meses,
                          width=140, height=32, corner_radius=8,
                          command=self._cambiar_mes).pack(side="left")

        # Frames
        self.resumen_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.resumen_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.balance_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.balance_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.grafico_frame = ctk.CTkFrame(self, fg_color="#16162a", corner_radius=12)
        self.grafico_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#111118", corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._cargar()

    def _cambiar_mes(self, valor):
        self.mes_filtro = valor
        self._cargar()

    def _cargar(self):
        for f in [self.resumen_frame, self.balance_frame,
                  self.grafico_frame, self.scroll]:
            for w in f.winfo_children():
                w.destroy()

        conn = get_connection()
        mes = self.mes_filtro

        ingresos    = conn.execute("SELECT * FROM ingresos WHERE mes=? ORDER BY fecha DESC", (mes,)).fetchall()
        total_mes   = conn.execute("SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes=?", (mes,)).fetchone()["t"]
        nico_mes    = conn.execute("SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes=? AND titular='Nico'", (mes,)).fetchone()["t"]
        mama_mes    = conn.execute("SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes=? AND titular='Mama'", (mes,)).fetchone()["t"]
        airbnb_mes  = conn.execute("SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes=? AND tipo='Airbnb'", (mes,)).fetchone()["t"]
        extra_mes   = conn.execute("SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes=? AND tipo='Extra'", (mes,)).fetchone()["t"]
        total_anio  = conn.execute("SELECT COALESCE(SUM(monto),0) as t FROM ingresos WHERE mes LIKE ?", (f"{mes[:4]}%",)).fetchone()["t"]

        # Mismo cálculo que el Dashboard: lo pagado del mes + lo que falta pagar
        r = resumen_mes(date(int(mes[:4]), int(mes[5:]), 1))
        es_mes_actual = mes == date.today().strftime("%Y-%m")
        total_gastos = r["pagado"] + (r["falta"] if es_mes_actual else 0)

        # Meses con datos reales + 2 meses futuros proyectados
        hoy = date.today()
        datos_grafico = []

        # Meses con ingresos registrados
        meses_con_datos = conn.execute(
            "SELECT mes, SUM(monto) as t FROM ingresos GROUP BY mes ORDER BY mes"
        ).fetchall()
        for row in meses_con_datos:
            datos_grafico.append((row["mes"][5:], row["t"], total_gastos, False))

        # 2 meses futuros proyectados (usando promedio de ingresos reales)
        avg_ing = conn.execute(
            "SELECT COALESCE(AVG(t),0) as a FROM (SELECT SUM(monto) as t FROM ingresos GROUP BY mes)"
        ).fetchone()["a"]
        for i in range(1, 3):
            m = (hoy.replace(day=1) + relativedelta(months=i)).strftime("%Y-%m")
            datos_grafico.append((m[5:], avg_ing, total_gastos, True))

        conn.close()

        balance = total_mes - total_gastos

        # ── TARJETAS PEQUEÑAS ────────────────────────────────────────────
        tarjetas = [
            ("💵 Total mes",  f"${total_mes:,}",  "#2ecc71"),
            ("👤 Nico",       f"${nico_mes:,}",   "#00bcd4"),
            ("👩 Mamá",       f"${mama_mes:,}",   "#ce93d8"),
            ("🏠 Airbnb",     f"${airbnb_mes:,}", "#fbbf24"),
            ("⭐ Extras",      f"${extra_mes:,}",  "#f97316"),
            ("📅 Año",        f"${total_anio:,}", "#a78bfa"),
        ]
        for titulo, valor, color in tarjetas:
            card = ctk.CTkFrame(self.resumen_frame, fg_color="#16162a", corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=4)
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=10),
                         text_color="#555577").pack(pady=(10, 2))
            ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=color).pack(pady=(0, 10))

        # ── PANEL BALANCE DESTACADO ──────────────────────────────────────
        color_bal = "#2ecc71" if balance >= 0 else "#e74c3c"
        signo     = "+" if balance >= 0 else ""
        msg       = "✅ Mes cubierto" if balance >= 0 else f"⚠️ Faltan ${abs(balance):,} para cubrir gastos"

        bal_panel = ctk.CTkFrame(self.balance_frame, fg_color="#16162a", corner_radius=12)
        bal_panel.pack(fill="x")

        left = ctk.CTkFrame(bal_panel, fg_color="transparent")
        left.pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(left, text="BALANCE DEL MES",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#555577").pack(anchor="w")
        ctk.CTkLabel(left, text=f"{signo}${abs(balance):,}",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=color_bal).pack(anchor="w")
        ctk.CTkLabel(left, text=msg, font=ctk.CTkFont(size=12),
                     text_color=color_bal).pack(anchor="w")

        right = ctk.CTkFrame(bal_panel, fg_color="transparent")
        right.pack(side="right", padx=20, pady=12)

        for label, val, col in [
            ("Ingresos", f"${total_mes:,}", "#2ecc71"),
            ("Gastos est.", f"${total_gastos:,}", "#e74c3c"),
        ]:
            r = ctk.CTkFrame(right, fg_color="transparent")
            r.pack(anchor="e")
            ctk.CTkLabel(r, text=f"{label}:", font=ctk.CTkFont(size=12),
                         text_color="#555577").pack(side="left", padx=(0, 8))
            ctk.CTkLabel(r, text=val, font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=col).pack(side="left")

        # ── GRÁFICO MATPLOTLIB ──────────────────────────────────────────
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np

            labels   = [d[0] for d in datos_grafico]
            ing_vals = [d[1] / 1_000_000 for d in datos_grafico]
            gas_vals = [d[2] / 1_000_000 for d in datos_grafico]
            proyect  = [d[3] for d in datos_grafico]

            fig, ax = plt.subplots(figsize=(9, 2.6))
            fig.patch.set_facecolor("#16162a")
            ax.set_facecolor("#16162a")

            x = np.arange(len(labels))
            w = 0.32

            # Barras reales vs proyectadas
            for i, (iv, gv, pr) in enumerate(zip(ing_vals, gas_vals, proyect)):
                alpha_ing = 0.4 if pr else 0.9
                alpha_gas = 0.3 if pr else 0.9
                hatch = "//" if pr else None

                b1 = ax.bar(i - w/2, iv, width=w, color="#2ecc71",
                            alpha=alpha_ing, zorder=3, hatch=hatch)
                b2 = ax.bar(i + w/2, gv, width=w, color="#e74c3c",
                            alpha=alpha_gas, zorder=3, hatch=hatch)

                if iv > 0:
                    ax.text(i - w/2, iv + 0.03, f"${iv:.1f}M",
                            ha="center", va="bottom", fontsize=7,
                            color="#2ecc71" if not pr else "#555577")
                ax.text(i + w/2, gv + 0.03, f"${gv:.1f}M",
                        ha="center", va="bottom", fontsize=7,
                        color="#e74c3c" if not pr else "#555577")

            # Leyenda manual
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor="#2ecc71", label="Ingresos"),
                Patch(facecolor="#e74c3c", label="Gastos est."),
                Patch(facecolor="#555577", alpha=0.4, hatch="//", label="Proyectado"),
            ]
            ax.legend(handles=legend_elements, facecolor="#16162a",
                      edgecolor="#2a2a4a", labelcolor="#aaaaaa",
                      fontsize=9, loc="upper left")

            ax.set_xticks(x)
            ax.set_xticklabels(labels, color="#888888", fontsize=9)
            ax.tick_params(axis="y", colors="#555577", labelsize=8)
            ax.set_ylabel("Millones $", color="#555577", fontsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#2a2a4a")
            ax.spines["bottom"].set_color("#2a2a4a")
            ax.yaxis.grid(True, color="#2a2a4a", linewidth=0.6, zorder=0)
            ax.set_axisbelow(True)


            plt.tight_layout(pad=0.8)

            canvas = FigureCanvasTkAgg(fig, master=self.grafico_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="x", padx=10, pady=10)
            plt.close(fig)

        except Exception as e:
            ctk.CTkLabel(self.grafico_frame,
                         text="pip install matplotlib  para ver el gráfico",
                         text_color="#555", font=ctk.CTkFont(size=11)).pack(pady=15)

        # ── TABLA ────────────────────────────────────────────────────────
        if not ingresos:
            ctk.CTkLabel(self.scroll,
                         text="Sin ingresos en este mes",
                         font=ctk.CTkFont(size=13), text_color="#444").pack(pady=30)
            return

        hdr = ctk.CTkFrame(self.scroll, fg_color="#1a1a2e", corner_radius=6)
        hdr.pack(fill="x", padx=4, pady=(4, 2))
        for texto, ancho in [("Titular",110),("Tipo",110),("Monto",120),
                              ("Fecha",105),("🔁",60),("Nota",0),("",90)]:
            ctk.CTkLabel(hdr, text=texto, font=ctk.CTkFont(size=12, weight="bold"),
                         width=ancho if ancho else 1, anchor="w",
                         text_color="#6677aa").pack(side="left", padx=8, pady=7,
                                                    expand=(ancho==0), fill="x" if ancho==0 else "none")

        for i, ing in enumerate(ingresos):
            self._fila(ing, i)

    def _fila(self, ing, idx):
        color_t = "#00bcd4" if ing["titular"] == "Nico" else "#ce93d8"
        bg = "#1a1a2e" if idx % 2 == 0 else "#111118"
        fila = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=6)
        fila.pack(fill="x", padx=4, pady=1)

        try:
            dt = datetime.strptime(ing["fecha"], "%Y-%m-%d")
            fecha_txt = dt.strftime("%d/%m/%Y")
        except Exception:
            fecha_txt = ing["fecha"]

        def celda(texto, ancho=0, color="#cccccc", bold=False, expand=False):
            ctk.CTkLabel(fila, text=str(texto),
                         font=ctk.CTkFont(size=13, weight="bold" if bold else "normal"),
                         width=ancho if ancho else 1,
                         anchor="w", text_color=color,
                         ).pack(side="left", padx=8, pady=9,
                                expand=expand, fill="x" if expand else "none")

        celda(ing["titular"],          110, color_t,   bold=True)
        celda(ing["tipo"],             110, "#aaaaaa")
        celda(f"${ing['monto']:,}",    120, "#2ecc71",  bold=True)
        celda(fecha_txt,               105, "#888888")
        celda("🔁" if ing["recurrente"] else "—", 60,
              "#fbbf24" if ing["recurrente"] else "#333355")
        celda(ing["nota"] or "—",      0,  "#555577",  expand=True)

        btns = ctk.CTkFrame(fila, fg_color="transparent")
        btns.pack(side="right", padx=8)

        ctk.CTkButton(btns, text="✏️", width=34, height=28,
                      corner_radius=8,
                      fg_color="#1a3a5c", hover_color="#1a5276",
                      command=lambda i=ing: self._editar(i)).pack(side="left", padx=3)

        ctk.CTkButton(btns, text="🗑", width=34, height=28,
                      corner_radius=8,
                      fg_color="#3b0a0a", hover_color="#7f1d1d",
                      command=lambda i=ing["id"]: self._eliminar(i)).pack(side="left", padx=3)

    def _form(self, win, ing=None):
        ctk.CTkLabel(win, text="Titular:").pack(pady=(0,2))
        titular_var = ctk.StringVar(value=ing["titular"] if ing else "Nico")
        ff = ctk.CTkFrame(win, fg_color="transparent")
        ff.pack(pady=(0,8))
        ctk.CTkRadioButton(ff, text="Nico", variable=titular_var,
                           value="Nico").pack(side="left", padx=15)
        ctk.CTkRadioButton(ff, text="Mamá", variable=titular_var,
                           value="Mama").pack(side="left", padx=15)

        ctk.CTkLabel(win, text="Tipo:").pack(pady=(0,2))
        tipo_var = ctk.StringVar(value=ing["tipo"] if ing else "Sueldo")
        ctk.CTkOptionMenu(win, variable=tipo_var,
                          values=["Sueldo","Airbnb","Extra","Otro"],
                          width=220).pack(pady=(0,8))

        ctk.CTkLabel(win, text="Monto ($):").pack(pady=(0,2))
        entry_monto = ctk.CTkEntry(win, placeholder_text="ej: 750000", width=260)
        if ing:
            entry_monto.insert(0, str(ing["monto"]))
        entry_monto.pack(pady=(0,8))

        ctk.CTkLabel(win, text="Fecha (DD / MM / AAAA):").pack(pady=(0,2))
        ff2 = ctk.CTkFrame(win, fg_color="transparent")
        ff2.pack(pady=(0,8))
        hoy = date.today()
        if ing:
            try:
                dt = datetime.strptime(ing["fecha"], "%Y-%m-%d")
                d, m, a = dt.day, dt.month, dt.year
            except Exception:
                d, m, a = hoy.day, hoy.month, hoy.year
        else:
            d, m, a = hoy.day, hoy.month, hoy.year

        e_dia = ctk.CTkEntry(ff2, width=65)
        e_dia.insert(0, str(d).zfill(2))
        e_dia.pack(side="left", padx=4)
        e_mes = ctk.CTkEntry(ff2, width=65)
        e_mes.insert(0, str(m).zfill(2))
        e_mes.pack(side="left", padx=4)
        e_anio = ctk.CTkEntry(ff2, width=85)
        e_anio.insert(0, str(a))
        e_anio.pack(side="left", padx=4)

        ctk.CTkLabel(win, text="Nota (opcional):").pack(pady=(0,2))
        entry_nota = ctk.CTkEntry(win, placeholder_text="ej: Sueldo agosto", width=260)
        if ing and ing["nota"]:
            entry_nota.insert(0, ing["nota"])
        entry_nota.pack(pady=(0,8))

        rec_var = ctk.BooleanVar(value=bool(ing["recurrente"]) if ing else False)
        ctk.CTkCheckBox(win, text="🔁  Marcar como ingreso recurrente mensual",
                        variable=rec_var).pack(pady=(0,8))

        return titular_var, tipo_var, entry_monto, e_dia, e_mes, e_anio, entry_nota, rec_var

    def _agregar(self):
        win = ctk.CTkToplevel(self)
        win.title("Nuevo Ingreso")
        win.geometry("400x520")
        win.grab_set()
        ctk.CTkLabel(win, text="💵  Nuevo Ingreso",
                     font=ctk.CTkFont(weight="bold", size=15)).pack(pady=15)
        t, ti, m, d, me, a, n, r = self._form(win)
        lbl_err = ctk.CTkLabel(win, text="", text_color="#e74c3c")
        lbl_err.pack()

        def guardar():
            try:
                monto = int(m.get().replace(".", "").replace(",", ""))
                fecha_iso = f"{a.get()}-{me.get().zfill(2)}-{d.get().zfill(2)}"
                mes_str   = f"{a.get()}-{me.get().zfill(2)}"
                conn = get_connection()
                conn.execute(
                    "INSERT INTO ingresos (titular,tipo,monto,fecha,mes,nota,recurrente) VALUES (?,?,?,?,?,?,?)",
                    (t.get(), ti.get(), monto, fecha_iso, mes_str, n.get() or None, int(r.get()))
                )
                conn.commit(); conn.close()
                win.destroy(); self._cargar()
            except ValueError:
                lbl_err.configure(text="Monto inválido — solo números")

        ctk.CTkButton(win, text="Guardar", command=guardar,
                      fg_color="#27ae60", width=220, height=38,
                      corner_radius=10, font=ctk.CTkFont(size=14)).pack(pady=12)

    def _editar(self, ing):
        win = ctk.CTkToplevel(self)
        win.title("Editar Ingreso")
        win.geometry("400x540")
        win.grab_set()
        ctk.CTkLabel(win, text="✏️  Editar Ingreso",
                     font=ctk.CTkFont(weight="bold", size=15)).pack(pady=15)
        t, ti, m, d, me, a, n, r = self._form(win, ing)
        lbl_err = ctk.CTkLabel(win, text="", text_color="#e74c3c")
        lbl_err.pack()

        def guardar():
            try:
                monto = int(m.get().replace(".", "").replace(",", ""))
                fecha_iso = f"{a.get()}-{me.get().zfill(2)}-{d.get().zfill(2)}"
                mes_str   = f"{a.get()}-{me.get().zfill(2)}"
                conn = get_connection()
                conn.execute(
                    "UPDATE ingresos SET titular=?,tipo=?,monto=?,fecha=?,mes=?,nota=?,recurrente=? WHERE id=?",
                    (t.get(), ti.get(), monto, fecha_iso, mes_str, n.get() or None, int(r.get()), ing["id"])
                )
                conn.commit(); conn.close()
                win.destroy(); self._cargar()
            except ValueError:
                lbl_err.configure(text="Monto inválido — solo números")

        ctk.CTkButton(win, text="Guardar cambios", command=guardar,
                      fg_color="#2980b9", width=220, height=38,
                      corner_radius=10, font=ctk.CTkFont(size=14)).pack(pady=12)

    def _proponer_recurrentes(self):
        hoy = date.today()
        mes_actual   = hoy.strftime("%Y-%m")
        mes_anterior = (hoy.replace(day=1) - relativedelta(months=1)).strftime("%Y-%m")
        conn = get_connection()
        recurrentes = conn.execute(
            "SELECT * FROM ingresos WHERE mes=? AND recurrente=1", (mes_anterior,)
        ).fetchall()
        conn.close()

        if not recurrentes:
            win = ctk.CTkToplevel(self)
            win.geometry("320x130")
            ctk.CTkLabel(win, text="No hay ingresos recurrentes\ndel mes anterior.",
                         font=ctk.CTkFont(size=13)).pack(expand=True)
            ctk.CTkButton(win, text="Cerrar", command=win.destroy).pack(pady=10)
            return

        win = ctk.CTkToplevel(self)
        win.title("Recurrentes")
        win.geometry("420x320")
        win.grab_set()
        ctk.CTkLabel(win, text="🔁  Ingresos recurrentes",
                     font=ctk.CTkFont(weight="bold", size=14)).pack(pady=12)
        ctk.CTkLabel(win, text=f"Se copiarán al mes {mes_actual}:",
                     text_color="#aaaaaa").pack()
        frame = ctk.CTkScrollableFrame(win)
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        for r in recurrentes:
            ctk.CTkLabel(frame,
                         text=f"• {r['titular']}  —  {r['tipo']}:  ${r['monto']:,}",
                         anchor="w", text_color="#cccccc").pack(fill="x", pady=3)

        def confirmar():
            conn = get_connection()
            for r in recurrentes:
                conn.execute(
                    "INSERT INTO ingresos (titular,tipo,monto,fecha,mes,nota,recurrente) VALUES (?,?,?,?,?,?,1)",
                    (r["titular"], r["tipo"], r["monto"],
                     f"{mes_actual}-01", mes_actual, r["nota"])
                )
            conn.commit(); conn.close()
            win.destroy()
            self.mes_var.set(mes_actual)
            self.mes_filtro = mes_actual
            self._cargar()

        ctk.CTkButton(win, text="✅  Confirmar", command=confirmar,
                      fg_color="#27ae60", width=200).pack(pady=12)

    def _eliminar(self, ingreso_id):
        conn = get_connection()
        conn.execute("DELETE FROM ingresos WHERE id=?", (ingreso_id,))
        conn.commit(); conn.close()
        self._cargar()
