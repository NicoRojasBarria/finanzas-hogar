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
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._build()

    def _build(self):
        # Grid de 3 filas: cabecera fija | tarjetas fijas | tabla expandible
        self.grid_rowconfigure(0, weight=0)   # cabecera
        self.grid_rowconfigure(1, weight=0)   # tarjetas
        self.grid_rowconfigure(2, weight=1)   # tabla — toma todo el alto restante
        self.grid_columnconfigure(0, weight=1)

        # Encabezado
        self.cabecera = ctk.CTkFrame(self, fg_color="transparent")
        self.cabecera.grid(row=0, column=0, sticky="ew",
                           padx=(34, 30), pady=(24, 0))

        # Tarjetas resumen: se crean UNA vez y después solo se actualizan
        fila_tarjetas = ctk.CTkFrame(self, fg_color="transparent")
        fila_tarjetas.grid(row=1, column=0, sticky="ew",
                           padx=(28, 24), pady=(14, 10))
        self.tarjetas = {}
        colores = [("pagado", tema.VERDE), ("falta", tema.AMBAR),
                   ("proximo", tema.AZUL), ("deuda", tema.ROJO)]
        for i, (clave, color) in enumerate(colores):
            fila_tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjetas")
            tarjeta = ui.TarjetaResumen(fila_tarjetas, "", "", color=color)
            tarjeta.grid(row=0, column=i, sticky="ew")
            self.tarjetas[clave] = tarjeta

        # Contenedor de la tabla: ocupa toda la fila 2
        self.contenedor_tabla = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor_tabla.grid(row=2, column=0, sticky="nsew",
                                   padx=(28, 24), pady=(0, 12))
        self.contenedor_tabla.grid_rowconfigure(0, weight=1)
        self.contenedor_tabla.grid_columnconfigure(0, weight=1)

        self._cargar_creditos()

    def _cargar_creditos(self):
        # Destruir la tabla anterior completa (si existe)
        for w in self.contenedor_tabla.winfo_children():
            w.destroy()

        conn = get_connection()
        creditos = conn.execute(
            "SELECT * FROM creditos ORDER BY titular DESC, banco"
        ).fetchall()
        conn.close()

        self._actualizar_resumen(creditos)

        if not creditos:
            ctk.CTkLabel(self.contenedor_tabla, text="Sin créditos registrados",
                         font=tema.fuente(14), text_color=tema.TEXTO_SUAVE).pack(pady=40)
            return

        COLS = [
            ("Titular", 150), ("Banco", 190), ("Cuota", 170), ("Avance", 150),
            ("Próx. vencimiento", 160), ("Estado", 150), ("Acciones", 220),
        ]
        self.tabla = ui.Tabla(self.contenedor_tabla, COLS, destacada=2)
        self.tabla.grid(row=0, column=0, sticky="nsew")

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
        estado    = ("terminado" if terminado
                     else "planilla" if planilla and cr["estado"] == "al_dia"
                     else cr["estado"])
        _, color_estado = tema.estado(estado)
        problema  = estado in ("judicial", "atrasado")

        celdas, fondo = self.tabla.fila(color_estado, resaltar=problema)

        pagadas   = cr["cuotas_pagadas"] or 0
        total     = cr["cuotas_total"]   or 0
        monto_ult, fecha_ult = self._ultimo_pago(cr["id"])
        avance_sub = (f"Últ. {tema.pesos(monto_ult)}  {fecha_ult}"
                      if monto_ult else "Sin pagos")

        # Titular ────────────────────────────────────────────────────────
        titular = cr["titular"]
        ctk.CTkLabel(
            celdas[0], text=f"  {titular}",
            image=ui.avatar(titular, 34), compound="left",
            font=tema.fuente(14, "bold"),
            text_color=tema.TEXTO, anchor="w",
        ).pack(side="left")

        # Banco / número ─────────────────────────────────────────────────
        numero = cr["numero"] or "—"
        caja_banco = ui.texto_doble(celdas[1], cr["banco"], numero)
        self.after(10, lambda b=caja_banco, n=numero: self._bind_numero(b, n))

        # Cuota destacada ────────────────────────────────────────────────
        color_cuota = (tema.GRIS if terminado
                       else color_estado if problema
                       else tema.AZUL)
        sub_cuota = "pagado completo" if terminado else "mensual"
        ui.celda_destacada(celdas[2], tema.pesos(cr["cuota"]),
                           sub_cuota, color=color_cuota, fondo=fondo)

        # Avance ─────────────────────────────────────────────────────────
        color_barra = tema.GRIS if terminado else tema.AZUL
        marco_av = ctk.CTkFrame(celdas[3], fg_color="transparent")
        marco_av.pack(side="left", fill="y", pady=10)
        ui.BarraAvance(marco_av, pagadas, total,
                       color=color_barra, ancho=120).pack(anchor="w")
        ctk.CTkLabel(marco_av, text=avance_sub,
                     font=tema.fuente(11), text_color=tema.TEXTO_TENUE,
                     anchor="w").pack(anchor="w", pady=(2, 0))

        # Próx. vencimiento ──────────────────────────────────────────────
        if terminado:
            vtext, vsub, vcolor = "—", None, tema.TEXTO_TENUE
        elif planilla:
            vtext, vsub, vcolor = "Desc. por sueldo", None, tema.VIOLETA
        elif not cr["prox_vencimiento"]:
            vtext, vsub, vcolor = "—", None, tema.TEXTO_TENUE
        else:
            try:
                dt_vcto = datetime.strptime(cr["prox_vencimiento"], "%d/%m/%Y").date()
                dias    = (dt_vcto - date.today()).days
                vtext   = cr["prox_vencimiento"]
                if dias < 0:
                    vsub, vcolor = f"vencido hace {-dias}d", tema.ROJO
                elif dias == 0:
                    vsub, vcolor = "vence hoy", tema.AMBAR
                elif dias <= 5:
                    vsub, vcolor = f"en {dias} día{'s' if dias != 1 else ''}", tema.AMBAR
                else:
                    vsub, vcolor = f"en {dias} días", tema.TEXTO
            except Exception:
                vtext, vsub, vcolor = cr["prox_vencimiento"], None, tema.TEXTO
        ui.texto_doble(celdas[4], vtext, vsub, color=vcolor, fuente=tema.fuente(13))

        # Estado ─────────────────────────────────────────────────────────
        ui.Badge(celdas[5], estado, fondo=fondo).pack(side="left", pady=20)

        # Acciones ───────────────────────────────────────────────────────
        if not terminado and not planilla:
            ui.boton(celdas[6], "Pagar",
                     command=lambda c=cr: self._registrar_pago(c),
                     tipo="primario", color=tema.VERDE, ancho=84,
                     ).pack(side="left", padx=(0, 8))
        ui.boton(celdas[6], "Historial",
                 command=lambda c=cr: self._ver_historial(c),
                 tipo="secundario", color=tema.AZUL, ancho=92,
                 ).pack(side="left", padx=(0, 6))
        if not terminado:
            ui.boton(celdas[6], "↩",
                     command=lambda c=cr: self._deshacer_pago(c),
                     tipo="secundario", color=tema.TEXTO_SUAVE, ancho=40,
                     ).pack(side="left")

    def _bind_numero(self, caja_banco, numero):
        """Hace clicable el label del número de crédito (copia al portapapeles)."""
        try:
            lbl = [w for w in caja_banco.winfo_children()
                   if isinstance(w, ctk.CTkLabel)][-1]
            lbl.configure(cursor="hand2")
            lbl.bind("<Button-1>",
                     lambda e, n=numero, l=lbl: self._copiar_numero(n, l))
        except Exception:
            pass

    def _copiar_numero(self, numero, lbl):
        self.clipboard_clear()
        self.clipboard_append(numero)
        orig_text  = lbl.cget("text")
        orig_color = lbl.cget("text_color")
        lbl.configure(text="✓ Copiado", text_color=tema.VERDE)
        self.after(1400, lambda: lbl.configure(text=orig_text,
                                               text_color=orig_color))

    def _registrar_pago(self, cr):
        win = ctk.CTkToplevel(self)
        win.title(f"Pagar — {cr['titular']} / {cr['banco']}")
        win.geometry("380x340")
        win.configure(fg_color=tema.FONDO)
        win.grab_set()

        ctk.CTkLabel(win, text=f"{cr['titular']} — {cr['banco']}",
                     font=tema.fuente(14, "bold"),
                     text_color=tema.TEXTO).pack(pady=16)

        ctk.CTkLabel(win, text="Monto pagado ($):",
                     font=tema.fuente(13), text_color=tema.TEXTO_SUAVE).pack()
        entry_monto = ctk.CTkEntry(
            win, placeholder_text=tema.pesos(cr["cuota"]),
            font=tema.fuente(13), width=220,
            fg_color=tema.SUPERFICIE, border_color=tema.LINEA,
            text_color=tema.TEXTO)
        entry_monto.pack(pady=6)

        ctk.CTkLabel(win, text="Fecha (DD / MM / AAAA):",
                     font=tema.fuente(13), text_color=tema.TEXTO_SUAVE).pack()
        ff = ctk.CTkFrame(win, fg_color="transparent")
        ff.pack(pady=6)
        hoy = date.today()
        campos = []
        for ph, w, val in [("DD", 58, str(hoy.day).zfill(2)),
                            ("MM", 58, str(hoy.month).zfill(2)),
                            ("AAAA", 78, str(hoy.year))]:
            e = ctk.CTkEntry(ff, width=w, placeholder_text=ph,
                             fg_color=tema.SUPERFICIE, border_color=tema.LINEA,
                             text_color=tema.TEXTO, font=tema.fuente(13))
            e.insert(0, val)
            e.pack(side="left", padx=4)
            campos.append(e)
        e_dia, e_mes, e_anio = campos

        lbl_err = ctk.CTkLabel(win, text="", text_color=tema.ROJO,
                               font=tema.fuente(12))
        lbl_err.pack()

        def guardar():
            try:
                monto = int(entry_monto.get().replace(".", "").replace(",", ""))
                if monto <= 0:
                    raise ValueError
                fecha_iso = f"{e_anio.get()}-{e_mes.get().zfill(2)}-{e_dia.get().zfill(2)}"
                datetime.strptime(fecha_iso, "%Y-%m-%d")  # valida la fecha
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
                lbl_err.configure(text="Monto o fecha inválidos — revisa los campos")

        ui.boton(win, "Guardar", command=guardar,
                 tipo="primario", color=tema.VERDE, ancho=200).pack(pady=14)

    def _deshacer_pago(self, cr):
        conn = get_connection()
        ultimo = conn.execute(
            "SELECT id FROM pagos_creditos WHERE credito_id = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (cr["id"],),
        ).fetchone()

        if not ultimo:
            conn.close()
            win = ctk.CTkToplevel(self)
            win.configure(fg_color=tema.FONDO)
            win.title("Sin pagos")
            win.geometry("300x130")
            win.grab_set()
            ctk.CTkLabel(win, text="No hay pagos para deshacer.",
                         font=tema.fuente(13), text_color=tema.TEXTO).pack(expand=True)
            ui.boton(win, "Cerrar", command=win.destroy,
                     tipo="secundario", ancho=120).pack(pady=10)
            return

        conn.execute("DELETE FROM pagos_creditos WHERE id = ?", (ultimo["id"],))
        conn.execute(
            "UPDATE creditos SET cuotas_pagadas = MAX(0, cuotas_pagadas - 1) WHERE id = ?",
            (cr["id"],),
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
        win.geometry("400x440")
        win.configure(fg_color=tema.FONDO)
        win.grab_set()

        cab_his = ctk.CTkFrame(win, fg_color="transparent")
        cab_his.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(cab_his, image=ui.avatar(cr["titular"], 30),
                     text="").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(cab_his,
                     text=f"{cr['titular']} — {cr['banco']}",
                     font=tema.fuente(14, "bold"),
                     text_color=tema.TEXTO).pack(side="left")

        tabla_his = ui.Tabla(win, [("Fecha", 160), ("Monto", 200)], destacada=1)
        tabla_his.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        if not pagos:
            ctk.CTkLabel(tabla_his.cuerpo, text="Sin pagos registrados",
                         font=tema.fuente(13), text_color=tema.TEXTO_SUAVE).pack(pady=20)
        else:
            for p in pagos:
                try:
                    dt = datetime.strptime(p["fecha"], "%Y-%m-%d")
                    fecha_txt = dt.strftime("%d/%m/%Y")
                except Exception:
                    fecha_txt = p["fecha"]
                celdas_h, _ = tabla_his.fila()
                ctk.CTkLabel(celdas_h[0], text=fecha_txt,
                             font=tema.fuente(13), text_color=tema.TEXTO,
                             anchor="w").pack(side="left", padx=8)
                ui.celda_destacada(celdas_h[1], tema.pesos(p["monto_real"]),
                                   color=tema.AZUL)

        ui.boton(win, "Cerrar", command=win.destroy,
                 tipo="secundario", ancho=130).pack(pady=10)
