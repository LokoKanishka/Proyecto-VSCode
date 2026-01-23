import customtkinter as ctk

ctk.set_appearance_mode("Dark")
CYBER_YELLOW = "#FCEE0A"
CYBER_PURPLE = "#BD00FF"
CORE_BG = "#1A0033"

class CyberCoreWidget(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("300x450+1000+300")
        self.title("Lucy Core")
        self.overrideredirect(True)
        self.configure(fg_color="black")
        self.attributes("-alpha", 0.95)

        self.core_frame = ctk.CTkFrame(self, width=280, height=280, corner_radius=140, fg_color=CORE_BG, border_width=4, border_color=CYBER_YELLOW)
        self.core_frame.pack(expand=True, pady=10)

        self.energy_ring = ctk.CTkFrame(self.core_frame, width=220, height=220, corner_radius=110, fg_color=CORE_BG, border_width=3, border_color=CYBER_PURPLE)
        self.energy_ring.place(relx=0.5, rely=0.5, anchor="center")

        self.core_button = ctk.CTkButton(self.core_frame, text="LUCY", width=150, height=150, corner_radius=75,
                                         fg_color=CYBER_YELLOW, text_color="black", font=("Arial Black", 24))
        self.core_button.place(relx=0.5, rely=0.5, anchor="center")

        self.chat_bubble = ctk.CTkFrame(self, fg_color=CYBER_YELLOW, corner_radius=10)
        self.chat_bubble.pack(pady=10)

        self.chat_label = ctk.CTkLabel(self.chat_bubble, text="INICIALIZANDO...", text_color="black", font=("Consolas", 12, "bold"))
        self.chat_label.pack(padx=10, pady=5)

        self.close_btn = ctk.CTkButton(self, text="CERRAR BOCETO", fg_color="#330000", hover_color="#550000", command=self.destroy)
        self.close_btn.pack(pady=10)

        self.pulsing = False
        self.pulse_core()

    def pulse_core(self):
        try:
            if not self.pulsing:
                self.energy_ring.configure(border_color=CYBER_YELLOW)
                self.chat_label.configure(text="SISTEMA ACTIVO")
                self.pulsing = True
            else:
                self.energy_ring.configure(border_color=CYBER_PURPLE)
                self.chat_label.configure(text="ESCUCHANDO...")
                self.pulsing = False
            self.after(1000, self.pulse_core)
        except: pass

if __name__ == "__main__":
    app = CyberCoreWidget()
    app.mainloop()
