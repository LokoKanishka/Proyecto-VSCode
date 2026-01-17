import customtkinter as ctk
import threading
from src.gui.components.message_bubble import MessageBubble

# Intentar importar el puente de voz, usar dummy si falla
try:
    from src.engine.voice_bridge import LucyVoiceBridge
except ImportError:
    class LucyVoiceBridge:
        def start_listening_loop(self, callback): pass
        def stop_listening(self): pass
        def say(self, text): pass

class ChatArea(ctk.CTkFrame):
    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        self.chat_history = []
        self.voice_bridge = LucyVoiceBridge()
        self.is_listening = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. HISTORIAL
        self.chat_history_frame = ctk.CTkScrollableFrame(self, label_text="Chat History")
        self.chat_history_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 0))

        # 2. BARRA INFERIOR
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=20)
        self.input_frame.grid_columnconfigure(1, weight=1)

        # A. BOTON MICROFONO
        self.mic_btn = ctk.CTkButton(self.input_frame, text="🎙️", width=50, height=50, 
                                     fg_color="#cc0000", hover_color="#ff003c", 
                                     command=self.toggle_voice)
        self.mic_btn.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # B. CAJA TEXTO
        self.entry_box = ctk.CTkEntry(self.input_frame, placeholder_text="Escribe aquí...", height=50, font=("Roboto Mono", 14))
        self.entry_box.grid(row=0, column=1, sticky="ew", padx=10)
        self.entry_box.bind("<Return>", self.send_message)

        # C. BOTON SEND
        self.send_btn = ctk.CTkButton(self.input_frame, text="SEND", width=80, height=50, command=self.send_message)
        self.send_btn.grid(row=0, column=2, padx=(10, 0), sticky="e")

        # Iniciar voz
        try:
            threading.Thread(target=self.voice_bridge.start_listening_loop, args=(self.on_voice_input,), daemon=True).start()
        except: pass

    def toggle_voice(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.mic_btn.configure(fg_color="#00ff00", text="👂")
        else:
            self.mic_btn.configure(fg_color="#cc0000", text="🎙️")

    def on_voice_input(self, text):
        if text:
            self.entry_box.delete(0, "end")
            self.entry_box.insert(0, text)

    def send_message(self, event=None):
        user_text = self.entry_box.get()
        if not user_text.strip(): return

        self.display_message("You", user_text)
        self.chat_history.append({"role": "user", "content": user_text})
        self.entry_box.delete(0, "end")

        threading.Thread(target=self.process_ai_response, args=(user_text,)).start()

    def process_ai_response(self, user_text):
        if self.engine:
            response = self.engine.generate_response(user_text, self.chat_history)
            self.master.after(0, self.display_message, "LUCY", response)
            self.chat_history.append({"role": "assistant", "content": response})

    def display_message(self, sender, text):
        try:
            bubble = MessageBubble(self.chat_history_frame, text=text, is_user=(sender == "You"))
            bubble.pack(pady=5, padx=10, fill="x", anchor="e" if sender == "You" else "w")
        except:
            lbl = ctk.CTkLabel(self.chat_history_frame, text=f"{sender}: {text}", wraplength=400, justify="left")
            lbl.pack(pady=5, anchor="w")
