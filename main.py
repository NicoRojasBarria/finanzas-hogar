import customtkinter as ctk
from db.database import init_db

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Finanzas Hogar")
        self.geometry("1400x800")
        self.minsize(1200, 600)
        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)
        try:
            from tkinter import font as tkfont
            self.tk.call('font', 'create', 'Orbitron')
            tkfont.Font(root=self, family='Orbitron', size=11)
        except Exception:
            pass
        self._build_layout()

    def _build_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1a1a2e")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="💰 Finanzas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        ).pack(pady=(35, 25))

        ctk.CTkFrame(self.sidebar, height=2, fg_color="#2e2e4e").pack(
            fill="x", padx=15, pady=(0, 20)
        )

        botones = [
            ("🏠  Casa Padres",  self.mostrar_casa_padres),
            ("🏢  Departamento", self.mostrar_depa),
            ("💳  Créditos",     self.mostrar_creditos),
            ("📊  Dashboard",    self.mostrar_dashboard),
        ]

        for texto, comando in botones:
            ctk.CTkButton(
                self.sidebar,
                text=texto,
                command=comando,
                anchor="w",
                width=180,
                height=40,
                corner_radius=8,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                hover_color="#2e2e5e",
                text_color="#e0e0e0",
            ).pack(padx=18, pady=5, fill="x")

        ctk.CTkLabel(
            self.sidebar,
            text="v1.0",
            font=ctk.CTkFont(size=11),
            text_color="#555577"
        ).pack(side="bottom", pady=15)

        self.main_area = ctk.CTkFrame(self, fg_color="#212121")
        self.main_area.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(
            self.main_area,
            text="Selecciona una sección",
            font=ctk.CTkFont(size=16),
            text_color="#888888"
        ).pack(expand=True)

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

    def mostrar_dashboard(self):
        self._limpiar_main()
        from views.dashboard import DashboardView
        DashboardView(self.main_area)

    def _limpiar_main(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
