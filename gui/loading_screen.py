from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QMovie
import os

class LoadingScreen(QDialog):
    def __init__(self, message="Starting Libra...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(400, 300)
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #232526, stop:1 #414345);")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Animated GIF (optional, fallback to text)
        gif_path = os.path.join(os.path.dirname(__file__), "libra_loading.gif")
        if os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            self.anim_label = QLabel()
            self.anim_label.setAlignment(Qt.AlignCenter)
            self.anim_label.setMovie(self.movie)
            self.movie.start()
            layout.addWidget(self.anim_label)
        else:
            self.anim_label = QLabel("🔄")
            self.anim_label.setFont(QFont("Arial", 48))
            self.anim_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.anim_label)

        self.label = QLabel(message)
        self.label.setFont(QFont("Arial", 16, QFont.Bold))
        self.label.setStyleSheet("color: #fff; padding: 20px;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar { background: #333; border-radius: 10px; height: 20px; } QProgressBar::chunk { background: #0078d7; border-radius: 10px; }")
        layout.addWidget(self.progress)

        self.setLayout(layout)

    def set_message(self, msg):
        self.label.setText(msg)

    def set_progress(self, value):
        self.progress.setValue(value)
