import customtkinter as ctk
from .components.sidebar import Sidebar
from .components.config_panel import ConfigPanel
from .components.chat_area import ChatArea
from .components.audio_visualizer import AudioVisualizer
from src.engine.audio_processor import AudioProcessor
from src.engine.voice_bridge import LucyVoiceBridge

class LucyStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Theme setup: Night City
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("green") # Neón base
        
        # Override some colors for Cyberpunk feel
        self.configure(fg_color="#050505") # Void Black background

        # Window configuration
        self.title("LUCY Studio - Cyberpunk Edition")
        self.geometry("1200x800")
        
        # Initialize Audio Processor
        self.audio_processor = AudioProcessor()
        self.audio_processor.start()
        
        # Initialize Voice Bridge (STT/TTS)
        self.voice_bridge = LucyVoiceBridge()
        
        # Grid layout: 3 columns (Sidebar, Chat, Config)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=300) # Force sidebar width
        self.grid_columnconfigure(1, weight=1) # Chat area expands
        
        # 1. Sidebar (Left) - Extended with Visualizer
        self.sidebar_container = ctk.CTkFrame(self, width=300, fg_color="#0d0d0d", corner_radius=0)
        self.sidebar_container.grid(row=0, column=0, sticky="nsew")
        self.sidebar_container.grid_rowconfigure(0, weight=1)
        self.sidebar_container.grid_columnconfigure(0, weight=1)
        
        self.sidebar = Sidebar(self.sidebar_container, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Add a subtle 1px border between panels
        self.sidebar_container.configure(border_width=1, border_color="#1f1f1f")
        
        # 2. Chat Area (Center)
        # Pasamos el voice_bridge unificado para evitar doble carga de modelos
        self.chat_area = ChatArea(self, voice_bridge=self.voice_bridge, fg_color="#050505")
        self.chat_area.grid(row=0, column=1, sticky="nsew")
        
        # 3. Config Panel (Right)
        self.config_panel = ConfigPanel(self, engine=self.chat_area.engine, width=300, fg_color="#0d0d0d")
        self.config_panel.grid(row=0, column=2, sticky="nsew")
        self.config_panel.configure(border_width=1, border_color="#1f1f1f")
        
    def start(self):
        """Starts the main event loop."""
        try:
            self.mainloop()
        finally:
            self.audio_processor.stop()
            if hasattr(self, 'voice_bridge'):
                self.voice_bridge.stop_listening()

    def on_voice_input(self, text):
        """Callback for Speech-to-Text."""
        print(f"[App] Captured Voice: {text}")
        # Inject into chat entry and trigger send
        def _update_ui():
            self.chat_area.entry_box.delete(0, "end")
            self.chat_area.entry_box.insert(0, text)
            self.chat_area.on_send_press()
            
        self.after(0, _update_ui)
