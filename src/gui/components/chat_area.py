import customtkinter as ctk
from src.engine.voice_bridge import LucyVoiceBridge
import threading
import time

class ChatArea(ctk.CTkFrame):
    def __init__(self, master, engine=None, audio_processor=None, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        self.voice_bridge = LucyVoiceBridge()
        self.is_running = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Chat display
        self.chat_display = ctk.CTkTextbox(
            self, font=("Consolas", 14), text_color="#00ff41", fg_color="#000000"
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_display.insert("0.0", ">>> SISTEMA DE FLUJO ROBUSTO V2.0_\n")
        self.chat_display.configure(state="disabled")

        # Botón
        self.record_btn = ctk.CTkButton(
            self,
            text="🔴 INICIAR (OFF)",
            font=("Consolas", 14, "bold"),
            fg_color="#330000",
            hover_color="#550000",
            height=50,
            command=self.toggle_conversation
        )
        self.record_btn.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def toggle_conversation(self):
        if not self.is_running:
            print("⚡ [UI] Botón INICIAR presionado.")
            self.is_running = True
            self.record_btn.configure(text="🟢 ESCUCHANDO... (No toques nada)", fg_color="#004400")
            threading.Thread(target=self._conversation_loop, daemon=True).start()
        else:
            print("⚡ [UI] Botón DETENER presionado.")
            self.is_running = False
            self.voice_bridge.stop_listening()
            self.record_btn.configure(text="🔴 DETENIENDO...", fg_color="#555500")

    def _conversation_loop(self):
        print("⚡ [HILO] Bucle iniciado.")
        while self.is_running:
            # 1. ESCUCHAR (Bloqueante hasta que haya silencio)
            text = self.voice_bridge.listen_continuous()
            
            # 2. PROCESAR (Prioridad Absoluta)
            # Si escuchó algo, lo procesamos AUNQUE hayan cancelado el bucle.
            if text:
                print(f"⚡ [HILO] Procesando texto: '{text}'")
                self.safe_write_chat(f"TÚ: {text}")
                
                if self.engine:
                    self.safe_write_chat("LUCY: ...")
                    try:
                        full_response = ""
                        for chunk in self.engine.generate_response(text):
                            full_response += chunk
                        
                        self.safe_write_chat(f"\nLUCY: {full_response}\n")
                        self.voice_bridge.say(full_response)
                    except Exception as e:
                        print(f"❌ Error Cerebro: {e}")
                        self.safe_write_chat(f"[ERROR]: {e}")

            # 3. REVISAR SALIDA
            if not self.is_running:
                print("⚡ [HILO] Señal de parada detectada. Saliendo.")
                break

        # Limpieza final
        self.after(0, lambda: self.record_btn.configure(text="🔴 INICIAR (OFF)", fg_color="#330000"))
        print("⚡ [HILO] Bucle terminado.")

    def safe_write_chat(self, msg):
        self.after(0, lambda: self._write_chat_impl(msg))

    def _write_chat_impl(self, msg):
        try:
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", f"{msg}\n")
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
        except: pass
