import customtkinter as ctk
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

    def _cargar_cuentas(self):
        headers = ["Cuenta", "Identificador", "Monto Est.", "Responsable", "Acciones"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(self.tabla, text=h,
                         font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=col, padx=15, pady=8, sticky="w")

        conn = get_connection()
        cuentas = conn.execute(
            "SELECT * FROM cuentas_fijas WHERE propiedad = 'casa_padres'"
        ).fetchall()
        conn.close()

        for row, cuenta in enumerate(cuentas, start=1):
            ctk.CTkLabel(self.tabla, text=cuenta["nombre"]).grid(
                row=row, column=0, padx=15, pady=6, sticky="w")

            entry_id = ctk.CTkEntry(self.tabla, width=130)
            entry_id.insert(0, cuenta["identificador"])
            entry_id.configure(state="readonly")
            entry_id.grid(row=row, column=1, padx=15, pady=6, sticky="w")

            ctk.CTkLabel(self.tabla, text=f"${cuenta['monto_estimado']:,}").grid(
                row=row, column=2, padx=15, pady=6, sticky="w")
            ctk.CTkLabel(self.tabla, text=cuenta["responsable"]).grid(
                row=row, column=3, padx=15, pady=6, sticky="w")
            ctk.CTkButton(self.tabla, text="Registrar Pago", width=130,
                          command=lambda c=cuenta: self._registrar_pago(c)).grid(
                row=row, column=4, padx=15, pady=6)

    def _registrar_pago(self, cuenta):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Pagar {cuenta['nombre']}")
        ventana.geometry("350x250")
        ventana.grab_set()

        ctk.CTkLabel(ventana, text=f"Registrar pago — {cuenta['nombre']}",
                     font=ctk.CTkFont(weight="bold")).pack(pady=15)

        ctk.CTkLabel(ventana, text="Monto real ($):").pack()
        entry_monto = ctk.CTkEntry(ventana, placeholder_text="ej: 35000")
        entry_monto.pack(pady=5)

        ctk.CTkLabel(ventana, text="Fecha (YYYY-MM-DD):").pack()
        entry_fecha = ctk.CTkEntry(ventana, placeholder_text="ej: 2026-07-23")
        entry_fecha.pack(pady=5)

        def guardar():
            monto = entry_monto.get()
            fecha = entry_fecha.get()
            mes = fecha[:7] if fecha else ""
            if monto and fecha:
                conn = get_connection()
                conn.execute(
                    "INSERT INTO pagos (cuenta_id, monto_real, fecha, mes) VALUES (?, ?, ?, ?)",
                    (cuenta["id"], int(monto), fecha, mes)
                )
                conn.commit()
                conn.close()
                ventana.destroy()

        ctk.CTkButton(ventana, text="Guardar", command=guardar).pack(pady=15)