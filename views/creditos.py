import customtkinter as ctk
from db.database import get_connection
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from services.resumen import (resumen_mes, credito_activo, es_planilla,
                              pagado_creditos_por_mes)
from views import tema
from views import componentes as ui


def _sumar_un_mes(fecha_str):
    try:
        dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        return (dt + relativedelta(months=1)).strftime("%d/%m/%Y")
    except Exception:
        return fecha_str


def _plural(n, singular, plural):
    """_plural(1, 'cuota', 'cuotas') -> '1 cuota'; con 2 -> '2 cuotas'."""
    return f"{n} {singular if n == 1 else plural}"


class CreditosView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=tema.FONDO, corner_radius=0)
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        # Encabezado: se rellena en _actualizar_resumen()
        self.cabecera = ctk.CTkFrame(self, fg_color="transparent")
        self.cabecera.pack(fill="x", padx=(34, 30), pady=(24, 0))

        # Tarjetas resumen: se crean UNA vez y después solo se actualizan
        fila_tarjetas = ctk.CTkFrame(self, fg_color="transparent")
        fila_tarjetas.pack(fill="x", padx=(28, 24), pady=(14, 10))
        self.tarjetas = {}
        colores = [("pagado", tema.VERDE), ("falta", tema.AMBAR),
                   ("proximo", tema.AZUL), ("deuda", tema.ROJO)]
        for i, (clave, color) in enumerate(colores):
            fila_tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjetas")
            tarjeta = ui.TarjetaResumen(fila_tarjetas, "", "", color=color)
            tarjeta.grid(row=0, column=i, sticky="ew")
            self.tarjetas[clave] = tarjeta

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=("#e8e8e8", "#1a1a1a"))
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self._cargar_creditos()

    def _cargar_creditos(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        conn = get_connection()
        creditos = conn.execute(
            "SELECT * FROM creditos ORDER BY titular DESC, banco"
        ).fetchall()
        conn.close()

        self._actualizar_resumen(creditos)

        if not creditos:
            ctk.CTkLabel(self.scroll, text="Sin créditos registrados",
                         font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        # ── ENCABEZADOS ─────────────────────────────────────────────────
        header = ctk.CTkFrame(self.scroll, fg_color="#1a1a2e")
        header.pack(fill="x", padx=5, pady=(0, 4))
        cols = [
            ("Titular",      100), ("Banco",       120), ("N° Crédito",  140),
            ("Cuota",         95), ("Pagadas",       75), ("Restantes",    75),
            ("Últ. Pago",    130), ("Próx. Vcto.",  110), ("Estado",      110),
            ("Acciones",     240),
        ]
        for texto, ancho in cols:
            ctk.CTkLabel(header, text=texto, font=ctk.CTkFont(weight="bold"),
                         width=ancho, anchor="w").pack(side="left", padx=4, pady=6)

        for cr in creditos:
            self._fila(cr)

    # ── Encabezado y tarjetas ───────────────────────────────────────────
    def _actualizar_resumen(self, creditos):
        r = resumen_mes()
        hoy = date.today()
        activos = sum(1 for cr in creditos if credito_activo(cr))

        for w in self.cabecera.winfo_children():
            w.destroy()
        subtitulo = f"{r['mes'].capitalize()} {hoy.year}, " + _plural(
            activos, "crédito activo", "créditos activos")
        ui.titulo_seccion(self.cabecera, "Créditos", subtitulo).pack(side="left")

        self._poner_tarjeta(
            "pagado", f"Pagado en {r['mes']}", r["pagado_creditos"],
            _plural(r["n_pagos_creditos"], "pago registrado", "pagos registrados"),
            serie=pagado_creditos_por_mes())

        falta = r["falta_creditos"]
        self._poner_tarjeta(
            "falta", "Falta pagar", falta,
            _plural(r["n_falta_creditos"], "cuota pendiente", "cuotas pendientes")
            if falta else "Nada pendiente",
            color=tema.AMBAR if falta else tema.VERDE)

        self._poner_tarjeta(
            "proximo", f"Vence en {r['mes_prox']}", r["proximo_creditos"],
            _plural(r["n_proximo_creditos"], "cuota", "cuotas"))

        problemas = []
        if r["judiciales"]:
            problemas.append(f"{r['judiciales']} en judicial")
        if r["atrasados"]:
            problemas.append(_plural(r["atrasados"], "atrasado", "atrasados"))
        self._poner_tarjeta(
            "deuda", "Deuda restante", r["deuda"],
            ", ".join(problemas) if problemas else "Todo al día")

    def _poner_tarjeta(self, clave, titulo, monto, detalle, color=None, serie=None):
        tarjeta = self.tarjetas[clave]
        tarjeta.titulo = titulo
        if color:
            tarjeta.color = color
        tarjeta.actualizar(valor=tema.pesos(monto), detalle=detalle, serie=serie)

    def _ultimo_pago(self, credito_id):
        conn = get_connection()
        row = conn.execute(
            "SELECT monto_real, fecha FROM pagos_creditos "
            "WHERE credito_id = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (credito_id,),
        ).fetchone()
        conn.close()
        if row:
            try:
                dt = datetime.strptime(row["fecha"], "%Y-%m-%d")
                return row["monto_real"], dt.strftime("%d/%m/%Y")
            except Exception:
                return row["monto_real"], row["fecha"]
        return None, None

    def _fila(self, cr):
        terminado = not credito_activo(cr)
        planilla  = es_planilla(cr)
        estado  = "terminado" if terminado else ("planilla" if planilla and cr["estado"] == "al_dia" else cr["estado"])
        titular = cr["titular"]

        # Color fondo por estado
        bg = {"judicial": "#3b0000", "atrasado": "#2b1a00"}.get(estado, "#1e1e1e")

        fila = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=6)
        fila.pack(fill="x", padx=5, pady=3)

        pagadas     = cr["cuotas_pagadas"] or 0
        total       = cr["cuotas_total"]   or 0
        restantes   = max(0, total - pagadas) if total else "—"
        pagadas_txt = f"{pagadas}/{total}" if total else "—"

        monto_ult, fecha_ult = self._ultimo_pago(cr["id"])
        ult_txt = f"${monto_ult:,}\n{fecha_ult}" if monto_ult else "Sin pagos"

        prox_vcto = "—" if terminado else ("Desc. sueldo" if planilla else (cr["prox_vencimiento"] or "—"))

        color_cuota = "#e74c3c" if estado in ("judicial", "atrasado") else "#3498db"

        # Color titular: Nico = celeste, Mama = violeta
        color_titular = "#00bcd4" if titular == "Nico" else "#ce93d8"
        if terminado:
            color_cuota = "#666666"

        etiqueta, color_estado = {
            "al_dia":   ("✅ Al día",    "#2ecc71"),
            "atrasado": ("⚠️ Atrasado", "#e67e22"),
            "judicial": ("🔴 Judicial",  "#e74c3c"),
            "terminado": ("🏁 Terminado", "#888888"),
            "planilla":  ("🧾 Planilla",  "#9b8fd9"),
        }.get(estado, (estado, "#aaaaaa"))

        def celda(texto, ancho, color="#e0e0e0", bold=False):
            ctk.CTkLabel(fila, text=str(texto),
                         font=ctk.CTkFont(weight="bold" if bold else "normal"),
                         width=ancho, anchor="w", text_color=color,
                         justify="left").pack(side="left", padx=4, pady=8)

        celda(titular,                 100, color_titular, bold=True)
        celda(cr["banco"],             120)
        entry_num = ctk.CTkEntry(fila, width=135)
        entry_num.insert(0, cr["numero"] or "—")
        entry_num.configure(state="readonly")
        entry_num.pack(side="left", padx=4, pady=8)
        celda(f"${cr['cuota']:,}",      95, color_cuota, bold=True)
        celda(pagadas_txt,              75)
        celda(restantes,                75)
        celda(ult_txt,                 130)
        celda(prox_vcto,               110)
        celda(etiqueta,                110, color_estado, bold=True)

        btns = ctk.CTkFrame(fila, fg_color="transparent")
        btns.pack(side="left", padx=3)

        ctk.CTkButton(
            btns, text="💰 Pagar", width=78,
            fg_color="#27ae60", hover_color="#1e8449",
            command=lambda c=cr: self._registrar_pago(c),
        ).pack(side="left", padx=2, pady=6)

        ctk.CTkButton(
            btns, text="📋 Historial", width=88,
            fg_color="#2980b9", hover_color="#1a6fa1",
            command=lambda c=cr: self._ver_historial(c),
        ).pack(side="left", padx=2, pady=6)

        ctk.CTkButton(
            btns, text="↩", width=34, height=34,
            corner_radius=17,
            fg_color="#555", hover_color="#333",
            font=ctk.CTkFont(size=15),
            command=lambda c=cr: self._deshacer_pago(c),
        ).pack(side="left", padx=2, pady=6)

    def _registrar_pago(self, cr):
        win = ctk.CTkToplevel(self)
        win.title(f"Pagar — {cr['titular']} / {cr['banco']}")
        win.geometry("360x330")
        win.grab_set()

        ctk.CTkLabel(win, text=f"{cr['titular']} — {cr['banco']}",
                     font=ctk.CTkFont(weight="bold", size=14)).pack(pady=15)

        ctk.CTkLabel(win, text="Monto pagado ($):").pack()
        entry_monto = ctk.CTkEntry(win, placeholder_text=f"ej: {cr['cuota']:,}")
        entry_monto.pack(pady=5)

        ctk.CTkLabel(win, text="Fecha (DD / MM / AAAA):").pack()
        ff = ctk.CTkFrame(win, fg_color="transparent")
        ff.pack(pady=5)
        hoy = date.today()

        e_dia = ctk.CTkEntry(ff, width=55, placeholder_text="DD")
        e_dia.insert(0, str(hoy.day).zfill(2))
        e_dia.pack(side="left", padx=4)

        e_mes = ctk.CTkEntry(ff, width=55, placeholder_text="MM")
        e_mes.insert(0, str(hoy.month).zfill(2))
        e_mes.pack(side="left", padx=4)

        e_anio = ctk.CTkEntry(ff, width=75, placeholder_text="AAAA")
        e_anio.insert(0, str(hoy.year))
        e_anio.pack(side="left", padx=4)

        lbl_err = ctk.CTkLabel(win, text="", text_color="#e74c3c")
        lbl_err.pack()

        def guardar():
            try:
                monto = int(entry_monto.get().replace(".", "").replace(",", ""))
                fecha_iso = f"{e_anio.get()}-{e_mes.get().zfill(2)}-{e_dia.get().zfill(2)}"
                conn = get_connection()
                conn.execute(
                    "INSERT INTO pagos_creditos (credito_id, monto_real, fecha) VALUES (?, ?, ?)",
                    (cr["id"], monto, fecha_iso),
                )
                conn.execute(
                    "UPDATE creditos SET cuotas_pagadas = cuotas_pagadas + 1 WHERE id = ?",
                    (cr["id"],),
                )
                nuevo_vcto = _sumar_un_mes(cr["prox_vencimiento"]) if cr["prox_vencimiento"] else None
                if nuevo_vcto:
                    conn.execute(
                        "UPDATE creditos SET prox_vencimiento = ? WHERE id = ?",
                        (nuevo_vcto, cr["id"]),
                    )
                conn.commit()
                conn.close()
                win.destroy()
                self._cargar_creditos()
            except ValueError:
                lbl_err.configure(text="Monto inválido — solo números")

        ctk.CTkButton(win, text="Guardar", command=guardar,
                      fg_color="#27ae60").pack(pady=15)

    def _deshacer_pago(self, cr):
        conn = get_connection()
        ultimo = conn.execute(
            "SELECT id FROM pagos_creditos WHERE credito_id = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (cr["id"],),
        ).fetchone()

        if not ultimo:
            conn.close()
            win = ctk.CTkToplevel(self)
            win.title("Sin pagos")
            win.geometry("280x120")
            ctk.CTkLabel(win, text="No hay pagos para deshacer.").pack(expand=True)
            ctk.CTkButton(win, text="Cerrar", command=win.destroy).pack(pady=10)
            return

        conn.execute("DELETE FROM pagos_creditos WHERE id = ?", (ultimo["id"],))
        pagadas_actual = cr["cuotas_pagadas"] or 0
        conn.execute(
            "UPDATE creditos SET cuotas_pagadas = ? WHERE id = ?",
            (max(0, pagadas_actual - 1), cr["id"]),
        )
        if cr["prox_vencimiento"]:
            try:
                dt = datetime.strptime(cr["prox_vencimiento"], "%d/%m/%Y")
                anterior = (dt - relativedelta(months=1)).strftime("%d/%m/%Y")
                conn.execute(
                    "UPDATE creditos SET prox_vencimiento = ? WHERE id = ?",
                    (anterior, cr["id"]),
                )
            except Exception:
                pass
        conn.commit()
        conn.close()
        self._cargar_creditos()

    def _ver_historial(self, cr):
        conn = get_connection()
        pagos = conn.execute(
            "SELECT monto_real, fecha FROM pagos_creditos "
            "WHERE credito_id = ? ORDER BY fecha DESC",
            (cr["id"],),
        ).fetchall()
        conn.close()

        win = ctk.CTkToplevel(self)
        win.title(f"Historial — {cr['titular']} / {cr['banco']}")
        win.geometry("380x420")
        win.grab_set()

        ctk.CTkLabel(win, text=f"📋 {cr['titular']} — {cr['banco']}",
                     font=ctk.CTkFont(weight="bold", size=14)).pack(pady=15)

        frame = ctk.CTkScrollableFrame(win)
        frame.pack(fill="both", expand=True, padx=15, pady=5)

        hdr = ctk.CTkFrame(frame, fg_color="#1a1a2e")
        hdr.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(hdr, text="Fecha", width=160, anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=6)
        ctk.CTkLabel(hdr, text="Monto", width=160, anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=6)

        if not pagos:
            ctk.CTkLabel(frame, text="Sin pagos registrados").pack(pady=20)
        else:
            for p in pagos:
                try:
                    dt = datetime.strptime(p["fecha"], "%Y-%m-%d")
                    fecha_txt = dt.strftime("%d/%m/%Y")
                except Exception:
                    fecha_txt = p["fecha"]
                fila = ctk.CTkFrame(frame, fg_color="#1e1e1e", corner_radius=4)
                fila.pack(fill="x", pady=2)
                ctk.CTkLabel(fila, text=fecha_txt, width=160,
                             anchor="w").pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(fila, text=f"${p['monto_real']:,}", width=160,
                             anchor="w", text_color="#3498db").pack(side="left", padx=10, pady=6)

        ctk.CTkButton(win, text="Cerrar", command=win.destroy,
                      fg_color="#555").pack(pady=12)
