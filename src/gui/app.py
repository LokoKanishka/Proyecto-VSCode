import customtkinter as ctk
from src.gui.components.sidebar import Sidebar
from src.gui.components.chat_area import ChatArea
from src.gui.components.config_panel import ConfigPanel
from src.engine.ollama_engine import OllamaEngine

class LucyStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LUCY Studio - Cyberpunk Edition")
        self.geometry("1280x720")
        
        # Configurar Grid Principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Inicializar Motor IA
        self.engine = OllamaEngine()

        # 1. SIDEBAR (Izquierda) - Ya no pasamos width=70
        self.sidebar = Sidebar(self, callback_new_chat=self.new_chat)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # 2. CHAT AREA (Centro)
        self.chat_area = ChatArea(self, engine=self.engine)
        self.chat_area.grid(row=0, column=1, sticky="nsew")

        # 3. CONFIG PANEL (Derecha)
        self.config_panel = ConfigPanel(self)
        self.config_panel.grid(row=0, column=2, sticky="nsew")

    def new_chat(self):
        # Limpiar historial visual y de memoria
        self.chat_area.chat_history = []
        for widget in self.chat_area.chat_history_frame.winfo_children():
            widget.destroy()
        print("Chat reseteado")

if __name__ == "__main__":
    app = LucyStudioApp()
    app.mainloop()
