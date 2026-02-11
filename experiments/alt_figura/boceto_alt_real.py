import customtkinter as ctk
import random
import tkinter as tk

# Paleta Night City
CYBER_YELLOW = "#FCEE0A"
ALT_CYAN = "#00F0FF"
ALT_PURPLE = "#BD00FF"

class AltDeepNet(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("ALT_ULTIMATE")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="black")
        
        try: self.attributes("-alpha", 0.9)
        except: pass

        self.geometry("450x750+1000+100")
        self.is_expanded = False

        self.canvas = tk.Canvas(self, width=450, height=550, bg="black", highlightthickness=0)
        self.canvas.pack(pady=10)
        
        # Dibujar a Alt y el Nano Banana
        self.draw_alt_silhouette()
        self.draw_nano_banana()
        
        # Partículas de magia de código
        self.code_bits = []
        self.init_magic()

        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<Double-Button-1>", lambda e: self.toggle_console())

        # Consola Cyberpunk
        self.console = ctk.CTkFrame(self, fg_color="#050505", border_width=1, border_color=CYBER_YELLOW)
        self.chat = ctk.CTkTextbox(self.console, fg_color="black", text_color=ALT_CYAN, font=("Consolas", 12))
        self.chat.pack(expand=True, fill="both", padx=5, pady=5)
        self.chat.insert("0.0", ">>> [ALT_CUNNINGHAM_ENLACE]: Conectada.\n>>> No soy un gatito, Choomba. Soy tu peor pesadilla digital.\n")
        
        self.animate()

    def draw_alt_silhouette(self):
        # Dibujamos una silueta más "forma humana" con polígonos
        points = [225,80, 200,120, 150,150, 80,100, 100,130, 180,180, 180,350, 225,450, 270,350, 270,180, 350,130, 370,100, 300,150, 250,120]
        self.ghost = self.canvas.create_polygon(points, fill="", outline=ALT_CYAN, width=2, smooth=True)

    def draw_nano_banana(self):
        # El arco amarillo de energía rodeando a Alt
        self.banana = self.canvas.create_arc(50, 50, 400, 500, start=200, extent=140, 
                                             outline=CYBER_YELLOW, width=5, style="arc")
        self.banana2 = self.canvas.create_arc(50, 50, 400, 500, start=20, extent=140, 
                                              outline=CYBER_YELLOW, width=5, style="arc")

    def init_magic(self):
        # Bits de código en las manos (extremos de los brazos)
        for _ in range(40):
            x, y = random.choice([(80, 100), (370, 100)])
            char = random.choice(["0", "1", "X", "†", "∆"])
            p = self.canvas.create_text(x, y, text=char, fill=CYBER_YELLOW, font=("Arial", 10))
            self.code_bits.append([p, x, y, random.uniform(-2, 2), random.uniform(-2, 2)])

    def animate(self):
        # Animación de glitch y magia
        for b in self.code_bits:
            self.canvas.move(b[0], b[3], b[4])
            pos = self.canvas.coords(b[0])
            if abs(pos[0]-b[1]) > 40 or abs(pos[1]-b[2]) > 40:
                self.canvas.moveto(b[0], b[1], b[2])

        # Glitch del Nano Banana
        if random.random() > 0.8:
            self.canvas.itemconfig(self.banana, outline=ALT_PURPLE)
            self.canvas.itemconfig(self.ghost, outline="white")
        else:
            self.canvas.itemconfig(self.banana, outline=CYBER_YELLOW)
            self.canvas.itemconfig(self.ghost, outline=ALT_CYAN)

        self.after(60, self.animate)

    def toggle_console(self):
        if not self.is_expanded:
            self.geometry("450x850")
            self.console.pack(expand=True, fill="both", padx=10, pady=10)
            self.is_expanded = True
        else:
            self.console.pack_forget()
            self.geometry("450x750")
            self.is_expanded = False

    def start_move(self, event):
        self._x, self._y = event.x, event.y
    def on_move(self, event):
        self.geometry(f"+{self.winfo_x() + event.x - self._x}+{self.winfo_y() + event.y - self._y}")

if __name__ == "__main__":
    AltDeepNet().mainloop()
