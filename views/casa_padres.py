import customtkinter as ctk
import webbrowser
from datetime import date
from dateutil.relativedelta import relativedelta
from db.database import get_connection


class CasaPadresView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="🏠 Casa Padres",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(15, 5))

        # Tarjetas resumen
        self.resumen_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.resumen_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.tabla = ctk.CTkScrollableFrame(self, fg_color=("#e8e8e8", "#1a1a1a"))
        self.tabla.pack(fill="both", expand=True, padx=10, pady=5)

        self._cargar_cuentas()

    def _refrescar(self):
        for w in self.resumen_frame.winfo_children():
            w.destroy()
        for w in self.tabla.winfo_children():
            w.destroy()
        self._cargar_cuentas()

    def _calcular_estimado(self, conn, cuenta_id, monto_base):
        pagos = conn.execute(
            "SELECT monto_real FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC LIMIT 3",
            (cuenta_id,)
        ).fetchall()
        if not pagos:
            return monto_base
        elif len(pagos) < 3:
            return pagos[0]["monto_real"]
        else:
            return sum(p["monto_real"] for p in pagos) // len(pagos)

    def _cargar_cuentas(self):
        conn = get_connection()
        cuentas = conn.execute(
            "SELECT * FROM cuentas_fijas WHERE propiedad = 'casa_padres'"
        ).fetchall()
        hoy = date.today()
        mes_actual = hoy.strftime("%Y-%m")

        # ── TARJETAS RESUMEN ────────────────────────────────────────────
        total_estimado = sum(c["monto_estimado"] or 0 for c in cuentas)
        total_pagado_mes = 0
        vencidas = 0
        proximas = 0

        for c in cuentas:
            row = conn.execute(
                "SELECT COALESCE(SUM(monto_real),0) as total FROM pagos WHERE cuenta_id = ? AND mes = ?",
                (c["id"], mes_actual)
            ).fetchone()
            total_pagado_mes += row["total"] if row else 0

            dia = c["dia_vencimiento"]
            if dia:
                try:
                    venc = hoy.replace(day=dia)
                    if venc < hoy:
                        venc = (hoy.replace(day=1) + relativedelta(months=1)).replace(day=dia)
                    dias = (venc - hoy).days
                    if dias <= 0:
                        vencidas += 1
                    elif dias <= 5:
                        proximas += 1
                except Exception:
                    pass

        tarjetas = [
            ("💰 Total estimado/mes", f"${total_estimado:,}",   "#3498db"),
            ("✅ Pagado este mes",    f"${total_pagado_mes:,}", "#2ecc71"),
            ("🔴 Cuentas vencidas",  str(vencidas),             "#e74c3c"),
            ("⚠️ Vencen pronto",     str(proximas),             "#e67e22"),
        ]
        for titulo, valor, color in tarjetas:
            card = ctk.CTkFrame(self.resumen_frame, fg_color="#1e1e2e", corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=8, pady=5)
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=11),
                         text_color="#aaaaaa").pack(pady=(12, 2))
            ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=22, weight="bold"),
                         text_color=color).pack(pady=(0, 12))

        # ── ENCABEZADOS ─────────────────────────────────────────────────
        header = ctk.CTkFrame(self.tabla, fg_color="#1a1a2e")
        header.pack(fill="x", padx=5, pady=(0, 4))
        cols = [
            ("Cuenta", 140), ("Identificador", 130), ("Último Pago", 100),
            ("Fecha Pago", 110), ("Próx. Estimado", 120), ("Próx. Vencimiento", 160),
            ("Link", 50), ("Acciones", 270),
        ]
        for texto, ancho in cols:
            ctk.CTkLabel(header, text=texto, font=ctk.CTkFont(weight="bold"),
                         width=ancho, anchor="w").pack(side="left", padx=6, pady=6)

        # ── FILAS ────────────────────────────────────────────────────────
        for cuenta in cuentas:
            ultimo = conn.execute(
                "SELECT monto_real, fecha FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC LIMIT 1",
                (cuenta["id"],)
            ).fetchone()

            if ultimo:
                monto_txt = f"${ultimo['monto_real']:,}"
                partes = ultimo["fecha"].split("-")
                fecha_txt = f"{partes[2]}/{partes[1]}/{partes[0]}"
            else:
                monto_txt = "Sin pagos"
                fecha_txt = "—"

            estimado = self._calcular_estimado(conn, cuenta["id"], cuenta["monto_estimado"])
            estimado_txt = f"${estimado:,}" if estimado else "—"

            dia = cuenta["dia_vencimiento"]
            if dia:
                try:
                    venc = hoy.replace(day=dia)
                    if venc < hoy:
                        venc = (hoy.replace(day=1) + relativedelta(months=1)).replace(day=dia)
                    dias_restantes = (venc - hoy).days
                    color_v = "#e74c3c" if dias_restantes <= 0 else "#e67e22" if dias_restantes <= 5 else "#2ecc71"
                    venc_txt = f"{venc.strftime('%d/%m/%Y')} ({dias_restantes}d)"
                except Exception:
                    color_v = "#aaaaaa"
                    venc_txt = "—"
            else:
                color_v = "#aaaaaa"
                venc_txt = "—"

            fila = ctk.CTkFrame(self.tabla, fg_color="#1e1e1e", corner_radius=6)
            fila.pack(fill="x", padx=5, pady=3)

            def celda(texto, ancho, color="#e0e0e0", bold=False):
                ctk.CTkLabel(fila, text=str(texto),
                             font=ctk.CTkFont(weight="bold" if bold else "normal"),
                             width=ancho, anchor="w", text_color=color).pack(side="left", padx=6, pady=8)

            celda(cuenta["nombre"],    140)

            entry_id = ctk.CTkEntry(fila, width=120)
            entry_id.insert(0, cuenta["identificador"] or "")
            entry_id.configure(state="readonly")
            entry_id.pack(side="left", padx=6, pady=8)

            celda(monto_txt,           100)
            celda(fecha_txt,           110)
            ctk.CTkLabel(fila, text=estimado_txt, width=120, anchor="w",
                         text_color="#3498db").pack(side="left", padx=6, pady=8)
            ctk.CTkLabel(fila, text=venc_txt, width=160, anchor="w",
                         text_color=color_v).pack(side="left", padx=6, pady=8)

            if cuenta["url_pago"]:
                ctk.CTkButton(fila, text="🌐", width=44, height=30,
                              fg_color="#1a3a5c", hover_color="#1a5276",
                              command=lambda u=cuenta["url_pago"]: webbrowser.open(u)
                              ).pack(side="left", padx=4, pady=6)
            else:
                ctk.CTkLabel(fila, text="", width=44).pack(side="left", padx=4)

            btns = ctk.CTkFrame(fila, fg_color="transparent")
            btns.pack(side="left", padx=4)

            ctk.CTkButton(btns, text="💰 Pagar", width=85,
                          fg_color="#27ae60", hover_color="#1e8449",
                          command=lambda c=cuenta: self._registrar_pago(c)
                          ).pack(side="left", padx=2, pady=6)

            ctk.CTkButton(btns, text="📋 Historial", width=95,
                          fg_color="#2980b9", hover_color="#1a6fa1",
                          command=lambda c=cuenta: self._ver_historial(c)
                          ).pack(side="left", padx=2, pady=6)

            ctk.CTkButton(btns, text="↩", width=36, height=36,
                          corner_radius=18, fg_color="#555", hover_color="#333",
                          font=ctk.CTkFont(size=16),
                          command=lambda c=cuenta: self._deshacer_pago(c)
                          ).pack(side="left", padx=2, pady=6)

        conn.close()

    def _deshacer_pago(self, cuenta):
        conn = get_connection()
        ultimo = conn.execute(
            "SELECT id FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (cuenta["id"],)
        ).fetchone()
        if ultimo:
            conn.execute("DELETE FROM pagos WHERE id = ?", (ultimo["id"],))
            conn.commit()
        conn.close()
        self._refrescar()

    def _ver_historial(self, cuenta):
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

        conn = get_connection()
        pagos = conn.execute(
            "SELECT monto_real, fecha FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC",
            (cuenta["id"],)
        ).fetchall()
        conn.close()

        if not pagos:
            ctk.CTkLabel(frame, text="Sin pagos registrados").pack(pady=20)
        else:
            for p in pagos:
                partes = p["fecha"].split("-")
                fecha_txt = f"{partes[2]}/{partes[1]}/{partes[0]}"
                fila = ctk.CTkFrame(frame, fg_color="#1e1e1e", corner_radius=4)
                fila.pack(fill="x", pady=2)
                ctk.CTkLabel(fila, text=fecha_txt, width=160,
                             anchor="w").pack(side="left", padx=10, pady=6)
                ctk.CTkLabel(fila, text=f"${p['monto_real']:,}", width=160,
                             anchor="w", text_color="#3498db").pack(side="left", padx=10, pady=6)

        ctk.CTkButton(win, text="Cerrar", command=win.destroy,
                      fg_color="#555").pack(pady=12)

    def _registrar_pago(self, cuenta):
        win = ctk.CTkToplevel(self)
        win.title(f"Pagar {cuenta['nombre']}")
        win.geometry("350x300")
        win.grab_set()

        ctk.CTkLabel(win, text=f"💰 {cuenta['nombre']}",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=15)

        ctk.CTkLabel(win, text="Monto real ($):").pack()
        entry_monto = ctk.CTkEntry(win, placeholder_text="ej: 79838")
        entry_monto.pack(pady=5)

        ctk.CTkLabel(win, text="Fecha:").pack()
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
            monto_raw = entry_monto.get().replace(".", "").replace(",", "")
            dia = e_dia.get().zfill(2)
            mes = e_mes.get().zfill(2)
            anio = e_anio.get()
            if not monto_raw.isdigit():
                lbl_err.configure(text="⚠ Solo números, sin puntos")
                return
            fecha_iso = f"{anio}-{mes}-{dia}"
            mes_iso = f"{anio}-{mes}"
            conn = get_connection()
            conn.execute(
                "INSERT INTO pagos (cuenta_id, monto_real, fecha, mes) VALUES (?, ?, ?, ?)",
                (cuenta["id"], int(monto_raw), fecha_iso, mes_iso)
            )
            conn.commit()
            conn.close()
            win.destroy()
            self._refrescar()

        ctk.CTkButton(win, text="Guardar", command=guardar,
                      fg_color="#27ae60").pack(pady=15)
