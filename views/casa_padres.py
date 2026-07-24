import customtkinter as ctk
import webbrowser
from datetime import date
from db.database import get_connection

class CasaPadresView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🏠 Casa Padres",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)

        self.tabla = ctk.CTkScrollableFrame(self)
        self.tabla.pack(fill="both", expand=True, padx=20, pady=10)

        self._cargar_cuentas()

    def _refrescar(self):
        for widget in self.tabla.winfo_children():
            widget.destroy()
        self._cargar_cuentas()

    def _cargar_cuentas(self):
        headers = ["Cuenta", "Identificador", "Último Pago", "Fecha Pago", "Próx. Vencimiento", "Link", "Acciones"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(self.tabla, text=h,
                         font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=col, padx=12, pady=8, sticky="w")

        conn = get_connection()
        cuentas = conn.execute(
            "SELECT * FROM cuentas_fijas WHERE propiedad = 'casa_padres'"
        ).fetchall()

        hoy = date.today()

        for row, cuenta in enumerate(cuentas, start=1):
            ultimo = conn.execute(
                "SELECT monto_real, fecha FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC LIMIT 1",
                (cuenta["id"],)
            ).fetchone()

            ctk.CTkLabel(self.tabla, text=cuenta["nombre"]).grid(
                row=row, column=0, padx=12, pady=6, sticky="w")

            entry_id = ctk.CTkEntry(self.tabla, width=120)
            entry_id.insert(0, cuenta["identificador"])
            entry_id.configure(state="readonly")
            entry_id.grid(row=row, column=1, padx=12, pady=6, sticky="w")

            if ultimo:
                monto_txt = f"${ultimo['monto_real']:,}"
                partes = ultimo["fecha"].split("-")
                fecha_txt = f"{partes[2]}/{partes[1]}/{partes[0]}"
            else:
                monto_txt = "Sin pagos"
                fecha_txt = "—"

            ctk.CTkLabel(self.tabla, text=monto_txt).grid(
                row=row, column=2, padx=12, pady=6, sticky="w")
            ctk.CTkLabel(self.tabla, text=fecha_txt).grid(
                row=row, column=3, padx=12, pady=6, sticky="w")

            dia = cuenta["dia_vencimiento"]
            if dia:
                try:
                    venc = date(hoy.year, hoy.month, dia)
                    if venc < hoy:
                        if hoy.month == 12:
                            venc = date(hoy.year + 1, 1, dia)
                        else:
                            venc = date(hoy.year, hoy.month + 1, dia)
                    dias_restantes = (venc - hoy).days
                    if dias_restantes <= 3:
                        color = "#e63946"
                    elif dias_restantes <= 7:
                        color = "#f4a261"
                    else:
                        color = "#ffffff"
                    venc_txt = f"{venc.strftime('%d/%m/%Y')} ({dias_restantes}d)"
                    ctk.CTkLabel(self.tabla, text=venc_txt, text_color=color).grid(
                        row=row, column=4, padx=12, pady=6, sticky="w")
                except:
                    ctk.CTkLabel(self.tabla, text="—").grid(
                        row=row, column=4, padx=12, pady=6, sticky="w")
            else:
                ctk.CTkLabel(self.tabla, text="—").grid(
                    row=row, column=4, padx=12, pady=6, sticky="w")

            if cuenta["url_pago"]:
                ctk.CTkButton(self.tabla, text="🌐", width=35,
                              command=lambda u=cuenta["url_pago"]: webbrowser.open(u)).grid(
                    row=row, column=5, padx=5, pady=6)

            frame_acc = ctk.CTkFrame(self.tabla, fg_color="transparent")
            frame_acc.grid(row=row, column=6, padx=12, pady=6)

            ctk.CTkButton(frame_acc, text="Registrar Pago", width=120,
                          command=lambda c=cuenta: self._registrar_pago(c)).pack(side="left", padx=4)
            ctk.CTkButton(frame_acc, text="📋 Historial", width=110, fg_color="#2d6a4f",
                          command=lambda c=cuenta: self._ver_historial(c)).pack(side="left", padx=4)

        conn.close()

    def _ver_historial(self, cuenta):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Historial — {cuenta['nombre']}")
        ventana.geometry("400x350")
        ventana.grab_set()

        ctk.CTkLabel(ventana, text=f"📋 Historial de {cuenta['nombre']}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        frame = ctk.CTkScrollableFrame(ventana)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        for col, h in enumerate(["Fecha", "Monto"]):
            ctk.CTkLabel(frame, text=h,
                         font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=20, pady=6)

        conn = get_connection()
        pagos = conn.execute(
            "SELECT monto_real, fecha FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC",
            (cuenta["id"],)
        ).fetchall()
        conn.close()

        if not pagos:
            ctk.CTkLabel(frame, text="Sin pagos registrados").grid(row=1, column=0, columnspan=2, pady=20)
        else:
            for i, pago in enumerate(pagos, start=1):
                partes = pago["fecha"].split("-")
                fecha_txt = f"{partes[2]}/{partes[1]}/{partes[0]}"
                ctk.CTkLabel(frame, text=fecha_txt).grid(row=i, column=0, padx=20, pady=4)
                ctk.CTkLabel(frame, text=f"${pago['monto_real']:,}").grid(row=i, column=1, padx=20, pady=4)

    def _registrar_pago(self, cuenta):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Pagar {cuenta['nombre']}")
        ventana.geometry("350x300")
        ventana.grab_set()

        ctk.CTkLabel(ventana, text=f"Registrar pago — {cuenta['nombre']}",
                     font=ctk.CTkFont(weight="bold")).pack(pady=15)

        ctk.CTkLabel(ventana, text="Monto real ($):").pack()
        entry_monto = ctk.CTkEntry(ventana, placeholder_text="ej: 35000")
        entry_monto.pack(pady=5)

        ctk.CTkLabel(ventana, text="Fecha:").pack()
        fecha_frame = ctk.CTkFrame(ventana, fg_color="transparent")
        fecha_frame.pack(pady=5)

        hoy = date.today()

        entry_dia = ctk.CTkEntry(fecha_frame, width=55, placeholder_text="DD")
        entry_dia.insert(0, str(hoy.day).zfill(2))
        entry_dia.pack(side="left", padx=4)

        entry_mes = ctk.CTkEntry(fecha_frame, width=55, placeholder_text="MM")
        entry_mes.insert(0, str(hoy.month).zfill(2))
        entry_mes.pack(side="left", padx=4)

        entry_año = ctk.CTkEntry(fecha_frame, width=75, placeholder_text="AAAA")
        entry_año.insert(0, str(hoy.year))
        entry_año.pack(side="left", padx=4)

        def guardar():
            monto = entry_monto.get()
            dia = entry_dia.get().zfill(2)
            mes = entry_mes.get().zfill(2)
            año = entry_año.get()
            if monto and dia and mes and año:
                fecha_iso = f"{año}-{mes}-{dia}"
                mes_iso = f"{año}-{mes}"
                conn = get_connection()
                conn.execute(
                    "INSERT INTO pagos (cuenta_id, monto_real, fecha, mes) VALUES (?, ?, ?, ?)",
                    (cuenta["id"], int(monto), fecha_iso, mes_iso)
                )
                conn.commit()
                conn.close()
                ventana.destroy()
                self._refrescar()

        ctk.CTkButton(ventana, text="Guardar", command=guardar).pack(pady=15)