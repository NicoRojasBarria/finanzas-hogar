"""Vista previa del rediseño con datos de ejemplo.

No lee ni modifica finanzas.db. Ejecutar con:
    python demo_rediseno.py
"""
from datetime import date, datetime

import customtkinter as ctk

from views import tema
from views import componentes as ui

HOY = date(2026, 10, 6)

CREDITOS = [
    # titular, banco, numero, cuota, pagadas, total, vencimiento, estado
    ("Nico", "Duoc UC",        "DUOC-2026",     307000,  1,  5, "18/10/2026", "al_dia"),
    ("Nico", "Santander",      "00038587262",   143565, 12, 30, "05/10/2026", "judicial"),
    ("Nico", "Santander",      "00032939954",   118764,  9, 30, "05/10/2026", "judicial"),
    ("Mamá", "Banco de Chile", "BDC-MAMA-001",  432143,  5, 36, "10/10/2026", "al_dia"),
    ("Mamá", "Coopeuch",       "COOPEUCH",      237280, 19, 30, None,         "planilla"),
    ("Mamá", "BancoEstado",    "BE-00271",       99372, 15, 24, "10/10/2026", "atrasado"),
    ("Mamá", "BancoEstado",    "BE-00118",       66140, 22, 22, None,         "terminado"),
]

COLUMNAS = [
    ("Titular", 150), ("Banco", 190), ("Cuota", 170), ("Avance", 150),
    ("Próx. vencimiento", 160), ("Estado", 150), ("Acciones", 210),
]


def _dias(fecha):
    if not fecha:
        return None
    return (datetime.strptime(fecha, "%d/%m/%Y").date() - HOY).days


def _texto_vencimiento(fecha, estado):
    if estado == "planilla":
        return "Desc. por sueldo", None, tema.VIOLETA
    if estado == "terminado" or not fecha:
        return "—", None, tema.TEXTO_TENUE
    d = _dias(fecha)
    if d < 0:
        return fecha, f"vencido hace {-d} día{'s' if d < -1 else ''}", tema.ROJO
    if d == 0:
        return fecha, "vence hoy", tema.AMBAR
    return fecha, f"en {d} día{'s' if d > 1 else ''}", tema.TEXTO if d > 5 else tema.AMBAR


class Demo(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=tema.FONDO)
        tema.cargar_fuentes()
        self.title("Finanzas Hogar")
        self.geometry("1600x900")
        self.minsize(1300, 700)

        ui.BarraLateral(self, [
            ("Casa padres", None), ("Departamento", None), ("Créditos", None),
            ("Ingresos", None), ("Dashboard", None),
        ], activo="Créditos").pack(side="left", fill="y")

        principal = ctk.CTkFrame(self, fg_color=tema.FONDO, corner_radius=0)
        principal.pack(side="left", fill="both", expand=True, padx=(28, 24), pady=(24, 16))

        # Encabezado
        cab = ctk.CTkFrame(principal, fg_color="transparent")
        cab.pack(fill="x", padx=6)
        ui.titulo_seccion(cab, "Créditos", "Octubre 2026, 6 créditos activos").pack(side="left")
        ui.boton(cab, "+ Nuevo crédito", tipo="secundario", color=tema.VIOLETA,
                 ancho=150).pack(side="right", pady=8)

        # Tarjetas
        tarjetas = ctk.CTkFrame(principal, fg_color="transparent")
        tarjetas.pack(fill="x", pady=(14, 10))
        datos = [
            ("Pagado en octubre",  tema.pesos(739143),   "2 cuotas registradas", tema.VERDE,
             [3, 4, 3.5, 5, 4.8, 6, 6.5, 8]),
            ("Falta pagar",        tema.pesos(668701),   "4 cuotas pendientes",  tema.AMBAR,
             [6, 5.5, 6.2, 5, 5.4, 4.6, 4.9, 4]),
            ("Vence en noviembre", tema.pesos(1100844),  "5 cuotas",             tema.AZUL,
             [4, 4.4, 4.1, 5, 4.7, 5.3, 5.1, 5.6]),
            ("Deuda restante",     tema.pesos(23206277), "2 en judicial, 1 atrasado", tema.ROJO,
             [9, 8.6, 8.8, 8.1, 7.9, 7.4, 7.5, 7]),
        ]
        for i, (t, v, d, c, serie) in enumerate(datos):
            tarjetas.grid_columnconfigure(i, weight=1, uniform="t")
            ui.TarjetaResumen(tarjetas, t, v, d, c, serie).grid(row=0, column=i, sticky="ew")

        # Tabla
        tabla = ui.Tabla(principal, COLUMNAS, destacada=2)
        tabla.pack(fill="both", expand=True, padx=6, pady=(6, 0))

        for titular, banco, numero, cuota, pagadas, total, vcto, estado in CREDITOS:
            _, color = tema.estado(estado)
            problema = estado in ("judicial", "atrasado")
            celdas, fondo = tabla.fila(color, resaltar=problema)

            # Titular
            ctk.CTkLabel(celdas[0], text=f"  {titular}", image=ui.avatar(titular, 34),
                         compound="left", font=tema.fuente(14, "bold"),
                         text_color=tema.TEXTO, anchor="w").pack(side="left")
            # Banco
            ui.texto_doble(celdas[1], banco, numero)
            # Cuota
            terminado = estado == "terminado"
            color_cuota = tema.GRIS if terminado else (color if problema else tema.AZUL)
            ui.celda_destacada(celdas[2], tema.pesos(cuota),
                               "mensual" if not terminado else "pagado completo",
                               color=color_cuota, fondo=fondo)
            # Avance
            ui.BarraAvance(celdas[3], pagadas, total,
                           color=tema.GRIS if terminado else tema.AZUL).pack(side="left", pady=14)
            # Vencimiento
            principal_v, sub_v, color_v = _texto_vencimiento(vcto, estado)
            ui.texto_doble(celdas[4], principal_v, sub_v, color=color_v,
                           fuente=tema.fuente(14))
            # Estado
            ui.Badge(celdas[5], estado, fondo=fondo).pack(side="left", pady=20)
            # Acciones
            if not terminado and estado != "planilla":
                ui.boton(celdas[6], "Pagar").pack(side="left", padx=(0, 8))
            ui.boton(celdas[6], "Historial", tipo="secundario").pack(side="left")


if __name__ == "__main__":
    Demo().mainloop()
