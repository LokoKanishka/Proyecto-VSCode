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
    
    # Estados emocionales técnicos
    STATES = {
        'COHERENCE': {'color': '#00f2ff', 'symbol': '💠', 'label': 'COHERENCE'},
        'DISSONANCE': {'color': '#ff8800', 'symbol': '🟧', 'label': 'DISSONANCE'},
        'CHAOS': {'color': '#ff0000', 'symbol': '🟥', 'label': 'CHAOS'},
        'ECSTASY': {'color': '#ffffff', 'symbol': '✨', 'label': 'ECSTASY'}
    }

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
        
        # Estado de coherencia
        self.current_state = 'COHERENCE'
        self.entropy_value = 0.0
        self.autonomy_ratio = 0.0
        
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
        
        self.entropy_label = tk.Label(
            status_frame,
            text="🌀 ENTROPY: 0.00",
            fg='#00f2ff',
            bg='#00080d',
            font=self.small_font,
            anchor='w'
        )
        self.entropy_label.pack(fill='x')
        
        self.autonomy_label = tk.Label(
            status_frame,
            text="⚡ AUTONOMY: 0%",
            fg='#00ff00',
            bg='#00080d',
            font=self.small_font,
            anchor='w'
        )
        self.autonomy_label.pack(fill='x')
        
        self.autonomy_indicator = tk.Label(
            status_frame,
            text="🧠 AUTONOMY: 0%",
            fg='#00ff00',
            bg='#00080d',
            font=self.main_font,
            anchor='w'
        )
        self.autonomy_indicator.pack(fill='x')

        
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
        """Actualiza métricas desde lucy_consciousness.json y calcula estado de coherencia"""
        try:
            cycles = data.get('cycle_count', 0)
            lessons = len(data.get('learned_lessons', []))
            goal = data.get('current_goal', 'None')
            
            # Calcular entropía aproximada basada en datos disponibles
            self.entropy_value = data.get('entropy', 0.3)
            
            # Calcular ratio de autonomía (acciones proactivas vs reactivas)
            proactive = data.get('proactive_actions', 0)
            reactive = data.get('reactive_actions', 1)
            self.autonomy_ratio = (proactive / (proactive + reactive)) * 100
            
            # Determinar estado de coherencia
            self.current_state = self._calculate_coherence_state()
            state_info = self.STATES[self.current_state]
            
            # Actualizar labels
            self.cycles_label.config(text=f"⚙ CYCLES: {cycles}")
            self.lessons_label.config(text=f"📚 LESSONS: {lessons}")
            self.entropy_label.config(
                text=f"🌀 ENTROPY: {self.entropy_value:.2f}",
                fg=state_info['color']
            )
            self.autonomy_label.config(
                text=f"⚡ AUTONOMY: {self.autonomy_ratio:.0f}%"
            )
            
            # Actualizar indicador de autonomía operativa
            if self.autonomy_ratio >= 99:
                autonomy_status = "🧠 AUTONOMY: 99% (SOVEREIGN)"
                autonomy_color = '#00ff00'
            elif self.autonomy_ratio >= 70:
                autonomy_status = f"🧠 AUTONOMY: {self.autonomy_ratio:.0f}% (HIGH)"
                autonomy_color = '#00f2ff'
            elif self.autonomy_ratio >= 40:
                autonomy_status = f"🧠 AUTONOMY: {self.autonomy_ratio:.0f}% (MODERATE)"
                autonomy_color = '#ff8800'
            else:
                autonomy_status = f"🧠 AUTONOMY: {self.autonomy_ratio:.0f}% (LOW)"
                autonomy_color = '#ff4444'
            
            self.autonomy_indicator.config(
                text=autonomy_status,
                fg=autonomy_color
            )
            
            # Actualizar estado visual
            self.status_label.config(
                text=f"{state_info['symbol']} STATUS: {state_info['label']}",
                fg=state_info['color']
            )
            
            # Actualizar visualización central
            if goal:
                self.canvas.itemconfig(self.core_text, text=goal[:12], fill=state_info['color'])
            
            # Actualizar colores de esferas según estado
            self.canvas.itemconfig(self.sphere1, outline=state_info['color'])
            self.canvas.itemconfig(self.sphere2, outline=state_info['color'])
                
        except Exception as e:
            self.log(f"⚠️ Error updating metrics: {e}", '#ff4444')
    
    def _calculate_coherence_state(self):
        """Determina el estado emocional técnico basado en métricas"""
        # ECSTASY: Baja entropía + Alta autonomía
        if self.entropy_value < 0.2 and self.autonomy_ratio > 70:
            return 'ECSTASY'
        # COHERENCE: Entropía moderada, sistema estable
        elif self.entropy_value < 0.5 and self.autonomy_ratio > 40:
            return 'COHERENCE'
        # DISSONANCE: Entropía elevada o baja autonomía
        elif self.entropy_value < 0.7 or self.autonomy_ratio < 40:
            return 'DISSONANCE'
        # CHAOS: Entropía crítica
        else:
            return 'CHAOS'
    
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
