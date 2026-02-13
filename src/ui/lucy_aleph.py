import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextBrowser, QFrame, QSlider)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPalette, QFont, QPainter, QRadialGradient

class StateOrb(QWidget):
    """El Orbe de Consciencia: Pulsa según la actividad del enjambre."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self._glow = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(50)
        self.activity_level = 0.5 # 0.0 (Dormida) a 1.0 (Pensamiento intenso)

    def update_pulse(self):
        # El pulso varía sutilmente como una respiración
        import math
        import time
        self._glow = 0.7 + 0.3 * math.sin(time.time() * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color según estado: Violeta (Pensando), Ámbar (Alerta), Marfil (Standby)
        base_color = QColor(123, 44, 191) # Violeta Profundo
        
        gradient = QRadialGradient(50, 50, 45)
        gradient.setColorAt(0, base_color)
        gradient.setColorAt(1, QColor(0, 0, 0, 0)) # Transparencia exterior
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setOpacity(self._glow)
        painter.drawEllipse(5, 5, 90, 90)

class LucyAleph(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LUCY - La Biblioteca de los Tensores")
        self.resize(1200, 800)
        self.init_ui()
        self.apply_obsidian_theme()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Galería de Espejos (Sidebar)
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        title = QLabel("MEMORIA")
        title.setFont(QFont("Cinzel", 14, QFont.Weight.Bold))
        sidebar_layout.addWidget(title)
        
        # Dial de Entropía (Sustituye al slider de Temperatura)
        entropy_label = QLabel("NIVEL DE ENTROPÍA")
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(entropy_label)
        self.entropy_dial = QSlider(Qt.Orientation.Horizontal)
        self.entropy_dial.setRange(0, 100)
        self.entropy_dial.setValue(70)
        sidebar_layout.addWidget(self.entropy_dial)

        # 2. El Río de la Palabra (Chat Area)
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        
        # El Orbe preside la conversación
        self.orb = StateOrb()
        chat_layout.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignCenter)

        # Renderizador de Markdown Real
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setAcceptRichText(True)
        self.chat_display.setPlaceholderText("Aguarda... el laberinto se está despejando.")
        chat_layout.addWidget(self.chat_display)

        # Entrada de Texto
        self.input_field = QFrame()
        self.input_field.setFixedHeight(60)
        # (Aquí iría el QLineEdit estilizado)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.chat_container)

    def apply_obsidian_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0A0A0A; /* Negro Obsidiana */
                color: #F8F9FA; /* Marfil Suave */
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            #Sidebar {
                background-color: #050505;
                border-right: 1px solid #1A1A1A;
            }
            QTextBrowser {
                background-color: transparent;
                border: none;
                font-size: 15px;
                line-height: 1.6;
            }
            /* Estilo para bloques de código (Markdown simulado) */
            pre, code {
                background-color: #1A1A1A;
                color: #FFB703; /* Ámbar Viejo para código */
                border-radius: 4px;
                padding: 10px;
            }
            QSlider::handle:horizontal {
                background: #7B2CBF; /* Violeta */
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)

    def append_text_streaming(self, text):
        """Simula el efecto de máquina de escribir."""
        # Lógica de streaming...
        self.chat_display.insertHtml(f"<b>Lucy:</b> {text}<br>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LucyAleph()
    window.show()
    sys.exit(app.exec())
