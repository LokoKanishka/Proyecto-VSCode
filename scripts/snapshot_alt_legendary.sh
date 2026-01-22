#!/bin/bash
set -e

# 1. Configuración de directorios
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/alt_snapshot_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
mkdir -p scripts/assets/figurita_loop

echo "💾 Iniciando Protocolo de Salvado: Alt Cunningham V3..."

# 2. Respaldo de seguridad
if [ -f "lucy_alt_ui.py" ]; then
    cp lucy_alt_ui.py "$BACKUP_DIR/lucy_alt_ui.py.bak"
    echo "   >> Backup de UI creado."
fi
if [ -f "generate_figurita_loop.py" ]; then
    cp generate_figurita_loop.py "$BACKUP_DIR/generate_figurita_loop.py.bak"
    echo "   >> Backup de Generador creado."
fi

# 3. Escribiendo la UI "Nivel Legendario" (Asíncrona + Smooth)
cat << 'PYTHON_UI' > lucy_alt_ui.py
import customtkinter as ctk
from PIL import Image, ImageTk, ImageFont
import threading
import queue
import time
import sys
import os
import math

# --- CONFIGURACIÓN DEL PROYECTO ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Intento de backend
try:
    from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

# --- CONSTANTES VISUALES CYBERPUNK ---
COLOR_TEXTO_PRINCIPAL = "#00F0FF"
COLOR_TEXTO_SECUNDARIO = "#FF003C"
COLOR_FONDO = "#050505"
COLOR_BORDE_CONSOLA = "#00A3A3"
OPACIDAD_ESPECTRAL_BASE = 0.92

ANCHO_VENTANA = 600
ALTO_IMAGEN = 535
ALTO_TOTAL = 780 
FONT_MONO = ("JetBrains Mono", "Fira Code", "Consolas", 13)

class LucySpectralUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Lucy Alt Projection Interface")
        self.geometry(f"{ANCHO_VENTANA}x{ALTO_TOTAL}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", OPACIDAD_ESPECTRAL_BASE)
        self.configure(fg_color=COLOR_FONDO)
        
        self.main_queue = queue.Queue()
        self.load_queue = queue.Queue()
        
        self.is_listening = False
        self.console_visible = False
        self.pipeline = None
        
        self.assets_loaded = False
        self.anim_frames = []
        self.current_frame_idx = 0
        self.fps = 24
        self.frame_delay = int(1000 / self.fps)

        self.setup_ui_structure()
        self.setup_console()
        
        # Carga en hilo separado para no congelar la UI al inicio
        self.start_async_loading()
        
        if BACKEND_AVAILABLE:
            threading.Thread(target=self.init_backend_thread, daemon=True).start()
        
        self.process_main_queue()
        self.animate_loop()

    def setup_ui_structure(self):
        self.avatar_frame = ctk.CTkFrame(self, width=ANCHO_VENTANA, height=ALTO_IMAGEN, fg_color=COLOR_FONDO)
        self.avatar_frame.place(x=0, y=0)
        
        self.label_alt = ctk.CTkLabel(
            self.avatar_frame, 
            text="INICIALIZANDO PROYECCIÓN...", 
            text_color=COLOR_TEXTO_PRINCIPAL, 
            font=FONT_MONO,
            width=ANCHO_VENTANA, 
            height=ALTO_IMAGEN
        )
        self.label_alt.pack()
        
        # Bindings para arrastrar la ventana
        for widget in [self.avatar_frame, self.label_alt]:
            widget.bind("<ButtonPress-1>", self.on_mouse_press)
            widget.bind("<ButtonRelease-1>", self.on_mouse_release)
            widget.bind("<B1-Motion>", self.on_mouse_drag)

    def setup_console(self):
        self.console_height = 200
        self.console_y_hidden = ALTO_TOTAL + 10
        self.console_y_visible = ALTO_IMAGEN - 20
        self.console_current_y = self.console_y_hidden
        
        self.console_frame = ctk.CTkFrame(
            self, 
            fg_color=COLOR_FONDO, 
            corner_radius=12,
            border_width=2, 
            border_color=COLOR_BORDE_CONSOLA,
            width=ANCHO_VENTANA - 80, 
            height=self.console_height
        )
        self.console_frame.place(x=40, y=self.console_current_y)
        
        self.console = ctk.CTkTextbox(
            self.console_frame, 
            fg_color=COLOR_FONDO, 
            text_color=COLOR_TEXTO_PRINCIPAL, 
            font=FONT_MONO,
            wrap="word",
            activate_scrollbars=False
        )
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

    def start_async_loading(self):
        threading.Thread(target=self._load_assets_thread, daemon=True).start()

    def _load_assets_thread(self):
        p_dir = os.path.dirname(os.path.abspath(__file__))
        anim_dir = os.path.join(p_dir, "assets/figurita_loop")
        loaded = []
        
        if os.path.exists(anim_dir):
            # Intentamos cargar hasta 120 frames
            for i in range(120):
                f_path = os.path.join(anim_dir, f"alt_fig_{i}.png")
                if os.path.exists(f_path):
                    pil_img = Image.open(f_path).convert("RGBA")
                    loaded.append(ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(ANCHO_VENTANA, ALTO_IMAGEN)))
        
        # Enviamos los frames cargados a la cola principal
        self.load_queue.put(loaded)

    def process_main_queue(self):
        # Verificar si terminó la carga de imágenes
        if not self.assets_loaded and not self.load_queue.empty():
            self.anim_frames = self.load_queue.get_nowait()
            if self.anim_frames:
                self.assets_loaded = True
                self.label_alt.configure(text="", image=self.anim_frames[0])
                self.log_to_console("Sistema visual: EN LÍNEA")
            else:
                self.label_alt.configure(text="ERROR: NO ASSETS FOUND")
        
        self.after(100, self.process_main_queue)

    def animate_loop(self):
        if self.assets_loaded and self.anim_frames:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.anim_frames)
            self.label_alt.configure(image=self.anim_frames[self.current_frame_idx])
            
            # Efecto de respiración en la opacidad
            pulse = math.sin(time.time() * 2.0)
            target_alpha = min(0.98, max(0.88, OPACIDAD_ESPECTRAL_BASE + (pulse * 0.03)))
            self.attributes("-alpha", target_alpha)
            
        self.after(self.frame_delay, self.animate_loop)

    def on_mouse_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_mouse_release(self, event):
        # Si el mouse no se movió mucho, es un click, no un arrastre
        if abs(event.x - self.drag_start_x) < 5 and abs(event.y - self.drag_start_y) < 5:
            self.handle_click_action(event.x)

    def on_mouse_drag(self, event):
        nx = self.winfo_x() + (event.x - self.drag_start_x)
        ny = self.winfo_y() + (event.y - self.drag_start_y)
        self.geometry(f"+{nx}+{ny}")

    def handle_click_action(self, x):
        # Zona izquierda: Consola / Zona derecha: Interacción futura
        if x < ANCHO_VENTANA // 2:
            self.toggle_console()
        else:
            self.log_to_console("Enlace neuronal: ESTABLE (Click derecho)")

    def toggle_console(self):
        target = self.console_y_visible if not self.console_visible else self.console_y_hidden
        self.console_visible = not self.console_visible
        self.animate_console_slide(target)

    def animate_console_slide(self, target):
        # Interpolación suave (Lerp)
        diff = target - self.console_current_y
        if abs(diff) < 1:
            self.console_current_y = target
            self.console_frame.place(y=int(self.console_current_y))
            return
        
        self.console_current_y += diff * 0.15
        self.console_frame.place(y=int(self.console_current_y))
        self.after(16, lambda: self.animate_console_slide(target))

    def log_to_console(self, msg, level="info"):
        self.console.configure(state="normal")
        self.console.insert("end", f"» {msg}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def init_backend_thread(self):
        # Stub para futura integración con LucyVoicePipeline
        pass

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = LucySpectralUI()
    app.mainloop()
PYTHON_UI

# 4. Escribiendo el generador (para pasar a Gemini por las piernas)
cat << 'PYTHON_GEN' > generate_figurita_loop.py
import os
import math
from PIL import Image

def generate_figurita_loop(input_path, output_dir, num_frames=120):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    pixels = img.load()
    
    hair_region = height * 0.40     # Pelo
    tornado_region = height * 0.70  # Piernas / Tornado
    
    print(f"Generando {num_frames} cuadros espectrales...")

    for f in range(num_frames):
        new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        new_pixels = new_img.load()
        
        # Fase cíclica 0 a 2pi
        phase = (f / num_frames) * 2 * math.pi
        
        for y in range(height):
            # --- LÓGICA DE DEFORMACIÓN ---
            
            if y < hair_region:
                # Movimiento del pelo (suave, flotante)
                intensity = (1.0 - (y / hair_region)) * 10.0
                shift_x = math.sin(y * 0.04 + phase) * intensity
                shift_y = math.sin(phase + y * 0.02) * 2.0
            
            elif y > tornado_region:
                # --- AQUÍ ESTÁ EL PROBLEMA DE LAS PIERNAS ---
                # TODO: Ajustar esta sección para que las piernas no se "rompan" tanto.
                # Se busca un efecto de desvanecimiento o tornado, no de glitch duro.
                
                dist_from_torso = (y - tornado_region) / (height - tornado_region)
                intensity = dist_from_torso * 8.0
                
                # Movimiento actual (quizás muy rápido o amplio)
                shift_x = math.sin(y * 0.12 + phase * 2) * intensity
                shift_y = math.cos(phase) * 3.0
            
            else:
                # Torso (estático con respiración leve)
                shift_x = math.sin(phase) * 0.4
                shift_y = math.cos(phase * 0.5) * 1.0
            
            # --- MAPEO DE PIXELES ---
            for x in range(width):
                src_x = int(x - shift_x)
                src_y = int(y - shift_y)
                
                if 0 <= src_x < width and 0 <= src_y < height:
                    r, g, b, a = pixels[src_x, src_y]
                    if a > 0:
                        # Efecto de pulso en el brillo
                        pulse = 1.0 + math.sin(phase + (x+y)*0.01) * 0.05
                        new_pixels[x, y] = (
                            min(255, int(r * pulse)), 
                            min(255, int(g * pulse)), 
                            min(255, int(b * pulse)), 
                            a
                        )
        
        new_img.save(os.path.join(output_dir, f"alt_fig_{f}.png"), "PNG")
    
    print(">> Render completado.")

if __name__ == "__main__":
    # Asegurate de tener la imagen base
    generate_figurita_loop("alt_figurita_base.png", "assets/figurita_loop")
PYTHON_GEN

echo "✅ Código asegurado. Checkpoint creado en $BACKUP_DIR"
echo "🛠️ Podés ejecutar 'python3 lucy_alt_ui.py' para probar la nueva UI."
