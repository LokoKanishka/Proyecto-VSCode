import customtkinter as ctk  # <--- ESTA LINEA FALTABA
import sys
import os

# Asegurar que Python encuentre los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.gui.app import LucyStudioApp

def main():
    # Ahora sí funcionará porque 'ctk' está importado
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    app = LucyStudioApp()
    app.mainloop()

if __name__ == "__main__":
    main()
