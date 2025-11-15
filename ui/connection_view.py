"""
Connection Management UI for Libra
Phase 11 implementation: Manual peer connection, QR code, peer management
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QInputDialog
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
import qrcode
import io

# Placeholder for peer connection logic
from peer.connection_manager import ConnectionManager

class ConnectionView(QWidget):
    def __init__(self, connection_manager):
        super().__init__()
        self.connection_manager = connection_manager
        self.setWindowTitle("Peer Connections")
        self.setGeometry(200, 200, 500, 400)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Manual connection
        self.manual_layout = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Peer IP:PORT")
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.manual_connect)
        self.manual_layout.addWidget(self.ip_input)
        self.manual_layout.addWidget(self.connect_btn)
        self.layout.addLayout(self.manual_layout)

        # Peer list
        self.peer_list = QListWidget()
        self.peer_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.peer_list.customContextMenuRequested.connect(self.open_peer_menu)
        self.layout.addWidget(QLabel("Connected Peers:"))
        self.layout.addWidget(self.peer_list)
        self.refresh_peer_list()

        # QR code generation
        self.qr_btn = QPushButton("Show My QR Code")
        self.qr_btn.clicked.connect(self.show_qr_code)
        self.layout.addWidget(self.qr_btn)
        self.qr_label = QLabel()
        self.layout.addWidget(self.qr_label)

    def manual_connect(self):
        ip_port = self.ip_input.text().strip()
        if not ip_port:
            QMessageBox.warning(self, "Input Error", "Please enter IP:PORT.")
            return
        success = self.connection_manager.connect_to_peer(ip_port)
        if success:
            QMessageBox.information(self, "Connected", f"Connected to {ip_port}")
            self.refresh_peer_list()
        else:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to {ip_port}")

    def refresh_peer_list(self):
        self.peer_list.clear()
        for peer in self.connection_manager.get_peers():
            item = QListWidgetItem(f"{peer['nickname']} ({peer['ip']})")
            item.setData(Qt.UserRole, peer)
            self.peer_list.addItem(item)

    def open_peer_menu(self, position):
        item = self.peer_list.itemAt(position)
        if not item:
            return
        peer = item.data(Qt.UserRole)
        menu = QMenu()
        block_action = menu.addAction("Block/Unblock Peer")
        nickname_action = menu.addAction("Change Nickname")
        details_action = menu.addAction("View Details")
        remove_action = menu.addAction("Remove Peer")
        action = menu.exec_(self.peer_list.viewport().mapToGlobal(position))
        if action == block_action:
            self.connection_manager.toggle_block_peer(peer['id'])
            self.refresh_peer_list()
        elif action == nickname_action:
            new_nick, ok = QInputDialog.getText(self, "Change Nickname", "Enter new nickname:")
            if ok and new_nick:
                self.connection_manager.set_peer_nickname(peer['id'], new_nick)
                self.refresh_peer_list()
        elif action == details_action:
            QMessageBox.information(self, "Peer Details", f"Public Key: {peer['public_key']}\nFingerprint: {peer['fingerprint']}")
        elif action == remove_action:
            confirm = QMessageBox.question(self, "Remove Peer", f"Remove {peer['nickname']} and delete history?", QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.connection_manager.remove_peer(peer['id'])
                self.refresh_peer_list()

    def show_qr_code(self):
        # Example: encode peer ID, public key, IP
        my_info = self.connection_manager.get_my_info()
        qr_data = f"{my_info['id']}|{my_info['public_key']}|{my_info['ip']}"
        qr_img = qrcode.make(qr_data)
        buf = io.BytesIO()
        qr_img.save(buf, format='PNG')
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        self.qr_label.setPixmap(pixmap)
        self.qr_label.setFixedSize(200, 200)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    cm = ConnectionManager()  # Should be initialized with actual logic
    win = ConnectionView(cm)
    win.show()
    sys.exit(app.exec_())
