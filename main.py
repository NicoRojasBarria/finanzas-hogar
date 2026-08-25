import customtkinter as ctk
from db.database import init_db

# Configuración visual
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Finanzas Hogar")
        self.geometry("1200x700")
        self._build_layout()

    def _build_layout(self):
        # Panel lateral izquierdo
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(
            self.sidebar,
            text="💰 Finanzas",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=30)

        # Botones de navegación
        botones = [
            ("🏠 Casa Padres", self.mostrar_casa_padres),
            ("🏢 Departamento", self.mostrar_depa),
            ("💳 Créditos",    self.mostrar_creditos),
            ("📊 Dashboard",   self.mostrar_dashboard),
        ]

        for texto, comando in botones:
            ctk.CTkButton(
                self.sidebar,
                text=texto,
                command=comando,
                anchor="w"
            ).pack(padx=20, pady=8, fill="x")

        # Área principal
        self.main_area = ctk.CTkFrame(self)
        self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self.label_bienvenida = ctk.CTkLabel(
            self.main_area,
            text="Selecciona una sección",
            font=ctk.CTkFont(size=16)
        )
        self.label_bienvenida.pack(expand=True)

    def mostrar_casa_padres(self):
        self._limpiar_main()
        from views.casa_padres import CasaPadresView
        CasaPadresView(self.main_area)

    def mostrar_depa(self):
        self._limpiar_main()
        ctk.CTkLabel(self.main_area, text="🏢 Departamento — en construcción",
                     font=ctk.CTkFont(size=16)).pack(expand=True)

    def mostrar_creditos(self):
         self._limpiar_main()
         from views.creditos import CreditosView
         CreditosView(self.main_area)

    def mostrar_dashboard(self):
        self._limpiar_main()
        ctk.CTkLabel(self.main_area, text="📊 Dashboard — en construcción",
                     font=ctk.CTkFont(size=16)).pack(expand=True)

    def _limpiar_main(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()