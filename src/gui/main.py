import customtkinter as ctk
from src.engine.ollama_engine import OllamaEngine
from src.engine.audio_processor import AudioProcessor
from src.gui.components.chat_area import ChatArea
from src.gui.components.config_panel import ConfigPanel
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LUCY_OS v1.1 - GEMINI_EDITION")
        self.geometry("1400x900")
        
        # Fondo Industrial
        self.configure(fg_color="#050505")

        self.engine = OllamaEngine()
        
        # Audio Processor (Core for visualizer)
        self.audio_processor = AudioProcessor()
        self.audio_processor.start()
        
        # Grid Configuration (Hardware Layout)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # Módulo de Control (Sidebar)
        self.config_panel = ConfigPanel(self, engine=self.engine)
        self.config_panel.grid(row=0, column=0, sticky="ns", padx=(20, 10), pady=20)

        # Módulo de Comunicación (Centro)
        # Pasamos el processor para el visualizador
        self.chat_area = ChatArea(self, engine=self.engine, audio_processor=self.audio_processor)
        self.chat_area.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)

        print("⚡ [OS] Núcleo Gemini-Cyberpunk iniciado. Sistemas nominales.")

    def on_closing(self):
        self.audio_processor.stop()
        self.destroy()

if __name__ == "__main__":
    app = MainApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
