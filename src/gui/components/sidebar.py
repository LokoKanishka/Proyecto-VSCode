import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        # Ticket 11: Unified with force_ui.py geometry
        super().__init__(master, width=300, corner_radius=0, **kwargs)
        self.pack_propagate(False) # Force 300px width

        # Titulo (Cyberpunk Style)
        self.logo_label = ctk.CTkLabel(
            self, 
            text="LUCY Studio", 
            font=ctk.CTkFont(family="Courier New", size=24, weight="bold"),
            text_color="#00ff41" # Matrix Green
        )
        self.logo_label.pack(pady=(30, 20), padx=20, anchor="w")

        # Navigation Buttons
        self.btn_new = self._create_cyber_button("New Chat", command=self._on_new_chat)
        self.btn_search = self._create_cyber_button("Search History")
        self.btn_models = self._create_cyber_button("My Models")

        # Spacer
        self.spacer = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self.spacer.pack(expand=True, fill="both")

        # Settings abajo
        self.btn_settings = self._create_cyber_button("Settings", side="bottom")

    def _create_cyber_button(self, text, command=None, side="top"):
        btn = ctk.CTkButton(
            self, 
            text=f"> {text}", 
            height=50, 
            anchor="w", 
            fg_color="transparent", 
            border_width=1, 
            border_color="#1f1f1f",
            text_color="#00ff41",
            hover_color="#1a1a1a",
            font=("Courier New", 13, "bold"),
            command=command
        )
        if side == "bottom":
            btn.pack(side="bottom", fill="x", padx=20, pady=30)
        else:
            btn.pack(side="top", fill="x", padx=20, pady=10)
        return btn

    def _on_new_chat(self):
        """Triggers context reset in ChatArea."""
        if hasattr(self.master, "chat_area"):
            self.master.chat_area.reset_context()
        elif hasattr(self.master.master, "chat_area"): # If nested in a container
            self.master.master.chat_area.reset_context()
