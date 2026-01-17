import sys
import os

# Asegurar que Python encuentre los modulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.gui.app import LucyStudioApp

def main():
    app = LucyStudioApp()
    # AQUI ESTABA EL ERROR: Cambiamos app.start() por app.mainloop()
    app.mainloop()

if __name__ == "__main__":
    main()
