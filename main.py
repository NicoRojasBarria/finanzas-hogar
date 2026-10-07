import os
import customtkinter as ctk
from PIL import Image
from db.database import init_db
from views import tema
from views import componentes as ui

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Rutas de assets ───────────────────────────────────────────────────────────
_BASE      = os.path.dirname(os.path.abspath(__file__))
_LOGO_DIR  = os.path.join(_BASE, "assets", "logo")
_LOGO_300  = os.path.join(_LOGO_DIR, "logo_300.png")
_LOGO_140  = os.path.join(_LOGO_DIR, "logo_140.png")
_LOGO_32   = os.path.join(_LOGO_DIR, "logo_32.png")


def _ctk_image(path, size):
    """Carga un PNG como CTkImage si existe, si no devuelve None."""
    if not os.path.exists(path):
        return None
    img = Image.open(path)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=tema.FONDO)
        tema.cargar_fuentes()
        self.title("Drax — Finanzas Hogar")
        self.geometry("1400x800")
        self.minsize(1200, 600)

        # Ícono de ventana
        if os.path.exists(_LOGO_32):
            try:
                ico = ctk.CTkImage(
                    light_image=Image.open(_LOGO_32),
                    dark_image=Image.open(_LOGO_32),
                    size=(32, 32))
                lbl_ico = ctk.CTkLabel(self, image=ico, text="")
                self.iconphoto(True, ico._light_image)
            except Exception:
                pass

        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)

        self._build_layout()

    # ── Layout principal ──────────────────────────────────────────────────────
    def _build_layout(self):
        # Barra lateral con el kit visual
        items = [
            ("Casa Padres",  self.mostrar_casa_padres),
            ("Departamento", self.mostrar_depa),
            ("Créditos",     self.mostrar_creditos),
            ("Ingresos",     self.mostrar_ingresos),
            ("Dashboard",    self.mostrar_dashboard),
        ]
        self.sidebar = _BarraLateralDrax(self, items)
        self.sidebar.pack(side="left", fill="y")

        # Área principal
        self.main_area = ctk.CTkFrame(self, fg_color=tema.FONDO, corner_radius=0)
        self.main_area.pack(side="right", fill="both", expand=True)

        self._mostrar_bienvenida()

    def _mostrar_bienvenida(self):
        """Pantalla inicial con el logo Drax."""
        logo = _ctk_image(_LOGO_300, 300)
        if logo:
            ctk.CTkLabel(self.main_area, image=logo, text="").pack(expand=True)
        else:
            # Fallback si aún no se generaron los PNGs
            ctk.CTkLabel(
                self.main_area,
                text="Drax",
                font=tema.fuente_numero(48),
                text_color=tema.VIOLETA,
            ).pack(expand=True)
            ctk.CTkLabel(
                self.main_area,
                text="Software by Drax",
                font=tema.fuente(13),
                text_color=tema.TEXTO_TENUE,
            ).pack()

    # ── Navegación ────────────────────────────────────────────────────────────
    def _limpiar_main(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    def mostrar_casa_padres(self):
        self._limpiar_main()
        from views.casa_padres import CasaPadresView
        CasaPadresView(self.main_area)

    def mostrar_depa(self):
        self._limpiar_main()
        from views.departamento import DepartamentoView
        DepartamentoView(self.main_area)

    def mostrar_creditos(self):
        self._limpiar_main()
        from views.creditos import CreditosView
        CreditosView(self.main_area)

    def mostrar_ingresos(self):
        self._limpiar_main()
        from views.ingresos import IngresosView
        IngresosView(self.main_area)

    def mostrar_dashboard(self):
        self._limpiar_main()
        from views.dashboard import DashboardView
        DashboardView(self.main_area)


# ── Barra lateral con logo Drax ───────────────────────────────────────────────
class _BarraLateralDrax(ctk.CTkFrame):
    """BarraLateral del kit, pero con el logo Drax arriba en vez del texto."""

    def __init__(self, master, items, ancho=230):
        super().__init__(master, width=ancho, corner_radius=0,
                         fg_color=tema.PANEL)
        self.pack_propagate(False)
        self._botones = {}

        # Logo
        logo = _ctk_image(_LOGO_140, 120)
        if logo:
            ctk.CTkLabel(self, image=logo, text="").pack(pady=(20, 4))
        else:
            ctk.CTkLabel(self, text="Drax",
                         font=tema.fuente_numero(20),
                         text_color=tema.TEXTO).pack(pady=(30, 4))

        ctk.CTkLabel(self, text="Software by Drax",
                     font=tema.fuente(10),
                     text_color=tema.TEXTO_TENUE).pack()

        ctk.CTkFrame(self, height=1, fg_color=tema.LINEA).pack(
            fill="x", padx=20, pady=(14, 12))

        # Botones de navegación
        for texto, comando in items:
            fila = ctk.CTkFrame(self, fg_color="transparent", height=44)
            fila.pack(fill="x", padx=14, pady=2)
            fila.pack_propagate(False)
            indicador = ctk.CTkFrame(fila, width=3, corner_radius=2,
                                     fg_color="transparent")
            indicador.pack(side="left", fill="y", pady=10)
            b = ctk.CTkButton(
                fila, text=texto, anchor="w", height=40, corner_radius=10,
                font=tema.fuente(14), fg_color="transparent",
                hover_color=tema.SUPERFICIE, text_color=tema.TEXTO_SUAVE,
                command=lambda t=texto, c=comando: self._click(t, c))
            b.pack(side="left", fill="x", expand=True, padx=(6, 0))
            self._botones[texto] = (b, indicador)

        ctk.CTkLabel(self, text="v2.0",
                     font=tema.fuente(11),
                     text_color=tema.TEXTO_TENUE).pack(side="bottom", pady=16)

    def _click(self, texto, comando):
        self._marcar(texto)
        if comando:
            comando()

    def _marcar(self, texto):
        for t, (b, ind) in self._botones.items():
            activo = t == texto
            b.configure(
                fg_color=tema.SUPERFICIE_ALT if activo else "transparent",
                text_color=tema.TEXTO if activo else tema.TEXTO_SUAVE,
                font=tema.fuente(14, "bold" if activo else "normal"))
            ind.configure(fg_color=tema.VIOLETA if activo else "transparent")


if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
