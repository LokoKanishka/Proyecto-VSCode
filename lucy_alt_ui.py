import customtkinter as ctk
from PIL import Image, ImageTk, ImageFont
import threading
import queue
import time
import sys
import os
import math

# --- CONFIGURACIÓN DEL PROYECTO ---
# Aseguramos que el script pueda encontrar el paquete lucy_voice
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Intentar importar backend
try:
    import loguru
    from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig
    BACKEND_AVAILABLE = True
except ImportError as e:
    # print(f"⚠️ Alerta: Backend no encontrado ({e}). Modo UI Demo.")
    BACKEND_AVAILABLE = False

# --- CONSTANTES VISUALES CYBERPUNK ---
COLOR_TEXTO_PRINCIPAL = "#00F0FF"  # Cian brillante
COLOR_TEXTO_SECUNDARIO = "#FF003C" # Rojo neón (para errores/sistema)
COLOR_FONDO = "#050505"            # Casi negro
COLOR_BORDE_CONSOLA = "#00A3A3"    # Cian más oscuro para bordes
OPACIDAD_ESPECTRAL_BASE = 0.92
ANCHO_VENTANA = 600
ALTO_IMAGEN = 535
ALTO_TOTAL = 780 # Espacio para consola desplegada

# Fuentes preferidas para consola (fallback a genéricas)
FONT_MONO = ("JetBrains Mono", "Fira Code", "Consolas", "Courier New", 13)

class LucySpectralUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Configuración de Ventana "Fantasma"
        self.title("Lucy Alt Projection Interface")
        self.geometry(f"{ANCHO_VENTANA}x{ALTO_TOTAL}")
        self.overrideredirect(True) # Sin bordes del SO
        self.attributes("-topmost", True) # Siempre visible
        self.attributes("-alpha", OPACIDAD_ESPECTRAL_BASE)
        self.configure(fg_color=COLOR_FONDO)
        # Intento de eliminar ícono en barra de tareas (funciona distinto según SO)
        try: self.wm_attributes("-type", "splash")
        except: pass
        
        # 2. Estado y Sincronización
        self.main_queue = queue.Queue() # Cola principal para UI
        self.load_queue = queue.Queue() # Cola para carga de imágenes
        self.is_listening = False
        self.console_visible = False
        self.pipeline = None
        self.voice_thread = None
        self.loading_thread = None
        self.stop_event = threading.Event()
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Props de Animación
        self.anim_frames = []
        self.current_frame_idx = 0
        self.fps = 24
        self.frame_delay = int(1000 / self.fps)
        self.assets_loaded = False

        # 3. Inicialización de Componentes
        self.setup_ui_structure()
        self.setup_console()
        
        # Iniciar carga de assets en segundo plano
        self.start_async_loading()

        # Iniciar backend si está disponible
        if BACKEND_AVAILABLE:
            threading.Thread(target=self.init_backend_thread, daemon=True).start()
        else:
            self.log_to_console("Backend no detectado. Modo simulación visual.", "system")
        
        # 4. Iniciar Bucles Principales
        self.process_main_queue()
        self.animate_loop()

    def setup_ui_structure(self):
        """Configura los contenedores principales"""
        # Frame principal para la imagen (Avatar)
        self.avatar_frame = ctk.CTkFrame(self, width=ANCHO_VENTANA, height=ALTO_IMAGEN, fg_color=COLOR_FONDO)
        self.avatar_frame.place(x=0, y=0)
        
        # Label para mostrar la animación o el mensaje de carga
        self.label_alt = ctk.CTkLabel(self.avatar_frame, text="INICIALIZANDO MATRIZ...", 
                                      text_color=COLOR_TEXTO_PRINCIPAL, font=FONT_MONO,
                                      width=ANCHO_VENTANA, height=ALTO_IMAGEN)
        self.label_alt.pack()
        
        # Bindings para interacción y arrastre
        # Importante: bind al label y al frame para asegurar captura
        for widget in [self.avatar_frame, self.label_alt]:
            widget.bind("<ButtonPress-1>", self.on_mouse_press)
            widget.bind("<ButtonRelease-1>", self.on_mouse_release)
            widget.bind("<B1-Motion>", self.on_mouse_drag)

    def setup_console(self):
        """Configura la consola deslizante 'Thought Box'"""
        self.console_height = 200
        self.console_y_hidden = ALTO_TOTAL + 10 # Escondida fuera de vista
        self.console_y_visible = ALTO_IMAGEN - 20 # Superpuesta ligeramente
        self.console_current_y = self.console_y_hidden

        self.console_frame = ctk.CTkFrame(self, fg_color=COLOR_FONDO, corner_radius=12, 
                                          border_width=2, border_color=COLOR_BORDE_CONSOLA, 
                                          width=ANCHO_VENTANA - 80, height=self.console_height)
        
        # Colocación inicial (escondida)
        self.console_frame.place(x=40, y=self.console_current_y)

        self.console = ctk.CTkTextbox(self.console_frame, fg_color=COLOR_FONDO, text_color=COLOR_TEXTO_PRINCIPAL, 
                                      font=FONT_MONO, wrap="word", activate_scrollbars=False,
                                      border_spacing=10)
        self.console.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_to_console("RED NEURONAL ESPECTRAL v2.1 ONLINE.", "system")
        self.log_to_console("Esperando sincronización de assets...")

    # --- GESTIÓN DE CARGA ASÍNCRONA ---
    def start_async_loading(self):
        """Inicia el hilo de carga de imágenes"""
        self.loading_thread = threading.Thread(target=self._load_assets_thread, daemon=True)
        self.loading_thread.start()

    def _load_assets_thread(self):
        """Hilo secundario: Carga imágenes de disco a memoria"""
        project_dir = os.path.dirname(os.path.abspath(__file__))
        anim_dir = os.path.join(project_dir, "assets/figurita_loop")
        loaded_frames = []

        try:
            # Intentar cargar secuencia
            if os.path.exists(anim_dir):
                for i in range(120):
                    f_path = os.path.join(anim_dir, f"alt_fig_{i}.png")
                    if os.path.exists(f_path):
                        pil_img = Image.open(f_path).convert("RGBA")
                        # Crear CTkImage en el hilo secundario es seguro generalmente
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(ANCHO_VENTANA, ALTO_IMAGEN))
                        loaded_frames.append(ctk_img)
                        # Opcional: reportar progreso a la consola (puede saturar)
                        # if i % 20 == 0: self.main_queue.put(("info", f"Cargando memoria visual: {int((i/120)*100)}%"))
            
            # Fallback si falla la secuencia
            if not loaded_frames:
                fb_path = os.path.join(project_dir, "alt_figurita_base.png")
                if os.path.exists(fb_path):
                     pil_img = Image.open(fb_path).convert("RGBA")
                     ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(ANCHO_VENTANA, ALTO_IMAGEN))
                     loaded_frames.append(ctk_img)
                     self.main_queue.put(("system", "Alerta: Usando imagen base de respaldo."))

            if loaded_frames:
                # Enviar frames cargados a la cola principal
                self.load_queue.put(loaded_frames)
            else:
                self.main_queue.put(("error", "Fallo crítico: No se encontraron assets visuales."))

        except Exception as e:
             self.main_queue.put(("error", f"Error en carga de assets: {e}"))

    # --- BUCLES Y PROCESAMIENTO PRINCIPAL (MAIN THREAD) ---
    def process_main_queue(self):
        """Procesa mensajes de otros hilos en el hilo principal UI"""
        # 1. Revisar mensajes de sistema/backend
        try:
            while not self.main_queue.empty():
                level, msg = self.main_queue.get_nowait()
                self.log_to_console(msg, level)
        except queue.Empty: pass

        # 2. Revisar si terminó la carga de imágenes
        try:
            if not self.assets_loaded and not self.load_queue.empty():
                frames = self.load_queue.get_nowait()
                self.anim_frames = frames
                self.assets_loaded = True
                self.label_alt.configure(text="", image=self.anim_frames[0]) # Limpiar texto de carga y poner primer frame
                self.log_to_console("Sincronización visual completa.", "system")
                if BACKEND_AVAILABLE:
                     self.log_to_console(">> Toca la esfera DERECHA para iniciar enlace vocal.", "info")
        except queue.Empty: pass

        self.after(100, self.process_main_queue)

    def animate_loop(self):
        """Ciclo de animación visual (solo si los assets están listos)"""
        if self.assets_loaded and self.anim_frames:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.anim_frames)
            self.label_alt.configure(image=self.anim_frames[self.current_frame_idx])
            
            # Efecto de transparencia pulsante (Holograma)
            pulse = math.sin(time.time() * 2.0) # Velocidad del pulso
            current_alpha = OPACIDAD_ESPECTRAL_BASE + (pulse * 0.03)
            # Mantener dentro de rangos sensatos
            self.attributes("-alpha", min(0.98, max(0.88, current_alpha)))
            
        # Mantener el bucle independientemente de si hay assets o no
        self.after(self.frame_delay, self.animate_loop)

    # --- INTERACCIÓN Y ARRASTRE (MEJORADO) ---
    def on_mouse_press(self, event):
        """Captura la posición inicial para el arrastre y detecta clics"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_mouse_release(self, event):
        """Determina la acción al soltar el clic (si no hubo mucho arrastre)"""
        # Si el ratón se movió muy poco, considéralo un clic
        if abs(event.x - self.drag_start_x) < 5 and abs(event.y - self.drag_start_y) < 5:
            self.handle_click_action(event.x)

    def on_mouse_drag(self, event):
        """Calcula y aplica el nuevo posicionamiento de la ventana"""
        # Calcular el delta del movimiento
        deltax = event.x - self.drag_start_x
        deltay = event.y - self.drag_start_y
        # Obtener posición actual y sumar el delta
        new_x = self.winfo_x() + deltax
        new_y = self.winfo_y() + deltay
        self.geometry(f"+{new_x}+{new_y}")

    def handle_click_action(self, x_pos):
        """Zonas de detección de clic basadas en la coordenada X"""
        # Punto medio aproximado de la imagen de 600px
        CENTER_X = ANCHO_VENTANA // 2 
        
        if x_pos < CENTER_X:
            # ZONA IZQUIERDA: Consola
            self.toggle_console()
        else:
            # ZONA DERECHA: Voz (Avatar)
            self.on_avatar_interaction()

    # --- GESTIÓN DE LA CONSOLA (ANIMACIÓN SUAVIZADA) ---
    def toggle_console(self):
        target = self.console_y_visible if not self.console_visible else self.console_y_hidden
        self.console_visible = not self.console_visible
        
        # Efecto visual: cambiar borde cuando está activa
        if self.console_visible:
            self.console_frame.configure(border_color=COLOR_TEXTO_PRINCIPAL)
        else:
            self.console_frame.configure(border_color=COLOR_BORDE_CONSOLA)
            
        self.animate_console_slide(target)

    def animate_console_slide(self, target_y):
        """Animación con efecto 'ease-out' para suavidad"""
        diff = target_y - self.console_current_y
        
        # Si estamos muy cerca, terminar la animación
        if abs(diff) < 1:
            self.console_current_y = target_y
            self.console_frame.place(y=int(self.console_current_y))
            return

        # Factor de suavizado (0.2 = rápido, 0.05 = lento)
        step = diff * 0.15
        # Asegurar movimiento mínimo para evitar estancamiento
        if step > 0 and step < 1: step = 1
        if step < 0 and step > -1: step = -1
            
        self.console_current_y += step
        self.console_frame.place(y=int(self.console_current_y))
        
        # Continuar animación (más rápido que el bucle principal)
        self.after(16, lambda: self.animate_console_slide(target_y))

    def log_to_console(self, message, level="info"):
        self.console.configure(state="normal")
        
        prefix = "» "
        colors = {"info": COLOR_TEXTO_PRINCIPAL, "system": "#AAAAAA", "error": COLOR_TEXTO_SECUNDARIO}
        tag = level
        
        self.console.tag_config(tag, foreground=colors.get(level, COLOR_TEXTO_PRINCIPAL))
        self.console.insert("end", f"{prefix}{message}\n", tag)
        self.console.see("end")
        self.console.configure(state="disabled")

        # Auto-abrir si es importante
        if not self.console_visible and (level == "error" or level == "system"):
             if self.assets_loaded: # Solo auto-abrir si ya cargó la UI
                self.toggle_console()

    # --- BACKEND Y VOZ ---
    def init_backend_thread(self):
        """Hilo de inicialización del pipeline de IA"""
        try:
            config = LucyPipelineConfig()
            self.pipeline = LucyVoicePipeline(config)
            self.main_queue.put(("system", "Vínculo neuronal establecido."))
        except Exception as e:
            self.main_queue.put(("error", f"Fallo en núcleo IA: {e}"))

    def on_avatar_interaction(self):
        if not BACKEND_AVAILABLE:
            self.log_to_console("Módulo de voz no instalado.", "error")
            self.toggle_console()
            return
        
        if self.is_listening:
            self.stop_listening_sequence()
        else:
            self.start_listening_sequence()

    def start_listening_sequence(self):
        if self.voice_thread and self.voice_thread.is_alive(): return
        if not self.pipeline:
             self.log_to_console("El pipeline aún no está listo.", "system")
             return

        self.is_listening = True
        self.stop_event.clear()
        self.log_to_console("Abriendo canal de escucha...", "info")
        # Cambiar color del borde de la consola para indicar estado "activo"
        self.console_frame.configure(border_color="#FFCC00") # Amarillo/Dorado activo
        if not self.console_visible: self.toggle_console()
        
        self.voice_thread = threading.Thread(target=self.voice_process_loop, daemon=True)
        self.voice_thread.start()

    def stop_listening_sequence(self):
        self.is_listening = False
        self.stop_event.set()
        self.log_to_console("Cerrando canal.", "system")
        # Restaurar color de consola
        self.console_frame.configure(border_color=COLOR_BORDE_CONSOLA if not self.console_visible else COLOR_TEXTO_PRINCIPAL)

    def voice_process_loop(self):
        """Bucle del hilo de voz"""
        while not self.stop_event.is_set():
            try:
                # Duración ajustada para ser más responsiva
                should_stop = self.pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)
                if should_stop or self.stop_event.is_set():
                    break
            except Exception as e:
                self.main_queue.put(("error", f"Interferencia vocal: {e}"))
                break
        
        self.main_queue.put(("system", "Ciclo de interacción finalizado."))
        self.stop_listening_sequence()

if __name__ == "__main__":
    # Configuración global de CTk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue") # Tema base, lo sobrescribimos manualmente
    
    app = LucySpectralUI()
    # Centrar la ventana al inicio
    ws = app.winfo_screenwidth()
    hs = app.winfo_screenheight()
    x = (ws/2) - (ANCHO_VENTANA/2)
    y = (hs/2) - (ALTO_TOTAL/2)
    app.geometry('%dx%d+%d+%d' % (ANCHO_VENTANA, ALTO_TOTAL, x, y))
    
    app.mainloop()
