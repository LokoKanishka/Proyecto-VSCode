import customtkinter as ctk

ctk.set_appearance_mode("Dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1100x600")
        self.title("LUCY - REPARACION VISUAL")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (IZQUIERDA) ---
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.pack_propagate(False) # ESTO OBLIGA EL ANCHO

        ctk.CTkLabel(self.sidebar, text="LUCY MENU", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkButton(self.sidebar, text="New Chat (ANCHO)", height=40, anchor="w").pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(self.sidebar, text="Settings", height=40, anchor="w").pack(fill="x", padx=10, pady=5)

        # --- CHAT AREA (DERECHA) ---
        self.chat = ctk.CTkFrame(self)
        self.chat.grid(row=0, column=1, sticky="nsew")
        self.chat.grid_rowconfigure(0, weight=1)
        self.chat.grid_columnconfigure(0, weight=1)

        # Historial (Arriba)
        self.history = ctk.CTkTextbox(self.chat)
        self.history.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.history.insert("0.0", "Si ves esta ventana, el archivo force_ui.py se creó correctamente.")

        # Input (Abajo)
        self.input = ctk.CTkFrame(self.chat, height=50)
        self.input.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.input.grid_columnconfigure(1, weight=1)

        # --- MICRÓFONO ROJO (AQUI ESTÁ LA CLAVE) ---
        self.mic = ctk.CTkButton(self.input, text="🎙️", width=50, fg_color="#cc0000", hover_color="red")
        self.mic.grid(row=0, column=0, padx=5)

        self.entry = ctk.CTkEntry(self.input, placeholder_text="Escribe aquí...")
        self.entry.grid(row=0, column=1, sticky="ew", padx=5)

        self.send = ctk.CTkButton(self.input, text="SEND", width=60)
        self.send.grid(row=0, column=2, padx=5)

if __name__ == "__main__":
    app = App()
    app.mainloop()
