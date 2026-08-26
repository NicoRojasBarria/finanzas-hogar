import customtkinter as ctk
from db.database import get_connection
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import webbrowser


def _dias_hasta(dia_vencimiento):
    if not dia_vencimiento:
        return None
    hoy = date.today()
    try:
        prox = hoy.replace(day=dia_vencimiento)
        if prox < hoy:
            prox = (hoy.replace(day=1) + relativedelta(months=1)).replace(day=dia_vencimiento)
        return (prox - hoy).days
    except Exception:
        return None


def _prox_vcto_str(dia_vencimiento):
    if not dia_vencimiento:
        return "—"
    hoy = date.today()
    try:
        prox = hoy.replace(day=dia_vencimiento)
        if prox < hoy:
            prox = (hoy.replace(day=1) + relativedelta(months=1)).replace(day=dia_vencimiento)
        return prox.strftime("%d/%m/%Y")
    except Exception:
        return "—"


class DepartamentoView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        # Título
        ctk.CTkLabel(
            self,
            text="🏢 Departamento",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(15, 5))

        # Tarjetas de resumen
        self.resumen_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.resumen_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=("#e8e8e8", "#1a1a1a"))
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self._cargar()

    def _get_cuentas(self):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM cuentas_fijas WHERE propiedad = 'departamento' ORDER BY id"
        ).fetchall()
        conn.close()
        return rows

    def _get_ultimo_pago(self, cuenta_id):
        conn = get_connection()
        row = conn.execute(
            "SELECT monto_real, fecha FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (cuenta_id,)
        ).fetchone()
        conn.close()
        if row:
            try:
                dt = datetime.strptime(row["fecha"], "%Y-%m-%d")
                return row["monto_real"], dt.strftime("%d/%m/%Y")
            except Exception:
                return row["monto_real"], row["fecha"]
        return None, None

    def _get_historial(self, cuenta_id):
        conn = get_connection()
        rows = conn.execute(
            "SELECT monto_real, fecha FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC",
            (cuenta_id,)
        ).fetchall()
        conn.close()
        resultado = []
        for r in rows:
            try:
                dt = datetime.strptime(r["fecha"], "%Y-%m-%d")
                fecha_txt = dt.strftime("%d/%m/%Y")
            except Exception:
                fecha_txt = r["fecha"]
            resultado.append({"monto": r["monto_real"], "fecha": fecha_txt})
        return resultado

    def _cargar(self):
        # Limpiar
        for w in self.resumen_frame.winfo_children():
            w.destroy()
        for w in self.scroll.winfo_children():
            w.destroy()

        cuentas = self._get_cuentas()

        # ── TARJETAS DE RESUMEN ──────────────────────────────────────────
        total_estimado = sum(c["monto_estimado"] or 0 for c in cuentas)
        total_pagado_mes = 0
        vencidas = 0
        proximas = 0

        mes_actual = date.today().strftime("%Y-%m")
        conn = get_connection()
        for c in cuentas:
            ids = [c["id"]]
            for cid in ids:
                row = conn.execute(
                    "SELECT COALESCE(SUM(monto_real),0) as total FROM pagos "
                    "WHERE cuenta_id = ? AND mes = ?",
                    (cid, mes_actual)
                ).fetchone()
                total_pagado_mes += row["total"] if row else 0
            dias = _dias_hasta(c["dia_vencimiento"])
            if dias is not None and dias <= 0:
                vencidas += 1
            elif dias is not None and dias <= 5:
                proximas += 1
        conn.close()

        tarjetas = [
            ("💰 Total estimado/mes", f"${total_estimado:,}", "#3498db"),
            ("✅ Pagado este mes",    f"${total_pagado_mes:,}", "#2ecc71"),
            ("🔴 Cuentas vencidas",  str(vencidas),            "#e74c3c"),
            ("⚠️ Vencen pronto",     str(proximas),            "#e67e22"),
        ]

        for titulo, valor, color in tarjetas:
            card = ctk.CTkFrame(self.resumen_frame, fg_color="#1e1e2e", corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=8, pady=5)
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=11),
                         text_color="#aaaaaa").pack(pady=(12, 2))
            ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=22, weight="bold"),
                         text_color=color).pack(pady=(0, 12))

        # ── ENCABEZADOS ──────────────────────────────────────────────────
        header = ctk.CTkFrame(self.scroll, fg_color="#1a1a2e")
        header.pack(fill="x", padx=5, pady=(0, 4))
        cols = [
            ("Cuenta", 140), ("Identificador", 130),
            ("Último Pago", 100), ("Fecha Pago", 110),
            ("Próx. Estimado", 120), ("Próx. Vencimiento", 160),
            ("Link", 50), ("Acciones", 260),
        ]
        for texto, ancho in cols:
            ctk.CTkLabel(header, text=texto, font=ctk.CTkFont(weight="bold"),
                         width=ancho, anchor="w").pack(side="left", padx=6, pady=6)

        # ── FILAS ────────────────────────────────────────────────────────
        for c in cuentas:
            self._fila(c)

    def _fila(self, cuenta):
        monto_ult, fecha_ult = self._get_ultimo_pago(cuenta["id"])
        prox_vcto = _prox_vcto_str(cuenta["dia_vencimiento"])
        dias = _dias_hasta(cuenta["dia_vencimiento"])

        if dias is not None and dias <= 0:
            color_vcto = "#e74c3c"
            vcto_txt = f"{prox_vcto} ({abs(dias)}d vencido)"
            bg = "#2b0000"
        elif dias is not None and dias <= 5:
            color_vcto = "#e67e22"
            vcto_txt = f"{prox_vcto} ({dias}d)"
            bg = "#2b1a00"
        elif dias is not None:
            color_vcto = "#2ecc71"
            vcto_txt = f"{prox_vcto} ({dias}d)"
            bg = "#1e1e1e"
        else:
            color_vcto = "#aaaaaa"
            vcto_txt = "—"
            bg = "#1e1e1e"

        fila = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=6)
        fila.pack(fill="x", padx=5, pady=3)

        def celda(texto, ancho, color="#e0e0e0", bold=False):
            ctk.CTkLabel(fila, text=str(texto),
                         font=ctk.CTkFont(weight="bold" if bold else "normal"),
                         width=ancho, anchor="w", text_color=color).pack(side="left", padx=6, pady=8)

        celda(cuenta["nombre"],                          140)
        celda(cuenta["identificador"] or "—",            130, "#aaaaaa")
        celda(f"${monto_ult:,}" if monto_ult else "Sin pagos", 100)
        celda(fecha_ult or "—",                          110)
        celda(f"${cuenta['monto_estimado']:,}" if cuenta["monto_estimado"] else "—", 120, "#3498db")
        celda(vcto_txt,                                  160, color_vcto)

        # Botón link
        if cuenta["url_pago"]:
            ctk.CTkButton(
                fila, text="🌐", width=44, height=30,
                fg_color="#1a3a5c", hover_color="#1a5276",
                command=lambda u=cuenta["url_pago"]: webbrowser.open(u)
            ).pack(side="left", padx=4, pady=6)
        else:
            ctk.CTkLabel(fila, text="", width=44).pack(side="left", padx=4)

        # Botones acción
        btns = ctk.CTkFrame(fila, fg_color="transparent")
        btns.pack(side="left", padx=4)

        ctk.CTkButton(
            btns, text="💰 Pagar", width=85,
            fg_color="#27ae60", hover_color="#1e8449",
            command=lambda c=cuenta: self._pagar(c)
        ).pack(side="left", padx=2, pady=6)

        ctk.CTkButton(
            btns, text="📋 Historial", width=95,
            fg_color="#2980b9", hover_color="#1a6fa1",
            command=lambda c=cuenta: self._historial(c)
        ).pack(side="left", padx=2, pady=6)

        ctk.CTkButton(
            btns, text="↩", width=36, height=36,
            corner_radius=18,
            fg_color="#555", hover_color="#333",
            font=ctk.CTkFont(size=16),
            command=lambda c=cuenta: self._deshacer(c)
        ).pack(side="left", padx=2, pady=6)

    def _pagar(self, cuenta):
        win = ctk.CTkToplevel(self)
        win.title(f"Pagar — {cuenta['nombre']}")
        win.geometry("360x300")
        win.grab_set()

        ctk.CTkLabel(win, text=cuenta["nombre"],
                     font=ctk.CTkFont(weight="bold", size=14)).pack(pady=15)

        ctk.CTkLabel(win, text="Monto pagado ($):").pack()
        entry_monto = ctk.CTkEntry(
            win, placeholder_text=f"ej: {cuenta['monto_estimado']:,}" if cuenta["monto_estimado"] else "ej: 50000"
        )
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
                mes_str = f"{e_anio.get()}-{e_mes.get().zfill(2)}"
                conn = get_connection()
                conn.execute(
                    "INSERT INTO pagos (cuenta_id, monto_real, fecha, mes) VALUES (?, ?, ?, ?)",
                    (cuenta["id"], monto, fecha_iso, mes_str)
                )
                conn.commit()
                conn.close()
                win.destroy()
                self._cargar()
            except ValueError:
                lbl_err.configure(text="Monto inválido — solo números")

        ctk.CTkButton(win, text="Guardar", command=guardar,
                      fg_color="#27ae60").pack(pady=15)

    def _deshacer(self, cuenta):
        conn = get_connection()
        ultimo = conn.execute(
            "SELECT id FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (cuenta["id"],)
        ).fetchone()
        if ultimo:
            conn.execute("DELETE FROM pagos WHERE id = ?", (ultimo["id"],))
            conn.commit()
        conn.close()
        self._cargar()

    def _historial(self, cuenta):
        pagos = self._get_historial(cuenta["id"])
        win = ctk.CTkToplevel(self)
        win.title(f"Historial — {cuenta['nombre']}")
        win.geometry("380x420")
        win.grab_set()

        ctk.CTkLabel(win, text=f"📋 {cuenta['nombre']}",
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
                fila = ctk.CTkFrame(frame, fg_color="#1e1e1e", corner_radius=4)
                fila.pack(fill="x", pady=2)
                ctk.CTkLabel(fila, text=p["fecha"], width=160,
                             anchor="w").pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(fila, text=f"${p['monto']:,}", width=160,
                             anchor="w", text_color="#3498db").pack(side="left", padx=10, pady=6)

        ctk.CTkButton(win, text="Cerrar", command=win.destroy,
                      fg_color="#555").pack(pady=12)
