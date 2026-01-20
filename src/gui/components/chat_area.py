import customtkinter as ctk
from src.engine.voice_bridge import LucyVoiceBridge
import threading

class ChatArea(ctk.CTkFrame):
    def __init__(self, master, engine=None, audio_processor=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        
        # --- CORRECCIÓN AQUÍ ---
        # El nuevo oído es autónomo, no necesita argumentos.
        self.voice_bridge = LucyVoiceBridge()
        # -----------------------

        self.is_recording = False

        # Configuración de Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Área de Chat (Scroll)
        self.chat_display = ctk.CTkTextbox(
            self, 
            font=("Consolas", 14), 
            text_color="#00ff41",
            fg_color="#000000",
            border_color="#003300",
            border_width=2
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_display.insert("0.0", ">>> SISTEMA LUCY ONLINE_\n")
        self.chat_display.configure(state="disabled")

        # Botón REC (Estilo Walkie-Talkie)
        self.record_btn = ctk.CTkButton(
            self,
            text="🔴 REC (OFF)",
            font=("Consolas", 14, "bold"),
            fg_color="#330000",
            hover_color="#550000",
            text_color="#ffcccc",
            height=50,
            command=self.toggle_recording
        )
        self.record_btn.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def toggle_recording(self):
        if not self.is_recording:
            # INICIAR GRABACIÓN
            self.is_recording = True
            self.record_btn.configure(
                text="🟢 ESCUCHANDO... (Habla ahora)", 
                fg_color="#004400", 
                hover_color="#006600",
                text_color="#ccffcc"
            )
            # Lanzar hilo de escucha
            threading.Thread(target=self._listen_thread).start()
        else:
            # PARAR MANUALMENTE (Si el usuario quiere cortar antes)
            self.is_recording = False
            self.voice_bridge.stop_listening()
            self.reset_button()

    def _listen_thread(self):
        # Esta función bloquea hasta que detecta silencio o termina el tiempo
        self.voice_bridge.listen_once(self.handle_transcription)
        # Cuando termina de escuchar, reseteamos el botón
        self.after(100, self.reset_button)

    def reset_button(self):
        self.is_recording = False
        self.record_btn.configure(
            text="🔴 REC (OFF)", 
            fg_color="#330000", 
            hover_color="#550000",
            text_color="#ffcccc"
        )

    def handle_transcription(self, text):
        # 1. Mostrar lo que dijiste
        self.write_chat(f"TÚ: {text}")
        
        # 2. Enviar al cerebro (IA)
        if self.engine:
            threading.Thread(target=self._process_ai, args=(text,)).start()

    def _process_ai(self, text):
        response_text = ""
        self.write_chat("LUCY: ...") # Indicador de pensando
        
        # Generar respuesta
        for chunk in self.engine.generate_response(text):
            response_text += chunk
        
        # Mostrar respuesta final
        self.write_chat(f"\nLUCY: {response_text}\n")
        
        # 3. Decirlo en voz alta
        self.voice_bridge.say(response_text)

    def write_chat(self, msg):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"{msg}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
