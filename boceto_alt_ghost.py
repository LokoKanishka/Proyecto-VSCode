import customtkinter as ctk
from PIL import Image, ImageTk
import random
import os

# Colores de la Red Profunda
CYBER_YELLOW = "#FCEE0A"
ALT_GHOST_CYAN = "#00F0FF"
ALT_GHOST_RED = "#FF003C"

class AltGhostWidget(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("LUCY_ALT_GHOST")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="black")
        # Nota: -transparentcolor solo funciona en Windows. 
        # En Linux (Linux x11) la transparencia se maneja via -alpha o compositor (Picom).
        try:
            self.wm_attributes("-transparentcolor", "black")
        except:
            print("ℹ️ Linux detected: Using alpha instead of transparentcolor.")
            self.attributes("-alpha", 0.95)

        self.is_expanded = False
        self._offset_x = 0
        self._offset_y = 0

        # --- CONTENEDOR DE LA APARICIÓN ---
        self.ghost_container = ctk.CTkFrame(self, fg_color="transparent")
        self.ghost_container.pack(side="left", padx=10, pady=10)

        # Cargar Imagen de Alt (Placeholder si no existe)
        img_path = "alt_ghost.png"
        self.ghost_img = None
        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                # Forzamos transparencia si no la tiene o ajustamos visualmente
                self.ghost_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(300, 500))
            except Exception as e:
                print(f"⚠️ Error cargando imagen: {e}")

        if self.ghost_img:
            self.ghost_label = ctk.CTkLabel(self.ghost_container, image=self.ghost_img, text="")
        else:
            # Marcador visual si no hay imagen
            self.ghost_label = ctk.CTkLabel(self.ghost_container, 
                                            text=r"[ ALT_CUNNINGHAM_GHOST ]" + "\n\n     /\\  /\\ \n    (  o.o  )\n     >  ^  <\n\n[ CODIGO MAGICO ]",
                                            font=("Consolas", 20, "bold"), text_color=ALT_GHOST_CYAN)

        self.ghost_label.pack()
        self.ghost_label.bind("<Button-1>", self.start_move)
        self.ghost_label.bind("<B1-Motion>", self.on_move)
        self.ghost_label.bind("<Double-Button-1>", lambda e: self.toggle_console())

        # --- LA CONSOLA "MÁGICA" (Oculta) ---
        self.console_frame = ctk.CTkFrame(self, fg_color="#050505", border_width=2, border_color=CYBER_YELLOW, corner_radius=0)
        
        self.console_title = ctk.CTkLabel(self.console_frame, text="/// ACCESS_GRANTED: DEEP_NET_CONSOLE", 
                                          font=("Courier", 12, "bold"), text_color=CYBER_YELLOW)
        self.console_title.pack(fill="x", padx=10, pady=5)

        self.chat_box = ctk.CTkTextbox(self.console_frame, fg_color="black", text_color=ALT_GHOST_CYAN, 
                                       font=("Consolas", 12), border_width=1, border_color="#111111")
        self.chat_box.pack(expand=True, fill="both", padx=10, pady=10)
        self.chat_box.insert("0.0", "LUCY-ALT: He cruzado el Blackwall. ¿Qué protocolos ejecutamos hoy?\n\n")
        self.chat_box.configure(state="disabled")

        # Iniciar efecto de interferencia
        self.glitch_effect()

    def toggle_console(self):
        if not self.is_expanded:
            # Expandir hacia la derecha
            self.geometry("800x600")
            self.console_frame.pack(side="left", expand=True, fill="both", padx=10, pady=50)
            self.is_expanded = True
        else:
            self.console_frame.pack_forget()
            self.geometry("320x600")
            self.is_expanded = False

    def glitch_effect(self):
        # Simula la inestabilidad de Alt Cunningham
        colors = [ALT_GHOST_CYAN, ALT_GHOST_RED, "#FFFFFF", CYBER_YELLOW]
        if not self.is_expanded:
            if not self.ghost_img:
                self.ghost_label.configure(text_color=random.choice(colors))
            # Cambio sutil de opacidad
            self.attributes("-alpha", random.uniform(0.85, 1.0))
        
        self.after(random.randint(150, 800), self.glitch_effect)

    # Lógica para moverla
    def start_move(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def on_move(self, event):
        x = self.winfo_x() + event.x - self._offset_x
        y = self.winfo_y() + event.y - self._offset_y
        self.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    app = AltGhostWidget()
    app.mainloop()
