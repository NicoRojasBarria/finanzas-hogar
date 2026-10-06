"""Tema visual de Finanzas Hogar.

Todas las vistas sacan de aquí sus colores, fuentes y formatos, así el
diseño se cambia en un solo lugar.

Uso:
    from views import tema
    tema.cargar_fuentes()            # una vez, después de crear la ventana
    ctk.CTkLabel(..., font=tema.fuente(13), text_color=tema.TEXTO)
"""
import os

import customtkinter as ctk
from tkinter import font as tkfont


# ── Paleta base ──────────────────────────────────────────────────────────
FONDO          = "#0D1322"   # fondo de la ventana
PANEL          = "#111829"   # barra lateral
SUPERFICIE     = "#161E33"   # filas y tarjetas
SUPERFICIE_ALT = "#1C2642"   # elemento activo o resaltado
LINEA          = "#242E4B"   # bordes y separadores

TEXTO          = "#E7EBF5"
TEXTO_SUAVE    = "#8D97B6"
TEXTO_TENUE    = "#5A6484"

# ── Colores con significado (usar siempre para lo mismo) ─────────────────
VERDE   = "#34D399"   # pagado, al día
AMBAR   = "#F5A524"   # pendiente, atrasado
ROJO    = "#F25C6B"   # judicial, deuda
AZUL    = "#4FB8FF"   # información, próximos vencimientos
VIOLETA = "#A78BFA"   # por planilla, marca de la app
GRIS    = "#7A839E"   # terminado

# Colores de avatar por persona (se asignan por nombre)
COLORES_PERSONA = {
    "nico": AZUL,
    "mamá": "#F472B6",
    "mama": "#F472B6",
}


# ── Estados de crédito: (texto, color) ───────────────────────────────────
ESTADOS = {
    "al_dia":    ("Al día",       VERDE),
    "atrasado":  ("Atrasado",     AMBAR),
    "judicial":  ("Judicial",     ROJO),
    "planilla":  ("Por planilla", VIOLETA),
    "terminado": ("Terminado",    GRIS),
}


def estado(clave):
    """Devuelve (texto, color) para un estado de crédito."""
    if clave in ESTADOS:
        return ESTADOS[clave]
    return (str(clave).replace("_", " ").capitalize(), GRIS)


def color_persona(nombre):
    clave = (nombre or "").strip().lower()
    if clave in COLORES_PERSONA:
        return COLORES_PERSONA[clave]
    paleta = [AZUL, VIOLETA, VERDE, AMBAR, "#F472B6"]
    return paleta[sum(map(ord, clave)) % len(paleta)]


# ── Utilidades de color ──────────────────────────────────────────────────
def _hex_a_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_a_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)


def mezclar(base, color, t):
    """Mezcla `color` sobre `base` con intensidad t (0 a 1)."""
    a, b = _hex_a_rgb(base), _hex_a_rgb(color)
    return _rgb_a_hex(a[i] + (b[i] - a[i]) * t for i in range(3))


def tenue(color, t=0.15, base=SUPERFICIE):
    """Versión apagada de un color, para fondos de badges o filas."""
    return mezclar(base, color, t)


def rgb(color):
    return _hex_a_rgb(color)


# ── Fuentes ──────────────────────────────────────────────────────────────
CARPETA_FUENTES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
)
RUTA_ORBITRON = os.path.join(CARPETA_FUENTES, "Orbitron.ttf")
FAMILIA_NUMEROS = "Orbitron"

_familia_texto = None


def cargar_fuentes():
    """Registra Orbitron. Llamar una vez, después de crear la ventana."""
    if os.path.exists(RUTA_ORBITRON):
        try:
            ctk.FontManager.load_font(RUTA_ORBITRON)
        except Exception:
            pass


def familia_texto():
    """Fuente para textos: la mejor disponible en el sistema."""
    global _familia_texto
    if _familia_texto is None:
        disponibles = set(tkfont.families())
        for f in ("Segoe UI", "Inter", "SF Pro Text", "Carlito", "DejaVu Sans"):
            if f in disponibles:
                _familia_texto = f
                break
        else:
            _familia_texto = "TkDefaultFont"
    return _familia_texto


def fuente(size=13, weight="normal"):
    """Fuente para textos normales, etiquetas y botones."""
    return ctk.CTkFont(family=familia_texto(), size=size, weight=weight)


def fuente_numero(size=16, weight="bold"):
    """Orbitron, para montos y títulos de sección."""
    return ctk.CTkFont(family=FAMILIA_NUMEROS, size=size, weight=weight)


# ── Formatos ─────────────────────────────────────────────────────────────
def pesos(monto):
    """1100806 -> '$1.100.806' (formato chileno)."""
    if monto is None:
        return "—"
    signo = "-" if monto < 0 else ""
    return f"{signo}${abs(int(monto)):,}".replace(",", ".")
