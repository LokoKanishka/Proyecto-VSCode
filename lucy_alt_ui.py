import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import queue
import time
import sys
import os
import math

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path: sys.path.append(project_root)

# --- CONFIGURACIÓN VISUAL HD ---
COLOR_TEXTO = "#00F0FF" # Cyan Cyberpunk
COLOR_FONDO = "#050505" # Casi negro
COLOR_CONSOLA_BG = "#0A0A0A" # Fondo consola levemente distinto
COLOR_BORDE = "#00E0E0"
OPACIDAD_BASE = 0.95 # Un poco más solido para se vea mejor
FPS = 24 # Estilo cinematográfico, más suave para la CPU

class LucySpectralUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Detectar tamaño de assets o usar default grande
        self.img_w = 850
        self.img_h = 1000
        
        self.title("Lucy Alt Interface HD")
        self.geometry(f"{self.img_w}x{self.img_h}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", OPACIDAD_BASE)
        self.configure(fg_color=COLOR_FONDO)
        # Nota: La transparencia real en linux depende del compositor
        
        self.load_queue = queue.Queue()
        self.console_visible = False
        self.assets_loaded = False
        self.playing_effect = False
        
        self.idle_frames = []
        self.effect_bits_frames = []
        self.current_frame_idx = 0
        self.frame_delay = int(1000 / FPS)

        self.setup_ui()
        self.setup_console_hd()
        
        self.start_async_loading()
        self.process_load_queue()
        self.animate_loop()

    def setup_ui(self):
        self.avatar_frame = ctk.CTkFrame(self, width=self.img_w, height=self.img_h, fg_color=COLOR_FONDO)
        self.avatar_frame.place(x=0, y=0)
        
        self.label_alt = ctk.CTkLabel(
            self.avatar_frame, 
            text="INITIALIZING HD CORE...", 
            text_color=COLOR_TEXTO,
            font=("JetBrains Mono", 16, "bold"),
            width=self.img_w, 
            height=self.img_h
        )
        self.label_alt.pack()
        
        for w in [self.avatar_frame, self.label_alt]:
            w.bind("<ButtonPress-1>", self.on_press)
            w.bind("<ButtonRelease-1>", self.on_release)
            w.bind("<B1-Motion>", self.on_drag)

    def setup_console_hd(self):
        # La consola ocupa el 50% inferior
        self.console_h = int(self.img_h * 0.5) 
        self.console_w = int(self.img_w * 0.9) # Margen a los lados
        
        self.console_y_hidden = self.img_h + 20
        self.console_y_visible = self.img_h - self.console_h - 20 
        self.console_y = self.console_y_hidden
        
        # Frame semi-transparente para el chat
        self.console_frame = ctk.CTkFrame(
            self, 
            fg_color=COLOR_CONSOLA_BG, 
            border_width=2, 
            border_color=COLOR_BORDE, 
            corner_radius=15,
            width=self.console_w, 
            height=self.console_h
        )
        self.console_frame.place(x=(self.img_w - self.console_w)//2, y=self.console_y)
        
        # Textbox interno
        self.console = ctk.CTkTextbox(
            self.console_frame, 
            fg_color="transparent", 
            text_color=COLOR_TEXTO, 
            font=("Consolas", 14),
            activate_scrollbars=False,
            width=self.console_w - 20,
            height=self.console_h - 20
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=10)
        self.log("Sistema Neural v3.0: En Espera...")

    def start_async_loading(self):
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path_idle = os.path.join(base_dir, "assets/figurita_loop")
        path_bits = os.path.join(base_dir, "assets/effect_bits")
        
        idle, bits = [], []
        
        # Cargar IDLE
        if os.path.exists(path_idle):
            files = sorted([f for f in os.listdir(path_idle) if f.endswith('.png')], key=lambda x: int(x.split('_')[-1].split('.')[0]))
            for f in files:
                img = Image.open(os.path.join(path_idle, f)).convert("RGBA")
                if not idle:
                    self.real_w, self.real_h = img.size
                idle.append(ctk.CTkImage(img, size=(self.real_w, self.real_h)))
        
        # Cargar BITS (Explosión)
        if os.path.exists(path_bits):
            files = sorted([f for f in os.listdir(path_bits) if f.endswith('.png')], key=lambda x: int(x.split('_')[-1].split('.')[0]))
            for f in files:
                img = Image.open(os.path.join(path_bits, f)).convert("RGBA")
                bits.append(ctk.CTkImage(img, size=(self.real_w, self.real_h)))

        self.load_queue.put((idle, bits))

    def process_load_queue(self):
        if not self.load_queue.empty():
            idle, bits = self.load_queue.get()
            if idle:
                self.idle_frames = idle
                self.effect_bits_frames = bits
                
                # Ajustar geometría al tamaño real si es necesario
                if hasattr(self, 'real_w'):
                    self.img_w, self.img_h = self.real_w, self.real_h
                    self.geometry(f"{self.img_w}x{self.img_h}")
                    self.console_h = int(self.img_h * 0.5)
                    self.console_y_visible = self.img_h - self.console_h - 20
                    self.console_frame.configure(width=int(self.img_w*0.9), height=self.console_h)
                
                self.assets_loaded = True
                self.label_alt.configure(text="")
                self.log(">> Renderizado HD Completo. Alt en línea.")
        else:
            self.after(100, self.process_load_queue)

    def animate_loop(self):
        if self.assets_loaded and not self.playing_effect:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.idle_frames)
            self.label_alt.configure(image=self.idle_frames[self.current_frame_idx])
            
            # Respiración de opacidad
            pulse = math.sin(time.time())
            self.attributes("-alpha", max(0.90, min(1.0, OPACIDAD_BASE + pulse*0.02)))
            
        self.after(self.frame_delay, self.animate_loop)

    # --- INTERACCIÓN ---
    def on_press(self, e): self.start_x, self.start_y = e.x, e.y
    def on_drag(self, e):
        nx = self.winfo_x() + (e.x - self.start_x)
        ny = self.winfo_y() + (e.y - self.start_y)
        self.geometry(f"+{nx}+{ny}")
    def on_release(self, e):
        if abs(e.x - self.start_x) < 5 and abs(e.y - self.start_y) < 5:
            self.check_hitbox(e.x, e.y)

    def check_hitbox(self, x, y):
        # Hitboxes escaladas (28%, 72%)
        target_lx = self.img_w * 0.28
        target_rx = self.img_w * 0.72
        target_y = self.img_h * 0.55
        radius = 120 

        if math.hypot(x - target_lx, y - target_y) < radius:
            self.trigger_bits_explosion()
        elif math.hypot(x - target_rx, y - target_y) < radius:
            self.log(">> Módulo de Voz: Acceso concedido.")

    def trigger_bits_explosion(self):
        if not self.effect_bits_frames: 
            self.toggle_console()
            return

        self.playing_effect = True
        self.log(">> Desencriptando interfaz visual...")
        
        def play_burst(idx):
            if idx < len(self.effect_bits_frames):
                self.label_alt.configure(image=self.effect_bits_frames[idx])
                self.after(20, lambda: play_burst(idx + 1))
            else:
                self.playing_effect = False
                self.toggle_console()

        play_burst(0)

    def toggle_console(self):
        target = self.console_y_visible if not self.console_visible else self.console_y_hidden
        self.console_visible = not self.console_visible
        self.animate_console(target)

    def animate_console(self, target):
        diff = target - self.console_y
        if abs(diff) < 2:
            self.console_y = target
            self.console_frame.place(y=int(target))
            return
        self.console_y += diff * 0.15
        self.console_frame.place(y=int(self.console_y))
        self.after(16, lambda: self.animate_console(target))

    def log(self, msg):
        try:
            self.console.configure(state="normal")
            self.console.insert("end", f"> {msg}\n")
            self.console.see("end")
            self.console.configure(state="disabled")
        except: pass

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = LucySpectralUI()
    app.mainloop()
