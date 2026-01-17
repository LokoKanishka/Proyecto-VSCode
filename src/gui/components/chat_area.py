import customtkinter as ctk
import threading
from src.gui.components.message_bubble import MessageBubble
from src.engine.voice_bridge import LucyVoiceBridge

class ChatArea(ctk.CTkFrame):
    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine 
        self.chat_history = []
        self.voice_bridge = LucyVoiceBridge()
        self.is_listening = False

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.chat_history_frame = ctk.CTkScrollableFrame(self, label_text="Chat History")
        self.chat_history_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 0))
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=20)
        self.input_frame.grid_columnconfigure(1, weight=1)

        # Botón Micrófono
        self.mic_btn = ctk.CTkButton(self.input_frame, text="🎙️", width=50, height=50, 
                                     fg_color="#cc0000", hover_color="#ff003c", 
                                     command=self.start_voice)
        self.mic_btn.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Caja de Texto
        self.entry_box = ctk.CTkEntry(self.input_frame, placeholder_text="Escribe aquí...", height=50, font=("Roboto Mono", 14))
        self.entry_box.grid(row=0, column=1, sticky="ew", padx=10)
        self.entry_box.bind("<Return>", self.send_message)
        self.send_btn = ctk.CTkButton(self.input_frame, text="SEND", width=80, height=50, command=self.send_message)
        self.send_btn.grid(row=0, column=2, padx=(10, 0), sticky="e")

    def start_voice(self):
        if self.is_listening: return # Evitar doble clic
        self.is_listening = True
        self.mic_btn.configure(fg_color="#00ff00", text="👂") # Verde
        
        # Lanzar hilo de escucha
        threading.Thread(target=self.voice_bridge.listen_oneshot, 
                         args=(self.on_text_received, self.on_listen_finished), 
                         daemon=True).start()

    def on_text_received(self, text):
        # Callback: Texto detectado -> Poner en caja y enviar
        self.master.after(0, lambda: self._process_voice_input(text))

    def on_listen_finished(self):
        # Callback: Fin de grabación -> Botón Rojo
        self.is_listening = False
        self.master.after(0, lambda: self.mic_btn.configure(fg_color="#cc0000", text="🎙️"))

    def _process_voice_input(self, text):
        self.entry_box.delete(0, "end")
        self.entry_box.insert(0, text)
        # Opcional: Auto-enviar si quieres fluidez total
        # self.send_message()

    def send_message(self, event=None):
        user_text = self.entry_box.get()
        if not user_text.strip(): return
        self.display_message("You", user_text)
        self.chat_history.append({"role": "user", "content": user_text})
        self.entry_box.delete(0, "end")
        threading.Thread(target=self.process_ai_response, args=(user_text,)).start()

    def process_ai_response(self, user_text):
        if self.engine:
            full_response = ""
            self.master.after(0, lambda: self.display_message("LUCY", "", is_stream=True))
            for chunk in self.engine.generate_response(user_text, self.chat_history):
                full_response += chunk
            self.chat_history.append({"role": "assistant", "content": full_response})
            self.voice_bridge.say(full_response)
            self.master.after(0, lambda: self.display_message("LUCY", full_response, update_last=True))

    def display_message(self, sender, text, is_stream=False, update_last=False):
        if update_last:
            widgets = self.chat_history_frame.winfo_children()
            if widgets: widgets[-1].destroy()
        bubble = MessageBubble(self.chat_history_frame, text=text or "...", is_user=(sender == "You"))
        bubble.pack(pady=5, padx=10, fill="x", anchor="e" if sender == "You" else "w")
        self.master.update_idletasks()
        self.chat_history_frame._parent_canvas.yview_moveto(1.0)
