import customtkinter as ctk
import time
import threading

# Configuración Cyberpunk
ctk.set_appearance_mode("Dark")
CYBER_YELLOW = "#FCEE0A"
CYBER_PURPLE = "#BD00FF"
CORE_BG = "#1A0033"
DARK_MTX = "#0A0A0A"

class ExpandableCore(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Geometrías para los dos estados
        self.collapsed_size = "180x180"
        self.expanded_size = "300x500"
        # Ubicación inicial (abajo a la derecha, ajusta si queda fuera)
        self.start_pos = "+1600+700" 
        
        self.geometry(self.collapsed_size + self.start_pos)
        self.title("Lucy Core V2")
        self.overrideredirect(True)
        self.configure(fg_color="black")
        self.attributes("-alpha", 0.95)

        self.is_expanded = False

        # --- CONTENEDOR PRINCIPAL ---
        self.main_container = ctk.CTkFrame(self, fg_color="black", corner_radius=20, border_width=2, border_color=CYBER_YELLOW)
        self.main_container.pack(expand=True, fill="both", padx=5, pady=5)

        # --- 1. EL NÚCLEO SUPERIOR (Siempre visible) ---
        self.top_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=160)
        self.top_frame.pack(fill="x", pady=(10, 0))

        # Esfera exterior
        self.core_frame = ctk.CTkFrame(self.top_frame, width=140, height=140, corner_radius=70, fg_color=CORE_BG, border_width=3, border_color=CYBER_YELLOW)
        self.core_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Anillo de energía
        self.energy_ring = ctk.CTkFrame(self.core_frame, width=110, height=110, corner_radius=55, fg_color=CORE_BG, border_width=2, border_color=CYBER_PURPLE)
        self.energy_ring.place(relx=0.5, rely=0.5, anchor="center")

        # Botón Central (Activador)
        self.core_button = ctk.CTkButton(self.core_frame, text="LUCY", width=80, height=80, corner_radius=40,
                                         fg_color=CYBER_YELLOW, text_color="black", font=("Arial Black", 14),
                                         hover_color="#FFFF00", command=self.toggle_expand)
        self.core_button.place(relx=0.5, rely=0.5, anchor="center")

        # --- 2. ÁREA DE CHAT (Oculta al inicio) ---
        self.chat_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        # No lo empacamos todavía
        
        self.chat_box = ctk.CTkTextbox(self.chat_frame, fg_color=DARK_MTX, text_color=CYBER_YELLOW, font=("Consolas", 12), corner_radius=10, border_width=1, border_color=CYBER_PURPLE)
        self.chat_box.pack(expand=True, fill="both", padx=10, pady=10)
        self.chat_box.insert("0.0", ">>> SISTEMA EN REPOSO.\n>>> Click en el núcleo para expandir.\n")
        self.chat_box.configure(state="disabled")

        # Botón de cierre pequeño
        self.close_btn = ctk.CTkButton(self, text="x", width=20, height=20, fg_color="#330000", text_color="red", hover_color="#550000", command=self.destroy, corner_radius=10)
        self.close_btn.place(x=10, y=10)

        # Animación
        self.pulsing = False
        self.pulse_core()
        
        # Simulación de chat (hilo separado)
        threading.Thread(target=self.simulate_chat, daemon=True).start()

    def toggle_expand(self):
        if not self.is_expanded:
            # EXPANDIR
            self.geometry(self.expanded_size + self.start_pos)
            self.chat_frame.pack(expand=True, fill="both")
            self.core_button.configure(text="▲")
            self.is_expanded = True
        else:
            # CONTRAER
            self.chat_frame.pack_forget()
            self.geometry(self.collapsed_size + self.start_pos)
            self.core_button.configure(text="LUCY")
            self.is_expanded = False

    def pulse_core(self):
        try:
            if not self.pulsing:
                self.energy_ring.configure(border_color=CYBER_YELLOW, border_width=4)
                self.pulsing = True
            else:
                self.energy_ring.configure(border_color=CYBER_PURPLE, border_width=2)
                self.pulsing = False
            self.after(800, self.pulse_core)
        except: pass

    def simulate_chat(self):
        time.sleep(3)
        msgs = [
            "TÚ: Hola Lucy, ¿estás ahí?",
            "LUCY: Siempre operativa. Todos los sistemas al 100%.",
            "TÚ: Necesito que abras el navegador y busques 'Cyberpunk ambient music'.",
            "LUCY: Entendido. Ejecutando protocolo de búsqueda...",
            "LUCY: ...",
            "LUCY: Listo. Reproduciendo en la ventana principal."
        ]
        for msg in msgs:
            if not self.winfo_exists(): break
            time.sleep(1.5)
            self.chat_box.configure(state="normal")
            prefix = ">>> " if "TÚ" in msg else " "
            color = CYBER_YELLOW if "LUCY" in msg else "#00FF41"
            self.chat_box.insert("end", f"{prefix}{msg}\n")
            self.chat_box.see("end")
            self.chat_box.configure(state="disabled")
            # Si habla Lucy, forzamos expansión si estaba cerrada
            if "LUCY" in msg and not self.is_expanded:
                 self.after(0, self.toggle_expand)

if __name__ == "__main__":
    app = ExpandableCore()
    app.mainloop()
