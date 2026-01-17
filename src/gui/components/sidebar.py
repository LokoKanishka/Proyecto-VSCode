import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, callback_new_chat=None, callback_settings=None, **kwargs):
        # AQUI ESTA LA CLAVE: width=300 y pack_propagate(False)
        super().__init__(master, width=300, corner_radius=0, **kwargs)
        self.callback_new_chat = callback_new_chat
        self.callback_settings = callback_settings
        
        self.grid_rowconfigure(4, weight=1)
        self.pack_propagate(False) 

        # Título
        self.logo_label = ctk.CTkLabel(self, text="LUCY Studio", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(pady=(30, 20), padx=20, anchor="w")

        # Botones (Anchos y con texto completo)
        self.btn_new = ctk.CTkButton(self, text="New Chat", height=45, anchor="w", fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), command=self.on_new_chat)
        self.btn_new.pack(fill="x", padx=20, pady=10)

        self.btn_search = ctk.CTkButton(self, text="Search History", height=45, anchor="w", fg_color="transparent", text_color=("gray10", "#DCE4EE"))
        self.btn_search.pack(fill="x", padx=20, pady=10)

        self.btn_models = ctk.CTkButton(self, text="My Models", height=45, anchor="w", fg_color="transparent", text_color=("gray10", "#DCE4EE"))
        self.btn_models.pack(fill="x", padx=20, pady=10)

        # Settings
        self.btn_settings = ctk.CTkButton(self, text="Settings", height=45, anchor="w", fg_color="transparent", text_color=("gray10", "#DCE4EE"), command=self.on_settings)
        self.btn_settings.pack(side="bottom", fill="x", padx=20, pady=30)

    def on_new_chat(self):
        if self.callback_new_chat: self.callback_new_chat()
        
    def on_settings(self):
        if self.callback_settings: self.callback_settings()
