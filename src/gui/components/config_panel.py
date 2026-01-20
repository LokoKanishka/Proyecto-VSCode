import customtkinter as ctk

class ConfigPanel(ctk.CTkFrame):
    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        
        # Estética de "Módulo de Hardware"
        self.configure(
            fg_color="#121212", 
            border_color="#333333", # Metal Cepillado
            border_width=2,
            corner_radius=0
        )

        # Cabecera con "Glow"
        self.header_frame = ctk.CTkFrame(self, fg_color="#002200", corner_radius=0, height=40)
        self.header_frame.pack(fill="x", padx=2, pady=2)
        
        self.label = ctk.CTkLabel(
            self.header_frame, 
            text="[ CPU_CORE_LOADED ]", 
            font=("Consolas", 14, "bold"), 
            text_color="#00ff41"
        )
        self.label.pack(pady=5)

        # Selectores con estilo industrial
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=20)

        ctk.CTkLabel(self.content_frame, text="> SELECT_MODEL:", font=("Consolas", 12), text_color="#00ff41").pack(anchor="w")
        
        self.model_selector = ctk.CTkOptionMenu(
            self.content_frame, 
            values=["tinyllama", "phi3", "llama3"],
            command=self.change_model,
            fg_color="#0a0a0a",
            button_color="#00ff41",
            button_hover_color="#00cc33",
            text_color="#00ff41",
            dropdown_fg_color="#050505",
            dropdown_text_color="#00ff41",
            font=("Consolas", 12),
            corner_radius=2
        )
        self.model_selector.set("tinyllama")
        self.model_selector.pack(pady=(5, 20), fill="x")

        ctk.CTkLabel(self.content_frame, text="> SYS_OVERRIDE:", font=("Consolas", 12), text_color="#00ff41").pack(anchor="w")
        
        self.sys_entry = ctk.CTkTextbox(
            self.content_frame, 
            height=200, 
            fg_color="#000000", 
            text_color="#00ff41",
            border_color="#00ff41",
            border_width=1,
            font=("Consolas", 12),
            corner_radius=2
        )
        prompt_corto = "Eres Lucy, la piloto Cyberpunk. Responde en español SIEMPRE. Sé breve y letal."
        self.sys_entry.insert("0.0", prompt_corto)
        self.sys_entry.pack(pady=5, fill="x")

        # Decoración de circuito (Label simulado)
        self.deco = ctk.CTkLabel(self, text="════════════════════", text_color="#222", font=("Consolas", 10))
        self.deco.pack(side="bottom", pady=10)

    def change_model(self, choice):
        if self.engine: 
            self.engine.set_model(choice)
        print(f"🔄 [KERNEL] Módulo {choice} montado.")
