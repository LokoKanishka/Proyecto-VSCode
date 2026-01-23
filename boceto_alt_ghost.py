import customtkinter as ctk
import random
import tkinter as tk

# Colores Night City
CYBER_YELLOW = "#FCEE0A"
ALT_CYAN = "#00F0FF"
DARK_VOID = "#050505"

class AltGhostLucy(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("ALT_LUCY_INTERFACE")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="black")
        
        # Compatibilidad Linux/WSL
        try: self.attributes("-alpha", 0.9)
        except: pass

        self.geometry("400x700+1000+200")
        self.is_expanded = False

        # --- CANVAS PARA EL FANTASMA ---
        # Aquí dibujaremos la "magia" de código
        self.canvas = tk.Canvas(self, width=350, height=550, bg="black", highlightthickness=0)
        self.canvas.pack(pady=20)
        
        # Dibujamos una silueta básica "fantasmal"
        self.draw_ghost_silhouette()
        
        # Animación de "Magia de Código" en las manos
        self.particles = []
        self.create_code_magic()

        # Al hacer clic en el fantasma, desplegamos la consola
        self.canvas.bind("<Button-1>", lambda e: self.toggle_console())
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonPress-1>", self.start_move)

        # --- LA CONSOLA (Desplegable) ---
        self.console = ctk.CTkFrame(self, fg_color=DARK_VOID, border_width=1, border_color=CYBER_YELLOW)
        # Se ubicará debajo del fantasma al expandir

        self.chat = ctk.CTkTextbox(self.console, fg_color="black", text_color=ALT_CYAN, font=("Consolas", 12))
        self.chat.pack(expand=True, fill="both", padx=5, pady=5)
        self.chat.insert("0.0", ">>> CONEXIÓN ESTABLECIDA CON EL MÁS ALLÁ...\n>>> Esperando protocolos...\n")
        
        self.update_animation()

    def draw_ghost_silhouette(self):
        # Dibujamos una forma humana abstracta con líneas de código
        # Cabeza
        self.canvas.create_oval(150, 50, 200, 110, outline=ALT_CYAN, width=2)
        # Cuerpo y manos extendidas (Magia)
        self.canvas.create_line(175, 110, 175, 250, fill=ALT_CYAN, width=2) # Tronco
        self.canvas.create_line(175, 150, 50, 100, fill=ALT_CYAN, width=2)  # Brazo Izq (hacia arriba)
        self.canvas.create_line(175, 150, 300, 100, fill=ALT_CYAN, width=2) # Brazo Der (hacia arriba)
        
    def create_code_magic(self):
        # Creamos "bits" de código que flotan cerca de las manos
        for _ in range(20):
            x = random.choice([50, 300]) + random.randint(-20, 20)
            y = 100 + random.randint(-20, 20)
            char = random.choice(["0", "1", "§", "∆", "∑"])
            p = self.canvas.create_text(x, y, text=char, fill=CYBER_YELLOW, font=("Courier", 10))
            self.particles.append([p, x, y, random.uniform(-1, 1)])

    def update_animation(self):
        # Hace que los bits de las manos se muevan como magia
        for p_data in self.particles:
            p, x, y, speed = p_data
            self.canvas.move(p, speed, random.uniform(-2, 2))
            # Si se alejan mucho, vuelven a la mano
            pos = self.canvas.coords(p)
            if abs(pos[0] - x) > 30: self.canvas.move(p, -speed*20, 0)
        
        # Efecto de parpadeo (Glitch)
        if random.random() > 0.9:
            self.canvas.configure(bg="#110000") # Flash rojo suave
        else:
            self.canvas.configure(bg="black")

        self.after(50, self.update_animation)

    def toggle_console(self):
        if not self.is_expanded:
            self.geometry("400x850")
            self.console.pack(expand=True, fill="both", padx=10, pady=10)
            self.is_expanded = True
        else:
            self.console.pack_forget()
            self.geometry("400x700")
            self.is_expanded = False

    # Mover ventana
    def start_move(self, event):
        self._x = event.x
        self._y = event.y
    def on_move(self, event):
        deltax = event.x - self._x
        deltay = event.y - self._y
        self.geometry(f"+{self.winfo_x() + deltax}+{self.winfo_y() + deltay}")

if __name__ == "__main__":
    app = AltGhostLucy()
    app.mainloop()
