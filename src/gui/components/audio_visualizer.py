import customtkinter as ctk
import numpy as np

class AudioVisualizer(ctk.CTkCanvas):
    def __init__(self, master, processor, **kwargs):
        super().__init__(master, 
                         bg=kwargs.get("fg_color", "#050505"), 
                         highlightthickness=0,
                         **kwargs)
        self.processor = processor
        
        # 4 Vertical Pillars - Standard Gemini Palette
        self.pillars = [
            {"color": "#4285F4", "freq_idx": 1},  # Cyan/Blue
            {"color": "#EA4335", "freq_idx": 4},  # Red/Magenta
            {"color": "#FBBC05", "freq_idx": 8},  # Amber
            {"color": "#34A853", "freq_idx": 12}, # Green
        ]
        
        self.heights = [10.0] * 4 # Current heights for smoothing
        self._update_viz()

    def _update_viz(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 20 or h < 20:
            self.after(20, self._update_viz)
            return

        fft = self.processor.get_fft_data()
        
        pillar_w = 12
        spacing = 18
        total_w = (pillar_w * 4) + (spacing * 3)
        start_x = (w - total_w) / 2
        center_y = h / 2

        for i, config in enumerate(self.pillars):
            # Get energy for this specific frequency range
            if len(fft) > config["freq_idx"]:
                energy = fft[config["freq_idx"]]
            else:
                energy = 0
            
            # target height: base + reaction
            target = 15 + (energy * 180) # Baseline 15px
            # Smoothing (Lerp)
            self.heights[i] += (target - self.heights[i]) * 0.2
            
            x_center = start_x + (i * (pillar_w + spacing)) + (pillar_w / 2)
            y_start = center_y - (self.heights[i] / 2)
            y_end = center_y + (self.heights[i] / 2)

            # Draw "Capsule" Pillar (rounded caps)
            # 1. Glow effect (faint border)
            self.create_line(
                x_center, y_start, x_center, y_end,
                width=pillar_w + 4,
                fill=config["color"],
                capstyle="round",
                stipple="gray50" # Transparency simulation in Tkinter
            )
            # 2. Solid Pillar
            self.create_line(
                x_center, y_start, x_center, y_end,
                width=pillar_w,
                fill=config["color"],
                capstyle="round"
            )

        self.after(16, self._update_viz) # ~60 FPS
