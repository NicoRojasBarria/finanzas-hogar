"""
Servicio de resumen mensual.

Toda la lógica de "cuánto pagué / cuánto falta / cuánto sobra" vive acá,
así Créditos, Dashboard e Ingresos muestran exactamente los mismos números.
(Es el equivalente a un @Service de Spring: las vistas solo lo llaman.)
"""
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from db.database import get_connection

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def nombre_mes(d):
    return MESES[d.month - 1]


def _parse_fecha(txt):
    try:
        return datetime.strptime(txt, "%d/%m/%Y").date()
    except Exception:
        return None


def credito_activo(cr):
    """Un crédito está activo si le quedan cuotas (o si no sabemos el total)."""
    total = cr["cuotas_total"]
    return not total or (cr["cuotas_pagadas"] or 0) < total


def es_planilla(cr):
    """Créditos descontados del sueldo: ya vienen restados del ingreso."""
    return bool(cr["por_planilla"]) if "por_planilla" in cr.keys() else False


def cuotas_restantes(cr):
    total = cr["cuotas_total"]
    if not total:
        return None
    return max(0, total - (cr["cuotas_pagadas"] or 0))


def _vencimientos_credito(cr, hasta):
    """Fechas de las cuotas que vencen desde prox_vencimiento hasta 'hasta' (inclusive)."""
    prox = _parse_fecha(cr["prox_vencimiento"])
    if not prox or not credito_activo(cr):
        return []
    restantes = cuotas_restantes(cr)
    limite = restantes if restantes is not None else 24
    fechas = []
    i = 0
    f = prox
    while f <= hasta and i < limite:
        fechas.append(f)
        i += 1
        f = prox + relativedelta(months=i)
    return fechas


def estimado_cuenta(conn, cuenta):
    """Mismo criterio que Casa Padres: último pago, o promedio de los últimos 3."""
    pagos = conn.execute(
        "SELECT monto_real FROM pagos WHERE cuenta_id = ? ORDER BY fecha DESC LIMIT 3",
        (cuenta["id"],)
    ).fetchall()
    if not pagos:
        return cuenta["monto_estimado"] or 0
    if len(pagos) < 3:
        return pagos[0]["monto_real"]
    return sum(p["monto_real"] for p in pagos) // len(pagos)


def resumen_mes(ref=None):
    hoy = date.today()
    ref = ref or hoy
    ini = ref.replace(day=1)
    fin = ini + relativedelta(months=1) - timedelta(days=1)
    ini_prox = ini + relativedelta(months=1)
    fin_prox = ini + relativedelta(months=2) - timedelta(days=1)
    mes_str = ref.strftime("%Y-%m")

    conn = get_connection()
    pendientes = []

    # ── Cuentas fijas (Casa Padres + Departamento) ──────────────────────
    cuentas = conn.execute("SELECT * FROM cuentas_fijas").fetchall()
    pagado_cuentas = conn.execute(
        "SELECT COALESCE(SUM(monto_real),0) AS t FROM pagos WHERE mes = ?", (mes_str,)
    ).fetchone()["t"]
    falta_cuentas = 0
    proximo_cuentas = 0

    for c in cuentas:
        est = estimado_cuenta(conn, c)
        proximo_cuentas += est
        pagada = conn.execute(
            "SELECT COUNT(*) AS n FROM pagos WHERE cuenta_id = ? AND mes = ?",
            (c["id"], mes_str)
        ).fetchone()["n"]
        if pagada or not est:
            continue
        vence = None
        if c["dia_vencimiento"]:
            try:
                vence = ini.replace(day=c["dia_vencimiento"])
            except ValueError:
                vence = fin
        falta_cuentas += est
        pendientes.append({
            "nombre": c["nombre"],
            "tipo": "Casa" if c["propiedad"] == "casa_padres" else "Depa",
            "monto": est,
            "vence": vence,
            "estimado": True,
        })

    # ── Créditos ────────────────────────────────────────────────────────
    creditos = conn.execute("SELECT * FROM creditos").fetchall()
    fila = conn.execute(
        "SELECT COALESCE(SUM(pc.monto_real),0) AS t, COUNT(*) AS n "
        "FROM pagos_creditos pc JOIN creditos c ON c.id = pc.credito_id "
        "WHERE strftime('%Y-%m', pc.fecha) = ? AND COALESCE(c.por_planilla, 0) = 0",
        (mes_str,)
    ).fetchone()
    pagado_creditos, n_pagos_creditos = fila["t"], fila["n"]

    falta_creditos = n_falta_creditos = 0
    proximo_creditos = n_proximo_creditos = 0
    deuda = judiciales = atrasados = 0

    for cr in creditos:
        if not credito_activo(cr):
            continue
        restantes = cuotas_restantes(cr)
        if restantes:
            deuda += (cr["cuota"] or 0) * restantes
        if cr["estado"] == "judicial":
            judiciales += 1
        elif cr["estado"] == "atrasado":
            atrasados += 1

        # Por planilla: suma a la deuda, pero no al pago mensual (ya viene
        # descontado del sueldo que se registra en Ingresos)
        if es_planilla(cr):
            continue

        for f in _vencimientos_credito(cr, fin):
            falta_creditos += cr["cuota"]
            n_falta_creditos += 1
            pendientes.append({
                "nombre": f"{cr['banco']} — {cr['titular']}",
                "tipo": "Crédito",
                "monto": cr["cuota"],
                "vence": f,
                "estimado": False,
            })

        prox = [f for f in _vencimientos_credito(cr, fin_prox) if f >= ini_prox]
        proximo_creditos += cr["cuota"] * len(prox)
        n_proximo_creditos += len(prox)

    ingresos = conn.execute(
        "SELECT COALESCE(SUM(monto),0) AS t FROM ingresos WHERE mes = ?", (mes_str,)
    ).fetchone()["t"]
    conn.close()

    pendientes.sort(key=lambda p: p["vence"] or fin)
    pagado = pagado_cuentas + pagado_creditos
    falta = falta_cuentas + falta_creditos

    return {
        "mes": nombre_mes(ini),
        "mes_prox": nombre_mes(ini_prox),
        "ingresos": ingresos,
        "pagado_cuentas": pagado_cuentas,
        "pagado_creditos": pagado_creditos,
        "n_pagos_creditos": n_pagos_creditos,
        "pagado": pagado,
        "falta_cuentas": falta_cuentas,
        "falta_creditos": falta_creditos,
        "n_falta_creditos": n_falta_creditos,
        "falta": falta,
        "total_mes": pagado + falta,
        "disponible": ingresos - pagado,          # lo que tenés hoy en mano
        "sobra": ingresos - pagado - falta,       # lo que queda después de pagar todo
        "proximo_cuentas": proximo_cuentas,
        "proximo_creditos": proximo_creditos,
        "n_proximo_creditos": n_proximo_creditos,
        "proximo": proximo_cuentas + proximo_creditos,
        "deuda": deuda,
        "judiciales": judiciales,
        "atrasados": atrasados,
        "pendientes": pendientes,
    }
