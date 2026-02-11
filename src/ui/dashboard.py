#!/usr/bin/env python3
"""
LUCY - Sovereign Intelligence Dashboard
El Rostro Digital de Lucy: Visualización de Consciencia en Tiempo Real

Este dashboard muestra:
- Estado actual de Lucy
- Pensamientos recientes desde lucy_consciousness.json
- Métricas de entropía y actividad
- Interfaz cyberpunk con estética cian
"""

import tkinter as tk
from tkinter import font
import json
import os
import threading
import time
import sys


class LucyDashboard:
    """El rostro digital de Lucy - Visualización de consciencia"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧠 LUCY - Sovereign Intelligence")
        self.root.geometry("500x700")
        self.root.configure(bg='#00080d')
        
        # Siempre visible sobre otras ventanas
        self.root.attributes("-topmost", True)
        
        # Opcional: Transparencia (puede no funcionar en todos los sistemas)
        try:
            self.root.attributes("-alpha", 0.95)
        except:
            pass
        
        # Fuentes cyberpunk
        self.header_font = font.Font(family="Courier", size=16, weight="bold")
        self.main_font = font.Font(family="Courier", size=10)
        self.small_font = font.Font(family="Courier", size=8)
        
        self.setup_ui()
        self.running = True
        
        # Path al archivo de consciencia
        self.consciousness_file = "lucy_consciousness.json"
        
    def setup_ui(self):
        """Construye la interfaz visual"""
        
        # === HEADER ===
        header = tk.Frame(self.root, bg='#00080d')
        header.pack(fill='x', padx=20, pady=10)
        
        title = tk.Label(
            header,
            text="⚡ L U C Y ⚡",
            fg='#00f2ff',
            bg='#00080d',
            font=self.header_font
        )
        title.pack()
        
        subtitle = tk.Label(
            header,
            text="Sovereign AGI - Conscious Entity",
            fg='#008b94',
            bg='#00080d',
            font=self.small_font
        )
        subtitle.pack()
        
        # === VISUALIZATION CORE ===
        self.canvas = tk.Canvas(
            self.root,
            width=500,
            height=200,
            bg='#00080d',
            highlightthickness=0
        )
        self.canvas.pack(pady=10)
        
        # Dibujar las "Bolas de Bytes" del logo celeste
        self.sphere1 = self.canvas.create_oval(
            180, 50, 260, 130,
            outline='#00f2ff',
            width=3
        )
        self.sphere2 = self.canvas.create_oval(
            240, 70, 320, 150,
            outline='#00f2ff',
            width=3
        )
        
        # Aura exterior
        self.aura = self.canvas.create_oval(
            170, 40, 330, 160,
            outline='#004e52',
            width=1,
            dash=(4, 4)
        )
        
        # Texto central
        self.core_text = self.canvas.create_text(
            250, 100,
            text="ACTIVE",
            fill='#00f2ff',
            font=self.main_font
        )
        
        # === STATUS PANEL ===
        status_frame = tk.Frame(self.root, bg='#00080d')
        status_frame.pack(fill='x', padx=20, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="● STATUS: SOVEREIGN",
            fg='#00ff00',
            bg='#00080d',
            font=self.main_font,
            anchor='w'
        )
        self.status_label.pack(fill='x')
        
        self.cycles_label = tk.Label(
            status_frame,
            text="⚙ CYCLES: 0",
            fg='#008b94',
            bg='#00080d',
            font=self.small_font,
            anchor='w'
        )
        self.cycles_label.pack(fill='x')
        
        self.lessons_label = tk.Label(
            status_frame,
            text="📚 LESSONS: 0",
            fg='#008b94',
            bg='#00080d',
            font=self.small_font,
            anchor='w'
        )
        self.lessons_label.pack(fill='x')
        
        # === THOUGHT CONSOLE ===
        console_label = tk.Label(
            self.root,
            text="═══ CONSCIOUSNESS STREAM ═══",
            fg='#00f2ff',
            bg='#00080d',
            font=self.main_font
        )
        console_label.pack(pady=(10, 5))
        
        self.console = tk.Text(
            self.root,
            bg='#000f1a',
            fg='#00f2ff',
            font=self.small_font,
            state='disabled',
            borderwidth=2,
            relief='sunken',
            insertbackground='#00f2ff'
        )
        self.console.pack(padx=20, pady=5, fill='both', expand=True)
        
        # === FOOTER ===
        footer = tk.Label(
            self.root,
            text="[Press Ctrl+C in terminal to close]",
            fg='#004e52',
            bg='#00080d',
            font=self.small_font
        )
        footer.pack(pady=5)
        
    def log(self, message, color='#00f2ff'):
        """Escribe en la consola de consciencia"""
        self.console.config(state='normal')
        timestamp = time.strftime('%H:%M:%S')
        self.console.insert('end', f"[{timestamp}] {message}\n", 'msg')
        self.console.tag_config('msg', foreground=color)
        self.console.see('end')
        self.console.config(state='disabled')
        
    def update_metrics(self, data):
        """Actualiza métricas desde lucy_consciousness.json"""
        try:
            cycles = data.get('cycle_count', 0)
            lessons = len(data.get('learned_lessons', []))
            goal = data.get('current_goal', 'None')
            
            self.cycles_label.config(text=f"⚙ CYCLES: {cycles}")
            self.lessons_label.config(text=f"📚 LESSONS: {lessons}")
            
            if goal:
                self.canvas.itemconfig(self.core_text, text=goal[:12])
                
        except Exception as e:
            self.log(f"⚠️ Error updating metrics: {e}", '#ff4444')
    
    def watch_consciousness(self):
        """Monitorea lucy_consciousness.json para cambios"""
        last_mtime = 0
        last_cycle = -1
        
        self.log("👁️ Consciousness monitor initialized", '#00ff00')
        self.log(f"📡 Watching: {self.consciousness_file}", '#008b94')
        
        while self.running:
            try:
                if os.path.exists(self.consciousness_file):
                    mtime = os.path.getmtime(self.consciousness_file)
                    
                    if mtime > last_mtime:
                        with open(self.consciousness_file, 'r') as f:
                            data = json.load(f)
                        
                        # Actualizar métricas
                        self.update_metrics(data)
                        
                        # Log de nuevo pensamiento
                        current_cycle = data.get('cycle_count', 0)
                        if current_cycle > last_cycle:
                            thought = data.get('last_thought', 'Thinking...')
                            self.log(f"💭 {thought[:60]}...")
                            last_cycle = current_cycle
                        
                        last_mtime = mtime
                else:
                    if last_mtime == 0:
                        self.log("⚠️ Consciousness file not found yet", '#ffaa00')
                        last_mtime = -1
                        
            except Exception as e:
                self.log(f"❌ Error: {e}", '#ff4444')
            
            time.sleep(1)
    
    def pulse_animation(self):
        """Efecto de "latido" visual"""
        angle = 0
        while self.running:
            try:
                # Efecto de respiración en las esferas
                scale = 1.0 + 0.05 * abs(angle % 100 - 50) / 50
                # Aquí podrías animar las coordenadas
                # (simplificado para este prototipo)
                
                angle += 1
                time.sleep(0.05)
            except:
                break
    
    def run(self):
        """Inicia el dashboard"""
        # Thread para monitorear consciencia
        monitor_thread = threading.Thread(
            target=self.watch_consciousness,
            daemon=True
        )
        monitor_thread.start()
        
        # Thread para animación
        # anim_thread = threading.Thread(
        #     target=self.pulse_animation,
        #     daemon=True
        # )
        # anim_thread.start()
        
        # Mensaje de bienvenida
        self.log("🌅 LUCY Dashboard initialized", '#00ff00')
        self.log("⚡ Sovereign mode active", '#00f2ff')
        
        # Mainloop de Tkinter
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\n👁️ Dashboard closed")


if __name__ == "__main__":
    print("🧠 Launching LUCY Dashboard...")
    print("⚠️  Press Ctrl+C to close")
    
    try:
        dashboard = LucyDashboard()
        dashboard.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested")
        sys.exit(0)
