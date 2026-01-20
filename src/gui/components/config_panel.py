import customtkinter as ctk

class ConfigPanel(ctk.CTkFrame):
    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine

        # Título
        self.label = ctk.CTkLabel(self, text="SYSTEM_CONFIG", font=("Consolas", 12, "bold"), text_color="#00ff41")
        self.label.pack(pady=(10, 5), padx=10, anchor="w")

        # Selector de Modelo (CORREGIDO: Sin border_width/border_color)
        self.model_var = ctk.StringVar(value="tinyllama")
        self.model_selector = ctk.CTkOptionMenu(
            self,
            values=["tinyllama", "mistral", "llama2", "neural-chat"],
            command=self.change_model,
            variable=self.model_var,
            fg_color="#222222",        # Color de fondo
            button_color="#00ff41",    # Color del botón
            button_hover_color="#00cc33",
            text_color="#ffffff"
        )
        self.model_selector.pack(pady=5, padx=10, fill="x")

        # Botón de Reset
        self.reset_btn = ctk.CTkButton(
            self,
            text="REBOOT_CORE",
            fg_color="#330000",
            hover_color="#550000",
            border_color="#ff0000",
            border_width=1,
            text_color="#ffcccc",
            command=self.reset_engine
        )
        self.reset_btn.pack(pady=10, padx=10, fill="x", side="bottom")

    def change_model(self, choice):
        print(f"🔄 Cambio de modelo solicitado: {choice}")
        if self.engine:
            self.engine.set_model(choice)

    def reset_engine(self):
        print("⚠️ Reiniciando motor...")
