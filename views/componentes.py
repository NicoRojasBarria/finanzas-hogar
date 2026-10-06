"""Componentes visuales reutilizables de Finanzas Hogar.

Las vistas (créditos, dashboard, etc.) arman sus pantallas con estas
piezas en vez de crear widgets sueltos con colores a mano.
"""
import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

from views import tema


def _escala(widget):
    try:
        return ctk.ScalingTracker.get_widget_scaling(widget)
    except Exception:
        return 1.0


# ═════════════════════════════════════════════════════════════════════════
#  Tarjeta resumen con brillo y mini gráfico
# ═════════════════════════════════════════════════════════════════════════
class TarjetaResumen(ctk.CTkFrame):
    """Tarjeta con título, monto grande, detalle y una línea de tendencia.

    serie: lista de números (por ejemplo, el total de los últimos meses).
    """

    SS = 2  # supersampling para bordes suaves

    def __init__(self, master, titulo, valor, detalle="", color=tema.AZUL,
                 serie=None, alto=158, fondo=tema.FONDO):
        super().__init__(master, fg_color=fondo, corner_radius=0, height=alto)
        self.titulo, self.valor, self.detalle = titulo, valor, detalle
        self.color, self.serie, self.fondo = color, serie or [], fondo
        self._alto = alto
        self._img = None
        self._pendiente = None

        s = _escala(self)
        self.canvas = tk.Canvas(self, bg=fondo, highlightthickness=0, bd=0,
                                height=int(alto * s))
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._programar)

    def actualizar(self, valor=None, detalle=None, serie=None):
        if valor is not None:
            self.valor = valor
        if detalle is not None:
            self.detalle = detalle
        if serie is not None:
            self.serie = serie
        self._dibujar()

    # ── dibujo ───────────────────────────────────────────────────────────
    def _programar(self, _evento=None):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(40, self._dibujar)

    def _dibujar(self):
        self._pendiente = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 40 or h < 40:
            return
        s = _escala(self)
        self._img = ImageTk.PhotoImage(self._fondo_tarjeta(w, h, s))
        c = self.canvas
        c.delete("all")
        c.create_image(0, 0, anchor="nw", image=self._img)

        cx = w // 2
        f_tit = tkfont.Font(family=tema.familia_texto(), size=-int(13 * s))
        f_val = tkfont.Font(family=tema.FAMILIA_NUMEROS, size=-int(27 * s), weight="bold")
        f_det = tkfont.Font(family=tema.familia_texto(), size=-int(12 * s))

        y = int(30 * s)
        ancho_tit = f_tit.measure(self.titulo)
        punto = int(4 * s)
        x0 = cx - (ancho_tit + punto * 2 + int(8 * s)) // 2
        c.create_oval(x0, y - punto, x0 + punto * 2, y + punto,
                      fill=self.color, outline="")
        c.create_text(x0 + punto * 2 + int(8 * s), y, text=self.titulo,
                      font=f_tit, fill=tema.TEXTO_SUAVE, anchor="w")
        c.create_text(cx, y + int(34 * s), text=self.valor, font=f_val,
                      fill=self.color)
        if self.detalle:
            c.create_text(cx, y + int(66 * s), text=self.detalle, font=f_det,
                          fill=tema.TEXTO_SUAVE)

    def _fondo_tarjeta(self, w, h, s):
        k = self.SS
        W, H = w * k, h * k
        m = int(10 * s * k)              # margen para el brillo
        r = int(16 * s * k)              # radio de esquinas
        caja = (m, m, W - m, H - m)
        col = tema.rgb(self.color)

        img = Image.new("RGBA", (W, H), tema.rgb(self.fondo) + (255,))

        # Brillo exterior
        brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(brillo).rounded_rectangle(caja, r, fill=col + (85,))
        brillo = brillo.filter(ImageFilter.GaussianBlur(9 * s * k))
        img.alpha_composite(brillo)

        # Cuerpo con degradado vertical
        arriba = tema.rgb(tema.mezclar(tema.SUPERFICIE, self.color, 0.16))
        abajo = tema.rgb(tema.SUPERFICIE)
        grad = Image.new("RGBA", (1, H))
        for yy in range(H):
            t = yy / max(1, H - 1)
            grad.putpixel((0, yy), tuple(int(arriba[i] + (abajo[i] - arriba[i]) * t)
                                         for i in range(3)) + (255,))
        grad = grad.resize((W, H))
        mascara = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mascara).rounded_rectangle(caja, r, fill=255)
        img.paste(grad, (0, 0), mascara)

        # Mini gráfico
        if len(self.serie) >= 2:
            capa = self._sparkline(caja, col, s * k, (W, H))
            capa.putalpha(Image.composite(capa.getchannel("A"),
                                          Image.new("L", (W, H), 0), mascara))
            img.alpha_composite(capa)

        # Borde
        ImageDraw.Draw(img).rounded_rectangle(
            caja, r, outline=col + (150,), width=max(1, int(1.2 * s * k)))

        return img.resize((w, h), Image.LANCZOS)

    def _sparkline(self, caja, col, s, tam):
        x0, y0, x1, y1 = caja
        top = y0 + (y1 - y0) * 0.76
        base = y1 - 4 * s
        vals = self.serie
        lo, hi = min(vals), max(vals)
        rango = (hi - lo) or 1
        n = len(vals)
        pts = [(x0 + (x1 - x0) * i / (n - 1),
                base - (v - lo) / rango * (base - top)) for i, v in enumerate(vals)]
        pts = _curva_suave(pts)

        capa = Image.new("RGBA", tam, (0, 0, 0, 0))
        # Relleno con degradado bajo la línea
        relleno = Image.new("RGBA", tam, (0, 0, 0, 0))
        ImageDraw.Draw(relleno).polygon(pts + [(x1, y1), (x0, y1)], fill=col + (255,))
        alfa = Image.new("L", (1, tam[1]))
        for yy in range(tam[1]):
            t = (yy - top) / max(1, (y1 - top))
            alfa.putpixel((0, yy), int(max(0.0, min(1.0, 1 - t)) * 70) if yy >= top else 70)
        alfa = alfa.resize(tam)
        relleno.putalpha(Image.composite(alfa, Image.new("L", tam, 0),
                                         relleno.getchannel("A")))
        capa.alpha_composite(relleno)

        # Línea con brillo
        linea = Image.new("RGBA", tam, (0, 0, 0, 0))
        ImageDraw.Draw(linea).line(pts, fill=col + (255,), width=int(2.2 * s), joint="curve")
        resplandor = linea.filter(ImageFilter.GaussianBlur(3 * s))
        capa.alpha_composite(resplandor)
        capa.alpha_composite(linea)
        return capa


def _curva_suave(pts, pasos=10):
    """Interpolación Catmull-Rom para que la línea no se vea quebrada."""
    if len(pts) < 3:
        return pts
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for j in range(pasos):
            t = j / pasos
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * t
                       + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t2
                       + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t3)
                for d in range(2)))
    out.append(pts[-1])
    return out


# ═════════════════════════════════════════════════════════════════════════
#  Piezas pequeñas
# ═════════════════════════════════════════════════════════════════════════
class Badge(ctk.CTkFrame):
    """Etiqueta de estado: 'Al día', 'Judicial', etc."""

    def __init__(self, master, clave_estado, fondo=tema.SUPERFICIE):
        texto, color = tema.estado(clave_estado)
        super().__init__(master, fg_color=tema.mezclar(fondo, color, 0.14),
                         border_color=tema.mezclar(fondo, color, 0.45),
                         border_width=1, corner_radius=8)
        ctk.CTkLabel(self, text=f"●  {texto}", font=tema.fuente(12, "bold"),
                     text_color=color, height=24).pack(padx=10, pady=2)


_cache_avatar = {}


def avatar(nombre, size=34):
    """Círculo con la inicial de la persona, en su color."""
    clave = (nombre, size)
    if clave in _cache_avatar:
        return _cache_avatar[clave]
    k = 4
    D = size * k
    color = tema.rgb(tema.color_persona(nombre))
    img = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, D - 1, D - 1), fill=tema.rgb(tema.mezclar(tema.SUPERFICIE, tema._rgb_a_hex(color), 0.28)))
    d.ellipse((k, k, D - 1 - k, D - 1 - k), outline=color + (255,), width=int(1.5 * k))
    inicial = (nombre or "?").strip()[:1].upper()
    try:
        f = ImageFont.truetype(tema.RUTA_ORBITRON, int(D * 0.42))
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    except Exception:
        f = ImageFont.load_default()
    d.text((D / 2, D / 2 + k), inicial, font=f, fill=color + (255,), anchor="mm")
    imagen = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    _cache_avatar[clave] = imagen
    return imagen


class BarraAvance(ctk.CTkFrame):
    """'12/30' con una barra de progreso fina debajo."""

    def __init__(self, master, pagadas, total, color=tema.AZUL, ancho=110):
        super().__init__(master, fg_color="transparent")
        pagadas, total = pagadas or 0, total or 0
        ctk.CTkLabel(self, text=f"{pagadas}/{total} cuotas" if total else "—",
                     font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                     height=18, anchor="w").pack(fill="x")
        barra = ctk.CTkProgressBar(self, width=ancho, height=5, corner_radius=3,
                                   fg_color=tema.LINEA, progress_color=color)
        barra.set(pagadas / total if total else 0)
        barra.pack(anchor="w", pady=(4, 0))


def boton(master, texto, command=None, tipo="primario", color=None, ancho=92):
    """Botones de acción. tipo: 'primario' (relleno) o 'secundario' (borde)."""
    if tipo == "primario":
        color = color or tema.VERDE
        return ctk.CTkButton(
            master, text=texto, command=command, width=ancho, height=32,
            corner_radius=9, font=tema.fuente(13, "bold"),
            fg_color=tema.mezclar(tema.SUPERFICIE, color, 0.85),
            hover_color=color, text_color="#06261A" if color == tema.VERDE else tema.FONDO)
    color = color or tema.AZUL
    return ctk.CTkButton(
        master, text=texto, command=command, width=ancho, height=32,
        corner_radius=9, font=tema.fuente(13, "bold"),
        fg_color="transparent", border_width=1,
        border_color=tema.mezclar(tema.SUPERFICIE, color, 0.55),
        hover_color=tema.mezclar(tema.SUPERFICIE, color, 0.15),
        text_color=color)


def titulo_seccion(master, texto, subtitulo=None):
    caja = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(caja, text=texto, font=tema.fuente_numero(24),
                 text_color=tema.TEXTO, anchor="w").pack(anchor="w")
    if subtitulo:
        ctk.CTkLabel(caja, text=subtitulo, font=tema.fuente(13),
                     text_color=tema.TEXTO_SUAVE, anchor="w").pack(anchor="w", pady=(2, 0))
    return caja


# ═════════════════════════════════════════════════════════════════════════
#  Tabla
# ═════════════════════════════════════════════════════════════════════════
class Tabla(ctk.CTkFrame):
    """Encabezado + filas con columnas de ancho fijo.

    columnas: lista de (titulo, ancho). La última se estira.
    destacada: índice de la columna que lleva el brillo (por ejemplo, Cuota).
    """

    def __init__(self, master, columnas, destacada=None, alto_fila=66):
        super().__init__(master, fg_color="transparent")
        self.columnas = columnas
        self.destacada = destacada
        self.alto_fila = alto_fila

        cab = ctk.CTkFrame(self, fg_color="transparent", height=34)
        cab.pack(fill="x", padx=(18, 12))
        for i, (titulo, ancho) in enumerate(columnas):
            celda = self._celda(cab, i, 34)
            es_dest = i == destacada
            ctk.CTkLabel(celda, text=titulo, font=tema.fuente(12, "bold"),
                         text_color=tema.AZUL if es_dest else tema.TEXTO_TENUE,
                         anchor="w").pack(side="left", padx=(14 if es_dest else 0, 0))

        self.cuerpo = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=tema.LINEA,
            scrollbar_button_hover_color=tema.SUPERFICIE_ALT)
        self.cuerpo.pack(fill="both", expand=True)

    def _celda(self, fila, i, alto):
        ancho = self.columnas[i][1]
        ultima = i == len(self.columnas) - 1
        celda = ctk.CTkFrame(fila, fg_color="transparent", width=ancho, height=alto)
        celda.pack(side="left", fill="x" if ultima else None, expand=ultima)
        celda.pack_propagate(False)
        return celda

    def fila(self, color_estado=None, resaltar=False):
        """Crea una fila y devuelve la lista de celdas para llenarlas."""
        fondo = tema.SUPERFICIE
        borde = tema.LINEA
        if resaltar and color_estado:
            fondo = tema.mezclar(tema.SUPERFICIE, color_estado, 0.07)
            borde = tema.mezclar(tema.LINEA, color_estado, 0.40)

        marco = ctk.CTkFrame(self.cuerpo, fg_color=fondo, border_color=borde,
                             border_width=1, corner_radius=12)
        marco.pack(fill="x", pady=4, padx=(0, 4))
        marco._fondo = fondo

        interior = ctk.CTkFrame(marco, fg_color="transparent")
        interior.pack(fill="x", padx=(6, 10), pady=1)

        acento = ctk.CTkFrame(interior, width=3, height=30, corner_radius=2,
                              fg_color=color_estado or tema.LINEA)
        acento.pack(side="left", padx=(4, 8))

        return [self._celda(interior, i, self.alto_fila) for i in range(len(self.columnas))], fondo


def celda_destacada(celda, texto, sub=None, color=tema.AZUL, fondo=tema.SUPERFICIE):
    """Bloque con borde de color para el dato principal de la fila."""
    caja = ctk.CTkFrame(celda, fg_color=tema.mezclar(fondo, color, 0.10),
                        border_color=tema.mezclar(fondo, color, 0.55),
                        border_width=1, corner_radius=10)
    caja.pack(side="left", pady=9, fill="both", expand=True, padx=(0, 26))
    ctk.CTkLabel(caja, text=texto, font=tema.fuente_numero(14), text_color=color,
                 anchor="w", height=20).pack(anchor="w", padx=12, pady=(6, 0))
    if sub:
        ctk.CTkLabel(caja, text=sub, font=tema.fuente(11), text_color=tema.TEXTO_SUAVE,
                     anchor="w", height=16).pack(anchor="w", padx=12, pady=(0, 6))
    return caja


def texto_doble(celda, principal, secundario=None, color=tema.TEXTO, fuente=None):
    caja = ctk.CTkFrame(celda, fg_color="transparent")
    caja.pack(side="left", fill="y", pady=12)
    ctk.CTkLabel(caja, text=principal, font=fuente or tema.fuente(14, "bold"),
                 text_color=color, anchor="w", height=20).pack(anchor="w")
    if secundario:
        ctk.CTkLabel(caja, text=secundario, font=tema.fuente(12),
                     text_color=tema.TEXTO_SUAVE, anchor="w", height=16).pack(anchor="w")
    return caja


# ═════════════════════════════════════════════════════════════════════════
#  Barra lateral
# ═════════════════════════════════════════════════════════════════════════
class BarraLateral(ctk.CTkFrame):
    """Navegación con indicador de sección activa.

    items: lista de (texto, funcion). activo: texto del item activo.
    """

    def __init__(self, master, items, activo=None, ancho=230):
        super().__init__(master, width=ancho, corner_radius=0, fg_color=tema.PANEL)
        self.pack_propagate(False)
        self._botones = {}

        marca = ctk.CTkFrame(self, fg_color="transparent")
        marca.pack(fill="x", padx=24, pady=(30, 6))
        ctk.CTkLabel(marca, text="FINANZAS", font=tema.fuente_numero(20),
                     text_color=tema.TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(marca, text="Hogar", font=tema.fuente(13),
                     text_color=tema.VIOLETA, anchor="w").pack(anchor="w")

        ctk.CTkFrame(self, height=1, fg_color=tema.LINEA).pack(fill="x", padx=20, pady=(18, 16))

        for texto, comando in items:
            fila = ctk.CTkFrame(self, fg_color="transparent", height=44)
            fila.pack(fill="x", padx=14, pady=2)
            fila.pack_propagate(False)
            indicador = ctk.CTkFrame(fila, width=3, corner_radius=2, fg_color="transparent")
            indicador.pack(side="left", fill="y", pady=10)
            b = ctk.CTkButton(
                fila, text=texto, anchor="w", height=40, corner_radius=10,
                font=tema.fuente(14), fg_color="transparent",
                hover_color=tema.SUPERFICIE, text_color=tema.TEXTO_SUAVE,
                command=lambda t=texto, c=comando: self._click(t, c))
            b.pack(side="left", fill="x", expand=True, padx=(6, 0))
            self._botones[texto] = (b, indicador)

        ctk.CTkLabel(self, text="v2.0", font=tema.fuente(11),
                     text_color=tema.TEXTO_TENUE).pack(side="bottom", pady=16)
        if activo:
            self.marcar(activo)

    def marcar(self, texto):
        for t, (b, ind) in self._botones.items():
            activo = t == texto
            b.configure(fg_color=tema.SUPERFICIE_ALT if activo else "transparent",
                        text_color=tema.TEXTO if activo else tema.TEXTO_SUAVE,
                        font=tema.fuente(14, "bold" if activo else "normal"))
            ind.configure(fg_color=tema.VIOLETA if activo else "transparent")

    def _click(self, texto, comando):
        self.marcar(texto)
        if comando:
            comando()
