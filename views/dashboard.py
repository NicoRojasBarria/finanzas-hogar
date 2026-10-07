import customtkinter as ctk
from db.database import get_connection
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from services.resumen import resumen_mes, credito_activo, nombre_mes


def _dias_hasta_str(fecha_str, formato="%d/%m/%Y"):
    try:
        dt = datetime.strptime(fecha_str, formato).date()
        return (dt - date.today()).days
    except Exception:
        return None


def _prox_vcto_desde_dia(dia):
    if not dia:
        return None, None
    hoy = date.today()
    try:
        prox = hoy.replace(day=dia)
        if prox < hoy:
            prox = (hoy.replace(day=1) + relativedelta(months=1)).replace(day=dia)
        return prox.strftime("%d/%m/%Y"), (prox - hoy).days
    except Exception:
        return None, None


def _badge_bg(color):
    """Devuelve un color de fondo oscuro compatible con tkinter (sin alpha)."""
    mapa = {
        "#f87171": "#3b1010",
        "#fbbf24": "#3b2e0a",
        "#34d399": "#0a2e1e",
        "#4a5580": "#1a1e2e",
    }
    return mapa.get(color, "#1a1a2e")


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._build()

    def _orb(self, size=13, weight="bold"):
        try:
            return ctk.CTkFont(family="Orbitron", size=size, weight=weight)
        except Exception:
            return ctk.CTkFont(size=size, weight=weight)

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        self.r = resumen_mes()

        # Título
        top = ctk.CTkFrame(scroll, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(top, text="📊 FINANZAS HOGAR",
                     font=self._orb(22), text_color="#a78bfa").pack(side="left")
        ctk.CTkLabel(top, text=date.today().strftime("%d/%m/%Y"),
                     font=self._orb(12), text_color="#7c6fe0",
                     fg_color="#16162a", corner_radius=20,
                     padx=14, pady=6).pack(side="right")

        self._panel_mes(scroll)
        self._panel_pendientes(scroll)

        mid = ctk.CTkFrame(scroll, fg_color="transparent")
        mid.pack(fill="both", expand=True, pady=10)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)

        self._panel_creditos(mid)
        self._panel_vencimientos(mid)

    # ── PANEL PRINCIPAL: ¿CÓMO VA EL MES? ────────────────────────────────
    def _panel_mes(self, parent):
        r = self.r
        panel = ctk.CTkFrame(parent, fg_color="#16162a", corner_radius=12)
        panel.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(panel, text=f"💰 ¿CÓMO VA {r['mes'].upper()}?",
                     font=self._orb(12), text_color="#7c6fe0").pack(
            anchor="w", padx=18, pady=(16, 6))

        # Resultado grande
        sobra = r["sobra"]
        if r["ingresos"] == 0:
            color, titulo = "#fbbf24", "Registrá los ingresos del mes"
            detalle = f"Sin ingresos cargados. Necesitás ${r['total_mes']:,} para cubrir {r['mes']}."
            valor = f"${r['falta']:,} por pagar"
        elif sobra >= 0:
            color, titulo = "#34d399", "TE SOBRA"
            detalle = "Después de pagar todo lo que falta del mes"
            valor = f"+${sobra:,}"
        else:
            color, titulo = "#f87171", "TE FALTA"
            detalle = "Para cubrir todo lo que falta pagar del mes"
            valor = f"-${abs(sobra):,}"

        ctk.CTkLabel(panel, text=titulo, font=self._orb(11),
                     text_color=color).pack(anchor="w", padx=18)
        ctk.CTkLabel(panel, text=valor, font=self._orb(34),
                     text_color=color).pack(anchor="w", padx=18)
        ctk.CTkLabel(panel, text=detalle, font=ctk.CTkFont(size=12),
                     text_color="#6b7299").pack(anchor="w", padx=18, pady=(0, 12))

        # Barra de progreso del mes
        total = r["total_mes"]
        pct = r["pagado"] / total if total else 1
        barra = ctk.CTkFrame(panel, fg_color="transparent")
        barra.pack(fill="x", padx=18, pady=(0, 4))
        pb = ctk.CTkProgressBar(barra, height=12, corner_radius=6,
                                progress_color="#34d399", fg_color="#1e1e38")
        pb.pack(fill="x")
        pb.set(pct)
        ctk.CTkLabel(panel,
                     text=f"Pagado ${r['pagado']:,} de ${total:,}  ({int(pct * 100)}%)",
                     font=ctk.CTkFont(size=12), text_color="#9aa3c7").pack(
            anchor="w", padx=18, pady=(2, 12))

        # La cuenta, paso a paso
        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.pack(fill="x", padx=12, pady=(0, 16))
        cajas = [
            ("INGRESOS", f"${r['ingresos']:,}", "#38bdf8", "Sueldos + Airbnb + extras"),
            ("− YA PAGADO", f"${r['pagado']:,}", "#34d399",
             f"Cuentas ${r['pagado_cuentas']:,} · Créditos ${r['pagado_creditos']:,}"),
            ("= EN MANO HOY", f"${r['disponible']:,}",
             "#cbd5e1" if r["disponible"] >= 0 else "#f87171", "Lo que te queda ahora"),
            ("− FALTA PAGAR", f"${r['falta']:,}", "#fbbf24" if r["falta"] else "#34d399",
             f"Cuentas ${r['falta_cuentas']:,} · Créditos ${r['falta_creditos']:,}"),
        ]
        for tit, val, col, sub in cajas:
            c = ctk.CTkFrame(fila, fg_color="#0f0f1c", corner_radius=8)
            c.pack(side="left", expand=True, fill="x", padx=6)
            ctk.CTkLabel(c, text=tit, font=self._orb(10),
                         text_color="#4a5580").pack(pady=(12, 4))
            ctk.CTkLabel(c, text=val, font=self._orb(17), text_color=col).pack()
            ctk.CTkLabel(c, text=sub, font=ctk.CTkFont(size=10),
                         text_color="#4a5580").pack(pady=(4, 12))

        ctk.CTkLabel(panel,
                     text=f"📅 {r['mes_prox'].capitalize()} se viene: ${r['proximo']:,} "
                          f"(cuentas ${r['proximo_cuentas']:,} + créditos ${r['proximo_creditos']:,})",
                     font=ctk.CTkFont(size=12), text_color="#6b7299").pack(
            anchor="w", padx=18, pady=(0, 14))

    # ── LO QUE FALTA PAGAR ESTE MES ──────────────────────────────────────
    def _panel_pendientes(self, parent):
        r = self.r
        panel = ctk.CTkFrame(parent, fg_color="#16162a", corner_radius=12)
        panel.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(panel, text=f"⏳ LO QUE FALTA PAGAR EN {r['mes'].upper()}",
                     font=self._orb(12), text_color="#7c6fe0").pack(
            anchor="w", padx=18, pady=(16, 8))

        if not r["pendientes"]:
            ctk.CTkLabel(panel, text="✅ Todo pagado este mes",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#34d399").pack(anchor="w", padx=18, pady=(0, 16))
            return

        hoy = date.today()
        for p in r["pendientes"]:
            f = ctk.CTkFrame(panel, fg_color="#0f0f1c", corner_radius=8)
            f.pack(fill="x", padx=14, pady=3)
            vence = p["vence"]
            if vence and vence < hoy:
                col, txt_v = "#f87171", f"venció {vence.strftime('%d/%m')}"
            elif vence:
                col, txt_v = "#fbbf24", f"vence {vence.strftime('%d/%m')}"
            else:
                col, txt_v = "#4a5580", "sin fecha"
            ctk.CTkLabel(f, text=p["nombre"], font=ctk.CTkFont(size=13, weight="bold"),
                         text_color="#cbd5e1").pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(f, text=f"· {p['tipo']}", font=ctk.CTkFont(size=11),
                         text_color="#4a5580").pack(side="left")
            monto = f"~${p['monto']:,}" if p["estimado"] else f"${p['monto']:,}"
            ctk.CTkLabel(f, text=monto, font=self._orb(12),
                         text_color="#cbd5e1").pack(side="right", padx=12)
            ctk.CTkLabel(f, text=txt_v, font=ctk.CTkFont(size=11),
                         text_color=col).pack(side="right", padx=8)
        ctk.CTkLabel(panel, text="~ = monto estimado según tus últimos pagos",
                     font=ctk.CTkFont(size=10), text_color="#4a5580").pack(
            anchor="w", padx=18, pady=(4, 14))

    # ── PANEL CRÉDITOS ────────────────────────────────────────────────────
    def _panel_creditos(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="#16162a", corner_radius=10)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(panel, text="PROGRESO CRÉDITOS",
                     font=self._orb(12), text_color="#7c6fe0").pack(
            anchor="w", padx=16, pady=(16, 12))

        conn = get_connection()
        creditos = conn.execute(
            "SELECT * FROM creditos ORDER BY titular DESC, banco"
        ).fetchall()
        conn.close()

        colores_titular = {"Nico": "#7c6fe0", "Mama": "#a78bfa", "Mamá": "#a78bfa"}

        for cr in creditos:
            f = ctk.CTkFrame(panel, fg_color="#0f0f1c", corner_radius=8)
            f.pack(fill="x", padx=14, pady=5)

            pagadas   = cr["cuotas_pagadas"] or 0
            total     = cr["cuotas_total"] or 0
            pct       = int(pagadas / total * 100) if total else 0
            restantes = max(0, total - pagadas) if total else None
            color     = colores_titular.get(cr["titular"], "#7c6fe0")
            casi_listo = restantes is not None and restantes <= 3

            if restantes == 0:
                fin_str = "TERMINADO"
            elif restantes is not None and cr["prox_vencimiento"]:
                try:
                    dt = datetime.strptime(cr["prox_vencimiento"], "%d/%m/%Y")
                    fin = dt + relativedelta(months=restantes - 1)
                    fin_str = f"{nombre_mes(fin)[:3].upper()} {fin.year}"
                except Exception:
                    fin_str = "—"
            else:
                fin_str = "PENDIENTE"

            top = ctk.CTkFrame(f, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 5))
            ctk.CTkLabel(top, text=f"{cr['titular']} — {cr['banco']}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#cbd5e1").pack(side="left")
            ctk.CTkLabel(top, text=f"${cr['cuota']:,}/mes",
                         font=self._orb(10), text_color="#4a5580").pack(side="right")

            track = ctk.CTkFrame(f, fg_color="#1e1e38", corner_radius=3, height=6)
            track.pack(fill="x", padx=12)
            track.pack_propagate(False)
            if pct > 0:
                ctk.CTkFrame(track,
                             fg_color="#34d399" if casi_listo else color,
                             corner_radius=3, height=6,
                             width=max(6, int(600 * pct / 100))
                             ).pack(side="left", fill="y")

            bot = ctk.CTkFrame(f, fg_color="transparent")
            bot.pack(fill="x", padx=12, pady=(4, 10))
            ctk.CTkLabel(bot, text=f"{pagadas} / {total if total else '?'} pagas",
                         font=ctk.CTkFont(size=12), text_color="#4a5580").pack(side="left")
            ctk.CTkLabel(bot,
                         text=f"{'🎉 ' if casi_listo else ''}Termina {fin_str}",
                         font=self._orb(10),
                         text_color="#34d399" if casi_listo else color).pack(side="right")


    # ── PANEL VENCIMIENTOS ────────────────────────────────────────────────
    def _panel_vencimientos(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="#16162a", corner_radius=10)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(panel, text="PRÓXIMOS VENCIMIENTOS",
                     font=self._orb(12), text_color="#7c6fe0").pack(
            anchor="w", padx=16, pady=(16, 12))

        conn = get_connection()
        cuentas  = conn.execute("SELECT * FROM cuentas_fijas").fetchall()
        creditos = conn.execute(
            "SELECT * FROM creditos WHERE prox_vencimiento IS NOT NULL"
        ).fetchall()
        creditos = [cr for cr in creditos if credito_activo(cr)]
        conn.close()

        items = []
        hoy = date.today()

        for c in cuentas:
            vcto, dias = _prox_vcto_desde_dia(c["dia_vencimiento"])
            if vcto and dias is not None:
                prop = "Casa" if c["propiedad"] == "casa_padres" else "Depa"
                items.append((dias, c["nombre"], vcto, prop))

        for cr in creditos:
            dias = _dias_hasta_str(cr["prox_vencimiento"])
            if dias is not None:
                items.append((dias, f"{cr['banco']} — {cr['titular']}",
                              cr["prox_vencimiento"], "Crédito"))

        items.sort(key=lambda x: x[0])

        for dias, nombre, vcto, tipo in items[:12]:
            f = ctk.CTkFrame(panel, fg_color="#0f0f1c", corner_radius=8)
            f.pack(fill="x", padx=14, pady=4)

            if dias <= 0:
                color = "#f87171"
                badge = "HOY" if dias == 0 else f"{abs(dias)}D VEN"
            elif dias <= 5:
                color = "#f87171"
                badge = f"{dias}D"
            elif dias <= 15:
                color = "#fbbf24"
                badge = f"{dias}D"
            elif dias <= 30:
                color = "#34d399"
                badge = f"{dias}D"
            else:
                color = "#4a5580"
                badge = f"{dias}D"

            left = ctk.CTkFrame(f, fg_color="transparent")
            left.pack(side="left", padx=12, pady=10)
            ctk.CTkLabel(left, text=nombre,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color="#cbd5e1", anchor="w").pack(anchor="w")
            ctk.CTkLabel(left, text=f"{vcto}  ·  {tipo}",
                         font=ctk.CTkFont(size=11), text_color="#4a5580",
                         anchor="w").pack(anchor="w")

            # Badge sin alpha — usar bg sólido
            badge_frame = ctk.CTkFrame(f, fg_color=_badge_bg(color), corner_radius=10)
            badge_frame.pack(side="right", padx=12, pady=10)
            ctk.CTkLabel(badge_frame, text=badge, font=self._orb(11),
                         text_color=color, padx=10, pady=4).pack()
