import customtkinter as ctk
from db.database import get_connection
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import os


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

        # ── TÍTULO ───────────────────────────────────────────────────────
        top = ctk.CTkFrame(scroll, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(top, text="📊 FINANZAS HOGAR",
                     font=self._orb(22), text_color="#a78bfa").pack(side="left")
        ctk.CTkLabel(top, text=date.today().strftime("%d %b %Y").upper(),
                     font=self._orb(12), text_color="#7c6fe0",
                     fg_color="#16162a", corner_radius=20,
                     padx=14, pady=6).pack(side="right")

        # ── TARJETAS ─────────────────────────────────────────────────────
        self._tarjetas(scroll)

        # ── CENTRO ───────────────────────────────────────────────────────
        mid = ctk.CTkFrame(scroll, fg_color="transparent")
        mid.pack(fill="both", expand=True, pady=10)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)

        self._panel_creditos(mid)
        self._panel_vencimientos(mid)

    # ── TARJETAS ─────────────────────────────────────────────────────────
    def _tarjetas(self, parent):
        conn = get_connection()
        mes_actual = date.today().strftime("%Y-%m")

        total_est = conn.execute(
            "SELECT COALESCE(SUM(monto_estimado),0) as t FROM cuentas_fijas"
        ).fetchone()["t"]
        total_creditos = conn.execute(
            "SELECT COALESCE(SUM(cuota),0) as t FROM creditos"
        ).fetchone()["t"]
        total_mes = total_est + total_creditos + 307000

        pagado = conn.execute(
            "SELECT COALESCE(SUM(monto_real),0) as t FROM pagos WHERE mes = ?",
            (mes_actual,)
        ).fetchone()["t"]
        pagado_cred = conn.execute(
            "SELECT COALESCE(SUM(monto_real),0) as t FROM pagos_creditos "
            "WHERE strftime('%Y-%m', fecha) = ?", (mes_actual,)
        ).fetchone()["t"]
        total_pagado = pagado + pagado_cred

        cuentas = conn.execute("SELECT * FROM cuentas_fijas").fetchall()
        vencidas = 0
        for c in cuentas:
            _, dias = _prox_vcto_desde_dia(c["dia_vencimiento"])
            if dias is not None and dias <= 0:
                vencidas += 1
        hoy = date.today()
        if hoy.day >= 25:
            vencidas += 1

        deuda = conn.execute(
            "SELECT COALESCE(SUM(cuota * MAX(0, COALESCE(cuotas_total,0) - COALESCE(cuotas_pagadas,0))),0) as t "
            "FROM creditos WHERE cuotas_total IS NOT NULL"
        ).fetchone()["t"]
        conn.close()

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 10))

        pct = int(total_pagado / total_mes * 100) if total_mes else 0
        datos = [
            ("GASTO TOTAL MES", f"${total_mes:,}",    "#a78bfa", "Casa + Depa + Créditos + DUOC"),
            ("PAGADO ESTE MES", f"${total_pagado:,}", "#34d399", f"{pct}% del total"),
            ("VENCEN HOY",      str(vencidas),         "#f87171", "Revisar urgente"),
            ("DEUDA CRÉDITOS",  f"${deuda:,}",         "#fbbf24", "5 créditos activos"),
        ]

        for titulo, valor, color, sub in datos:
            card = ctk.CTkFrame(frame, fg_color="#16162a", corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=6)
            ctk.CTkLabel(card, text=titulo, font=self._orb(10),
                         text_color="#4a5580").pack(pady=(16, 4))
            ctk.CTkLabel(card, text=valor, font=self._orb(20),
                         text_color=color).pack()
            ctk.CTkLabel(card, text=sub, font=ctk.CTkFont(size=12),
                         text_color="#4a5580").pack(pady=(4, 16))

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

        colores_titular = {"Nico": "#7c6fe0", "Mama": "#a78bfa"}

        for cr in creditos:
            f = ctk.CTkFrame(panel, fg_color="#0f0f1c", corner_radius=8)
            f.pack(fill="x", padx=14, pady=5)

            pagadas  = cr["cuotas_pagadas"] or 0
            total    = cr["cuotas_total"] or 0
            pct      = int(pagadas / total * 100) if total else 0
            restantes = max(0, total - pagadas) if total else None
            color    = colores_titular.get(cr["titular"], "#7c6fe0")

            # Fecha fin estimada
            if restantes is not None and cr["prox_vencimiento"]:
                try:
                    dt = datetime.strptime(cr["prox_vencimiento"], "%d/%m/%Y")
                    fin = dt + relativedelta(months=restantes)
                    fin_str = fin.strftime("%b %Y").upper()
                except Exception:
                    fin_str = "—"
            else:
                fin_str = "PENDIENTE"

            casi_listo = restantes is not None and restantes <= 3

            # Encabezado
            top = ctk.CTkFrame(f, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 5))
            ctk.CTkLabel(top,
                         text=f"{cr['titular']} — {cr['banco']}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#cbd5e1").pack(side="left")
            ctk.CTkLabel(top,
                         text=f"${cr['cuota']:,}/mes",
                         font=self._orb(10), text_color="#4a5580").pack(side="right")

            # Barra progreso
            track = ctk.CTkFrame(f, fg_color="#1e1e38", corner_radius=3, height=6)
            track.pack(fill="x", padx=12)
            track.pack_propagate(False)
            if pct > 0:
                ctk.CTkFrame(track, fg_color="#34d399" if casi_listo else color,
                             corner_radius=3, height=6,
                             width=max(6, int(800 * pct / 100))
                             ).pack(side="left", fill="y")

            # Pie
            bot = ctk.CTkFrame(f, fg_color="transparent")
            bot.pack(fill="x", padx=12, pady=(4, 10))
            ctk.CTkLabel(bot,
                         text=f"{pagadas} / {total if total else '?'} pagas",
                         font=ctk.CTkFont(size=12), text_color="#4a5580").pack(side="left")
            ctk.CTkLabel(bot,
                         text=f"{'🎉 ' if casi_listo else ''}Termina {fin_str}",
                         font=self._orb(10),
                         text_color="#34d399" if casi_listo else color).pack(side="right")

        # DUOC
        f = ctk.CTkFrame(panel, fg_color="#0f0f1c", corner_radius=8)
        f.pack(fill="x", padx=14, pady=(8, 14))
        ctk.CTkFrame(f, fg_color="#a78bfa", height=2, corner_radius=0).pack(fill="x")

        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 5))
        ctk.CTkLabel(top, text="Nico — DUOC UC",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#cbd5e1").pack(side="left")
        ctk.CTkLabel(top, text="$307.000/mes",
                     font=self._orb(10), text_color="#4a5580").pack(side="right")

        track = ctk.CTkFrame(f, fg_color="#1e1e38", corner_radius=3, height=6)
        track.pack(fill="x", padx=12)
        track.pack_propagate(False)
        ctk.CTkFrame(track, fg_color="#a78bfa", corner_radius=3, height=6,
                     width=400).pack(side="left", fill="y")

        bot = ctk.CTkFrame(f, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(bot, text="5 / 10 pagas (Mar–Dic)",
                     font=ctk.CTkFont(size=12), text_color="#4a5580").pack(side="left")
        ctk.CTkLabel(bot, text="Termina DIC 2026",
                     font=self._orb(10), text_color="#a78bfa").pack(side="right")

    # ── PANEL VENCIMIENTOS ────────────────────────────────────────────────
    def _panel_vencimientos(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="#16162a", corner_radius=10)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(panel, text="PRÓXIMOS VENCIMIENTOS",
                     font=self._orb(12), text_color="#7c6fe0").pack(
            anchor="w", padx=16, pady=(16, 12))

        conn = get_connection()
        cuentas = conn.execute("SELECT * FROM cuentas_fijas").fetchall()
        creditos = conn.execute(
            "SELECT titular, banco, prox_vencimiento FROM creditos WHERE prox_vencimiento IS NOT NULL"
        ).fetchall()
        conn.close()

        items = []

        # Cuentas fijas
        for c in cuentas:
            vcto, dias = _prox_vcto_desde_dia(c["dia_vencimiento"])
            if vcto and dias is not None:
                prop = "Casa" if c["propiedad"] == "casa_padres" else "Depa"
                items.append((dias, c["nombre"], vcto, prop))

        # DUOC el 25
        hoy = date.today()
        try:
            duoc = hoy.replace(day=25)
            if duoc < hoy:
                duoc = (hoy.replace(day=1) + relativedelta(months=1)).replace(day=25)
            items.append(((duoc - hoy).days, "DUOC UC", duoc.strftime("%d/%m/%Y"), "Educación"))
        except Exception:
            pass

        # Créditos
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

            ctk.CTkLabel(f, text=badge, font=self._orb(11),
                         text_color=color,
                         fg_color=f"{color}22",
                         corner_radius=10, padx=10, pady=4).pack(
                side="right", padx=12, pady=10)
