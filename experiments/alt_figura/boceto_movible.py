import customtkinter as ctk
import time
import threading

# Configuración Estética
ctk.set_appearance_mode("Dark")
CYBER_YELLOW = "#FCEE0A"
CYBER_PURPLE = "#BD00FF"
CORE_BG = "#1A0033"
DARK_MTX = "#0A0A0A"

class MovableCore(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Estado inicial
        self.collapsed_size = (200, 200)
        self.expanded_size = (320, 550)
        self.geometry(f"{self.collapsed_size[0]}x{self.collapsed_size[1]}+1000+400")
        
        self.overrideredirect(True) # Sin bordes
        self.attributes("-topmost", True)
        self.configure(fg_color="black")
        self.wm_attributes("-alpha", 0.95)

        self.is_expanded = False
        
        # --- LÓGICA DE ARRASTRE ---
        self._offset_x = 0
        self._offset_y = 0
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.on_move)

        # --- CONTENEDOR PRINCIPAL ---
        self.main_container = ctk.CTkFrame(self, fg_color="black", corner_radius=30, border_width=2, border_color=CYBER_YELLOW)
        self.main_container.pack(expand=True, fill="both", padx=5, pady=5)
        # Re-bind para que el frame también sea arrastrable
        self.main_container.bind("<Button-1>", self.start_move)
        self.main_container.bind("<B1-Motion>", self.on_move)

        # --- 1. CABECERA / NÚCLEO ---
        self.top_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=180)
        self.top_frame.pack(fill="x", pady=(10, 0))
        self.top_frame.bind("<Button-1>", self.start_move)
        self.top_frame.bind("<B1-Motion>", self.on_move)

        # Esfera
        self.core_frame = ctk.CTkFrame(self.top_frame, width=140, height=140, corner_radius=70, fg_color=CORE_BG, border_width=3, border_color=CYBER_YELLOW)
        self.core_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Botón Central
        self.core_button = ctk.CTkButton(self.core_frame, text="LUCY", width=80, height=80, corner_radius=40,
                                         fg_color=CYBER_YELLOW, text_color="black", font=("Arial Black", 14),
                                         command=self.toggle_expand)
        self.core_button.place(relx=0.5, rely=0.5, anchor="center")

        # --- 2. PANEL DE CHAT (Oculto) ---
        self.chat_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.chat_box = ctk.CTkTextbox(self.chat_frame, fg_color=DARK_MTX, text_color=CYBER_YELLOW, font=("Consolas", 12), border_width=1, border_color=CYBER_PURPLE)
        self.chat_box.pack(expand=True, fill="both", padx=15, pady=15)
        self.chat_box.insert("0.0", ">>> SISTEMA OPERATIVO.\n>>> Arrástrame desde el borde negro.\n")
        self.chat_box.configure(state="disabled")

        # Animación
        self.pulsing = False
        self.pulse_core()

    # --- FUNCIONES DE MOVIMIENTO ---
    def start_move(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def on_move(self, event):
        x = self.winfo_x() + event.x - self._offset_x
        y = self.winfo_y() + event.y - self._offset_y
        self.geometry(f"+{x}+{y}")

    def toggle_expand(self):
        if not self.is_expanded:
            self.geometry(f"{self.expanded_size[0]}x{self.expanded_size[1]}")
            self.chat_frame.pack(expand=True, fill="both")
            self.core_button.configure(text="▲")
            self.is_expanded = True
        else:
            self.chat_frame.pack_forget()
            self.geometry(f"{self.collapsed_size[0]}x{self.collapsed_size[1]}")
            self.core_button.configure(text="LUCY")
            self.is_expanded = False

    def pulse_core(self):
        try:
            color = CYBER_YELLOW if not self.pulsing else CYBER_PURPLE
            self.core_frame.configure(border_color=color)
            self.pulsing = not self.pulsing
            self.after(1000, self.pulse_core)
        except: pass

if __name__ == "__main__":
    app = MovableCore()
    app.mainloop()
