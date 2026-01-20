import customtkinter as ctk
import threading
from PIL import Image
import os
from src.gui.components.message_bubble import MessageBubble
from src.gui.components.audio_visualizer import AudioVisualizer
from src.engine.voice_bridge import LucyVoiceBridge

class ChatArea(ctk.CTkFrame):
    def __init__(self, master, engine=None, audio_processor=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine 
        self.audio_processor = audio_processor
        self.voice_bridge = LucyVoiceBridge(audio_processor=self.audio_processor)
        self.is_mic_active = False
        self.chat_history = []
        
        # Fondo Industrial
        self.configure(fg_color="#080808") 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=0) 
        
        # Frame del Historial
        self.history_container = ctk.CTkFrame(
            self, 
            fg_color="#000000", 
            border_color="#333333", 
            border_width=2,
            corner_radius=0
        )
        self.history_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.history_container.grid_columnconfigure(0, weight=1)
        self.history_container.grid_rowconfigure(0, weight=1)

        self.chat_history_frame = ctk.CTkScrollableFrame(
            self.history_container, 
            label_text="[ REMOTE_DATA_LINK_16.4 ]",
            label_font=("Consolas", 14, "bold"),
            fg_color="transparent",
            label_fg_color="#00ff41", 
            label_text_color="#000000",
            corner_radius=0
        )
        self.chat_history_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- ZONA DE CONTROL (Estilo Gemini) ---
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.control_frame.grid_columnconfigure(0, weight=1)

        # Visualizador de Ondas (Fondo para el botón)
        self.viz_container = ctk.CTkFrame(self.control_frame, fg_color="transparent", height=120)
        self.viz_container.grid(row=0, column=0, sticky="ew")
        
        if self.audio_processor:
            self.visualizer = AudioVisualizer(self.viz_container, self.audio_processor, height=120)
            self.visualizer.pack(fill="both", expand=True)

        # Micrófono Flotante
        img_path = os.path.abspath("assets/mic_style.png")
        self.mic_image = None
        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                self.mic_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(100, 100))
            except: pass

        self.mic_btn = ctk.CTkButton(
            self.viz_container, 
            text="START" if not self.mic_image else "", 
            image=self.mic_image,
            width=110, height=110, 
            fg_color="transparent", 
            hover_color="#111111",
            border_width=0,
            corner_radius=55,
            command=self.toggle_voice_loop
        )
        # Lo ponemos justo en el centro del visualizador
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        # Entrada manual
        self.entry_box = ctk.CTkEntry(
            self.control_frame, 
            placeholder_text=">>> CMD_OVERRIDE...", 
            fg_color="#000000", 
            text_color="#00ff41",
            border_color="#00ff41",
            border_width=1,
            font=("Consolas", 14),
            height=40,
            corner_radius=2
        )
        self.entry_box.grid(row=1, column=0, sticky="ew", pady=(15,0))
        self.entry_box.bind("<Return>", self.send_manual_message)

    def toggle_voice_loop(self):
        if not self.is_mic_active:
            self.is_mic_active = True
            self.mic_btn.configure(border_width=2, border_color="#ff0000")
            def on_voice_text(text):
                self.master.after(0, lambda: self.display_message("USER", text))
                self.master.after(0, lambda: self.process_ai_response_thread(text))
            threading.Thread(target=self.voice_bridge.start_listening_loop, args=(on_voice_text,), daemon=True).start()
        else:
            self.is_mic_active = False
            self.voice_bridge.stop_listening()
            self.mic_btn.configure(border_width=0)

    def send_manual_message(self, event=None):
        text = self.entry_box.get()
        if not text: return
        self.entry_box.delete(0, "end")
        self.display_message("USER", text)
        threading.Thread(target=self.process_ai_response_thread, args=(text,), daemon=True).start()

    def process_ai_response_thread(self, user_text):
        full_response = ""
        self.master.after(0, lambda: self.display_message("LUCY", ">>> ANALYZING_DATASTREAM...", is_stream=True))
        try:
            if not self.engine: return
            if not self.chat_history:
                self.chat_history.append({"role": "system", "content": "Eres Lucy, asistente Cyberpunk. SIEMPRE EN ESPAÑOL. Breve."})
            self.chat_history.append({"role": "user", "content": user_text})

            for chunk in self.engine.generate_response(self.chat_history): 
                full_response += chunk
                self.master.after(0, lambda c=full_response: self.update_last_message(c))
            
            self.chat_history.append({"role": "assistant", "content": full_response})
            if full_response:
                self.voice_bridge.say(full_response)
        except Exception as e:
            self.master.after(0, lambda: self.update_last_message(f"SYSTEM_FATAL_ERROR: {e}"))

    def display_message(self, sender, text, is_stream=False):
        bubble = MessageBubble(self.chat_history_frame, text=text, is_user=(sender == "USER"))
        bubble.pack(pady=10, padx=15, fill="x", anchor="e" if sender == "USER" else "w")
        self.master.after(100, lambda: self.chat_history_frame._parent_canvas.yview_moveto(1.0))

    def update_last_message(self, new_text):
        widgets = self.chat_history_frame.winfo_children()
        if widgets: widgets[-1].update_text(new_text)
