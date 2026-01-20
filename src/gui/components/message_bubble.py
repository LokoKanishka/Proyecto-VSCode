import customtkinter as ctk

class MessageBubble(ctk.CTkFrame):
    def __init__(self, master, text, is_user=False, **kwargs):
        super().__init__(master, **kwargs)
        
        # Colores extraídos del Botón (Metal Cepillado + Neón)
        if is_user:
            self.accent_color = "#00ff41" # Verde Neón
            self.bg_inner = "#0a1f0a"     # Verde Profundo
        else:
            self.accent_color = "#d800ff" # Violeta Neón
            self.bg_inner = "#1f0a1f"     # Violeta Profundo

        # Estilo "Hardware Module"
        self.configure(
            fg_color="#121212",      # Gris Metal Oscuro
            corner_radius=2,         # Esquinas casi rectas (industrial)
            border_width=2,
            border_color="#333333"    # Metal cepillado
        )

        # Efecto de Circuito/Glow Interno
        self.inner_frame = ctk.CTkFrame(
            self, 
            fg_color=self.bg_inner,
            corner_radius=0,
            border_width=1,
            border_color=self.accent_color
        )
        self.inner_frame.pack(padx=2, pady=2, fill="both", expand=True)

        self.label = ctk.CTkLabel(
            self.inner_frame, 
            text=text, 
            text_color=self.accent_color,
            font=("Consolas", 14),
            wraplength=450, 
            justify="left"
        )
        self.label.pack(padx=15, pady=10)

    def update_text(self, new_text):
        """Update the bubble text (for streaming)."""
        self.label.configure(text=new_text)
