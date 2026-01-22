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
        
        # PALABRAS CLAVE PARA DORMIR
        self.sleep_triggers = [
            "dormí", "dormite", "duérmete", "duermete", 
            "descansa", "apágate", "silencio", "hasta mañana",
            "stop", "basta"
        ]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(
            self, font=("Consolas", 14), text_color="#00ff41", fg_color="#000000"
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_display.insert("0.0", ">>> SISTEMA LUCY ONLINE (COMANDOS DE VOZ ACTIVOS)_\n")
        self.chat_display.configure(state="disabled")

        self.record_btn = ctk.CTkButton(
            self,
            text="🔴 INICIAR CONVERSACIÓN",
            font=("Consolas", 14, "bold"),
            fg_color="#330000",
            hover_color="#550000",
            height=50,
            command=self.toggle_conversation
        )
        self.record_btn.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def toggle_conversation(self):
        if not self.is_running:
            self.is_running = True
            self.record_btn.configure(text="🟢 ESCUCHANDO... (Di 'Lucy Dormí' para cortar)", fg_color="#004400")
            threading.Thread(target=self._conversation_loop, daemon=True).start()
        else:
            self.stop_conversation_logic()

    def stop_conversation_logic(self):
        """Lógica centralizada para detener el bucle"""
        self.is_running = False
        self.voice_bridge.stop_listening()
        self.after(0, lambda: self.record_btn.configure(text="🔴 DETENIENDO...", fg_color="#555500"))

    def _conversation_loop(self):
        print("⚡ [LOOP] Iniciado.")
        
        while self.is_running:
            # 1. ESCUCHAR
            user_text = self.voice_bridge.listen_continuous()
            
            if not self.is_running: break
            
            if user_text:
                self.safe_write_chat(f"TÚ: {user_text}")
                
                # --- 2. VERIFICAR COMANDO "DORMÍ" ---
                # Pasamos a minúsculas y chequeamos si alguna palabra clave está presente
                text_clean = user_text.lower()
                is_sleep_command = any(trigger in text_clean for trigger in self.sleep_triggers)
                
                if is_sleep_command:
                    print(f"💤 Comando detectado: {user_text}")
                    self.safe_write_chat("LUCY: [SISTEMA EN REPOSO]")
                    
                    # Respuesta final antes de morir
                    self.voice_bridge.say("Entendido. Quedo a la espera.")
                    
                    # Cortamos el bucle
                    self.is_running = False
                    break
                # ------------------------------------

                # 3. PENSAR Y HABLAR (Si no fue comando de dormir)
                if self.engine:
                    self.safe_write_chat("LUCY: ...")
                    full_response = ""
                    try:
                        for chunk in self.engine.generate_response(user_text):
                            full_response += chunk
                        
                        self.safe_write_chat(f"\nLUCY: {full_response}\n")
                        self.voice_bridge.say(full_response)
                        
                    except Exception as e:
                        print(f"Error IA: {e}")

            time.sleep(0.2)

        # Restaurar botón al salir del bucle
        self.after(0, lambda: self.record_btn.configure(text="🔴 INICIAR CONVERSACIÓN", fg_color="#330000"))
        print("⚡ [LOOP] Terminado.")

    def safe_write_chat(self, msg):
        self.after(0, lambda: self._write_chat_impl(msg))

    def _write_chat_impl(self, msg):
        try:
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", f"{msg}\n")
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
        except: pass
