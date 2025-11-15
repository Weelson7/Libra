def show_file_progress(self, sent, total):
        if not hasattr(self, 'file_progress_bar'):
            from PyQt5.QtWidgets import QProgressBar
            self.file_progress_bar = QProgressBar()
            self.centralWidget().layout().addWidget(self.file_progress_bar)
        self.file_progress_bar.setMaximum(total)
        self.file_progress_bar.setValue(sent)
        if sent >= total:
            self.file_progress_bar.setValue(total)
            self.file_progress_bar.setFormat("File transfer complete")
import sys
import os
from ui.connection_view import ConnectionView
from peer.connection_manager import ConnectionManager
from config import DB_PATH
import threading
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton, QLabel, QMenuBar, QAction, QFrame,
    QSystemTrayIcon, QStyle, QMenu, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QFont, QIcon
from db.device_manager import DeviceManager

class PeerItemWidget(QWidget):
    def __init__(self, nickname, status, last_seen, unread_count=0):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        self.name_label = QLabel(nickname)
        self.status_label = QLabel(status)
        self.status_label.setFont(QFont("Arial", 8))
        self.status_label.setStyleSheet(f"color: {'green' if status == 'Online' else 'gray'};")
        self.last_seen_label = QLabel(last_seen)
        self.last_seen_label.setFont(QFont("Arial", 8))
        self.last_seen_label.setStyleSheet("color: #888;")
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.last_seen_label)
        if unread_count > 0:
            self.unread_label = QLabel(f"{unread_count}")
            self.unread_label.setStyleSheet("background: red; color: white; border-radius: 8px; padding: 2px 6px;")
            layout.addWidget(self.unread_label)
        self.setLayout(layout)


class BackendThread(QThread):
    message_received = pyqtSignal(str, str, QDateTime)
    peer_status_changed = pyqtSignal(str, str)
    sync_completed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        # Simulate backend events
        while self.running:
            time.sleep(5)
            # Simulate message received for Peer 1
            self.message_received.emit("Peer 1", "This is a new message!", QDateTime.currentDateTime())
            time.sleep(3)
            # Simulate Peer 2 coming online
            self.peer_status_changed.emit("Peer 2", "Online")
            time.sleep(2)
            # Simulate sync completed
            self.sync_completed.emit("Peer 1")

    def stop(self):
        self.running = False

class DeviceManagementDialog(QDialog):
    def __init__(self, device_manager, user_id, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.user_id = user_id
        self.setWindowTitle("Device Management")
        self.layout = QVBoxLayout()
        self.device_list = QListWidget()
        self.refresh_devices()
        self.layout.addWidget(QLabel("Linked Devices:"))
        self.layout.addWidget(self.device_list)
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText("New device name")
        self.layout.addWidget(self.rename_input)
        self.rename_btn = QPushButton("Rename Device")
        self.rename_btn.clicked.connect(self.rename_device)
        self.layout.addWidget(self.rename_btn)
        self.revoke_btn = QPushButton("Revoke Device")
        self.revoke_btn.clicked.connect(self.revoke_device)
        self.layout.addWidget(self.revoke_btn)
        self.setLayout(self.layout)

    def refresh_devices(self):
        self.device_list.clear()
        devices = self.device_manager.get_devices(self.user_id)
        for d in devices:
            self.device_list.addItem(f"{d['device_id']} | {d['name']} | Trust: {d['trust_level']} | Last Active: {d['last_active']}")

    def rename_device(self):
        selected = self.device_list.currentItem()
        new_name = self.rename_input.text().strip()
        if selected and new_name:
            device_id = selected.text().split(' | ')[0]
            self.device_manager.rename_device(device_id, new_name)
            self.refresh_devices()
            QMessageBox.information(self, "Success", "Device renamed.")
        else:
            QMessageBox.warning(self, "Error", "Select a device and enter a new name.")

    def revoke_device(self):
        selected = self.device_list.currentItem()
        if selected:
            device_id = selected.text().split(' | ')[0]
            self.device_manager.revoke_device(device_id)
            self.refresh_devices()
            QMessageBox.information(self, "Success", "Device revoked.")
        else:
            QMessageBox.warning(self, "Error", "Select a device to revoke.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize peer_threads and peer_status first
        self.peer_threads = {
            "Peer 1": [
                {"sender": "me", "text": "Hello Peer 1!", "timestamp": QDateTime.currentDateTime().addSecs(-3600)},
                {"sender": "Peer 1", "text": "Hi!", "timestamp": QDateTime.currentDateTime().addSecs(-3590)}
            ],
            "Peer 2": [
                {"sender": "me", "text": "Are you there?", "timestamp": QDateTime.currentDateTime().addSecs(-7200)}
            ],
            "Peer 3": []
        }
        self.peer_status = {
            "Peer 1": "Online",
            "Peer 2": "Offline",
            "Peer 3": "Offline"
        }
        self.current_peer = None
        self.setWindowTitle("Libra Messenger")
        self.resize(900, 600)
        self.init_ui()
        self.init_tray()


    def init_ui(self):
        # Central Widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        # Menu Bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        settings_menu = menu_bar.addMenu("Settings")
        help_menu = menu_bar.addMenu("Help")
        file_menu.addAction(QAction("Exit", self))
        settings_menu.addAction(QAction("Preferences", self))
        help_menu.addAction(QAction("About", self))

        # Add Connection Management action
        conn_action = QAction("Manage Connections", self)
        conn_action.triggered.connect(self.open_connection_dialog)
        settings_menu.addAction(conn_action)

        # Add Alias Registry Management action
        alias_action = QAction("Manage Aliases", self)
        alias_action.triggered.connect(self.open_alias_registry_dialog)
        settings_menu.addAction(alias_action)
    def open_alias_registry_dialog(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox
        from utils.alias_registry import AliasRegistry
        class AliasRegistryDialog(QDialog):
            def __init__(self, registry, parent=None):
                super().__init__(parent)
                self.registry = registry
                self.setWindowTitle("Alias Registry Management")
                self.layout = QVBoxLayout()
                self.alias_list = QListWidget()
                self.refresh_aliases()
                self.layout.addWidget(QLabel("Current Aliases:"))
                self.layout.addWidget(self.alias_list)

                # Publish alias
                pub_layout = QHBoxLayout()
                self.onion_input = QLineEdit()
                self.onion_input.setPlaceholderText("Onion address")
                self.pubkey_input = QLineEdit()
                self.pubkey_input.setPlaceholderText("Public key (PEM or fingerprint)")
                self.alias_input = QLineEdit()
                self.alias_input.setPlaceholderText("Custom alias (optional)")
                self.private_check = QPushButton("Private")
                self.private_check.setCheckable(True)
                pub_btn = QPushButton("Publish Alias")
                pub_btn.clicked.connect(self.publish_alias)
                pub_layout.addWidget(self.onion_input)
                pub_layout.addWidget(self.pubkey_input)
                pub_layout.addWidget(self.alias_input)
                pub_layout.addWidget(self.private_check)
                pub_layout.addWidget(pub_btn)
                self.layout.addLayout(pub_layout)

                # Lookup/remove/purge
                lookup_layout = QHBoxLayout()
                self.lookup_input = QLineEdit()
                self.lookup_input.setPlaceholderText("Alias to lookup/remove")
                lookup_btn = QPushButton("Lookup")
                lookup_btn.clicked.connect(self.lookup_alias)
                remove_btn = QPushButton("Remove")
                remove_btn.clicked.connect(self.remove_alias)
                purge_btn = QPushButton("Purge Stale")
                purge_btn.clicked.connect(self.purge_stale)
                self.threshold_input = QLineEdit()
                self.threshold_input.setPlaceholderText("Threshold min (default 60)")
                lookup_layout.addWidget(self.lookup_input)
                lookup_layout.addWidget(lookup_btn)
                lookup_layout.addWidget(remove_btn)
                lookup_layout.addWidget(self.threshold_input)
                lookup_layout.addWidget(purge_btn)
                self.layout.addLayout(lookup_layout)

                self.setLayout(self.layout)

            def refresh_aliases(self):
                self.alias_list.clear()
                for reg in [self.registry._public_registry, self.registry._private_registry]:
                    for alias, record in reg.items():
                        self.alias_list.addItem(f"{alias} | Onion: {record.onion} | Last seen: {record.last_seen} | {'Public' if record.is_public else 'Private'}")

            def publish_alias(self):
                onion = self.onion_input.text().strip()
                pubkey = self.pubkey_input.text().strip()
                alias = self.alias_input.text().strip() or None
                is_public = not self.private_check.isChecked()
                try:
                    record = self.registry.publish_alias(onion, pubkey, alias, is_public)
                    QMessageBox.information(self, "Success", f"Published alias: {record.alias}")
                    self.refresh_aliases()
                except Exception as e:
                    QMessageBox.warning(self, "Error", str(e))

            def lookup_alias(self):
                alias = self.lookup_input.text().strip()
                record = self.registry.lookup_alias(alias, include_private=True)
                if record:
                    QMessageBox.information(self, "Alias Found", f"Alias: {record.alias}\nOnion: {record.onion}\nPublic key: {record.public_key}\nLast seen: {record.last_seen}\nType: {'Public' if record.is_public else 'Private'}")
                else:
                    QMessageBox.warning(self, "Not Found", "Alias not found.")

            def remove_alias(self):
                alias = self.lookup_input.text().strip()
                removed = self.registry.remove_alias(alias, include_private=True)
                if removed:
                    QMessageBox.information(self, "Removed", f"Removed alias: {alias}")
                    self.refresh_aliases()
                else:
                    QMessageBox.warning(self, "Not Found", "Alias not found.")

            def purge_stale(self):
                try:
                    threshold = int(self.threshold_input.text().strip() or "60")
                except Exception:
                    threshold = 60
                self.registry.purge_stale(threshold_minutes=threshold)
                QMessageBox.information(self, "Purged", f"Purged stale aliases older than {threshold} minutes.")
                self.refresh_aliases()

        # Use singleton registry for demo
        if not hasattr(self, "_alias_registry"):
            from utils.alias_registry import AliasRegistry
            self._alias_registry = AliasRegistry()
        dialog = AliasRegistryDialog(self._alias_registry, self)
        dialog.exec_()

        # Peer List Sidebar
        self.peer_list = QListWidget()
        self.peer_list.setFixedWidth(220)
        self.populate_peer_list()
        main_layout.addWidget(self.peer_list)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)


    def open_connection_dialog(self):
        if not hasattr(self, 'connection_manager'):
            self.connection_manager = ConnectionManager()
        self.conn_view = ConnectionView(self.connection_manager)
        self.conn_view.show()

    def init_ui(self):
        # Central Widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        # Menu Bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        settings_menu = menu_bar.addMenu("Settings")
        help_menu = menu_bar.addMenu("Help")
        file_menu.addAction(QAction("Exit", self))
        settings_menu.addAction(QAction("Preferences", self))
        help_menu.addAction(QAction("About", self))

        # Add Connection Management action
        conn_action = QAction("Manage Connections", self)
        conn_action.triggered.connect(self.open_connection_dialog)
        settings_menu.addAction(conn_action)

        # Peer List Sidebar
        self.peer_list = QListWidget()
        self.peer_list.setFixedWidth(220)
        self.populate_peer_list()
        main_layout.addWidget(self.peer_list)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Message Thread View
        thread_layout = QVBoxLayout()
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        self.message_display.setPlaceholderText("Select a peer to view messages.")
        thread_layout.addWidget(self.message_display)

        # Message Input Field
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.send_button = QPushButton("Send")
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        # File attachment button
        self.attach_button = QPushButton("Attach File")
        input_layout.addWidget(self.attach_button)
        thread_layout.addLayout(input_layout)

        # Drag and drop support for file attachments
        self.message_display.setAcceptDrops(True)
        self.message_display.installEventFilter(self)
        self.attach_button.clicked.connect(self.attach_file)

        main_layout.addLayout(thread_layout)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    def attach_file(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from utils.file_transfer import save_file_to_storage, split_file
        from db.db_handler import DBHandler
        from peer.connection_manager import ConnectionManager
        import time
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Attach", "", "All Files (*);;Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        if file_path:
            # Save file to storage and get hash
            storage_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'files')
            storage_dir = os.path.abspath(storage_dir)
            dst_path, file_hash = save_file_to_storage(file_path, storage_dir)
            file_size = os.path.getsize(dst_path)
            db = DBHandler()
            db.init_db()
            timestamp = int(time.time())
            db.insert_file_metadata(
                file_name=os.path.basename(dst_path),
                file_path=dst_path,
                file_hash=file_hash,
                file_size=file_size,
                message_id=None,
                peer_id=None,
                timestamp=timestamp
            )
            # Send file chunks to first peer (demo)
            conn_mgr = ConnectionManager()
            peers = conn_mgr.get_peers()
            if peers:
                peer = peers[0]
                ip_port = peer.get('ip')
                sock = conn_mgr.connect_to_peer(ip_port)
                conn_mgr.send_file_chunks(sock, dst_path, progress_callback=self.show_file_progress)
                sock.close()
                QMessageBox.information(self, "File Transfer", f"File sent to {ip_port}")
            else:
                QMessageBox.information(self, "File Transfer", "No peers available for file transfer.")

    def eventFilter(self, source, event):
        from PyQt5.QtCore import QEvent
        from PyQt5.QtWidgets import QMessageBox
        from utils.file_transfer import save_file_to_storage, split_file
        from db.db_handler import DBHandler
        import time
        if source == self.message_display and event.type() == QEvent.DragEnter:
            if event.mimeData().hasUrls():
                event.accept()
            else:
                event.ignore()
            return True
        if source == self.message_display and event.type() == QEvent.Drop:
            if event.mimeData().hasUrls():
                file_path = event.mimeData().urls()[0].toLocalFile()
                storage_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'files')
                storage_dir = os.path.abspath(storage_dir)
                dst_path, file_hash = save_file_to_storage(file_path, storage_dir)
                file_size = os.path.getsize(dst_path)
                db = DBHandler()
                db.init_db()
                timestamp = int(time.time())
                db.insert_file_metadata(
                    file_name=os.path.basename(dst_path),
                    file_path=dst_path,
                    file_hash=file_hash,
                    file_size=file_size,
                    message_id=None,
                    peer_id=None,
                    timestamp=timestamp
                )
                chunk_count = sum(1 for _ in split_file(dst_path))
                QMessageBox.information(self, "File Dropped", f"Saved to: {dst_path}\nSHA-256: {file_hash}\nSize: {file_size} bytes\nChunks: {chunk_count}")
            return True
        return super().eventFilter(source, event)

        main_layout.addLayout(thread_layout)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Connect signals
        self.send_button.clicked.connect(self.send_message)
        self.peer_list.itemClicked.connect(self.load_peer_thread)

        # Start backend thread after UI is ready
        self.init_backend()
    def init_tray(self):
        # System tray icon for notifications
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Quit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_notification(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)
    def init_backend(self):
        # Start backend thread and connect signals
        self.backend_thread = BackendThread()
        self.backend_thread.message_received.connect(self.on_message_received)
        self.backend_thread.peer_status_changed.connect(self.on_peer_status_changed)
        self.backend_thread.sync_completed.connect(self.on_sync_completed)
        self.backend_thread.start()

    def closeEvent(self, event):
        # Stop backend thread on close
        if hasattr(self, 'backend_thread'):
            self.backend_thread.stop()
            self.backend_thread.wait()
        event.accept()
    def on_message_received(self, peer_name, message, timestamp):
        # Add message to thread and update UI if peer is selected
        if peer_name not in self.peer_threads:
            self.peer_threads[peer_name] = []
        self.peer_threads[peer_name].append({"sender": peer_name, "text": message, "timestamp": timestamp})
        if self.current_peer == peer_name:
            self.display_thread(peer_name)
        self.show_notification(f"New message from {peer_name}", message)
    def on_peer_status_changed(self, peer_name, status):
        # Update peer status and refresh peer list
        self.peer_status[peer_name] = status
        self.peer_list.clear()
        self.populate_peer_list()
        if self.current_peer == peer_name:
            self.display_thread(peer_name)
    def on_sync_completed(self, peer_name):
        self.show_notification("Sync Completed", f"Messages with {peer_name} are up to date.")

    def populate_peer_list(self):
        # Use self.peer_status for live status
        peers = [
            {"nickname": "Peer 1", "status": self.peer_status.get("Peer 1", "Offline"), "last_seen": "now", "unread": self.count_unread("Peer 1")},
            {"nickname": "Peer 2", "status": self.peer_status.get("Peer 2", "Offline"), "last_seen": "10m ago", "unread": self.count_unread("Peer 2")},
            {"nickname": "Peer 3", "status": self.peer_status.get("Peer 3", "Offline"), "last_seen": "1h ago", "unread": self.count_unread("Peer 3")}
        ]
        for peer in peers:
            item = QListWidgetItem()
            widget = PeerItemWidget(peer["nickname"], peer["status"], peer["last_seen"], peer["unread"])
            item.setSizeHint(widget.sizeHint())
            self.peer_list.addItem(item)
            self.peer_list.setItemWidget(item, widget)

    def count_unread(self, peer_name):
        # Count pending messages (not delivered)
        thread = self.peer_threads.get(peer_name, [])
        return sum(1 for msg in thread if msg.get("delivery_status", "pending") == "pending")

    def send_message(self):
        import hashlib
        message = self.message_input.text()
        if message and self.current_peer:
            timestamp = QDateTime.currentDateTime()
            # Generate a unique message_id
            raw = f"{self.current_peer}:{message}:{timestamp.toSecsSinceEpoch()}"
            message_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
            # Mark as pending when sending
            self.peer_threads[self.current_peer].append({
                "sender": "me",
                "text": message,
                "timestamp": timestamp,
                "delivery_status": "pending",
                "message_id": message_id
            })
            self.display_thread(self.current_peer)
            self.message_input.clear()
            self.message_display.verticalScrollBar().setValue(
                self.message_display.verticalScrollBar().maximum()
            )

    def load_peer_thread(self, item):
        # Get peer name from widget
        widget = self.peer_list.itemWidget(item)
        peer_name = widget.name_label.text()
        self.current_peer = peer_name
        self.display_thread(peer_name)

    def display_thread(self, peer_name):
        self.message_display.clear()
        self.message_display.append(f"<b>--- Messages with {peer_name} ---</b>")
        thread = self.peer_threads.get(peer_name, [])
        for msg in thread:
            sender = "You" if msg["sender"] == "me" else msg["sender"]
            color = "#0078d7" if msg["sender"] == "me" else "#222"
            align = "right" if msg["sender"] == "me" else "left"
            ts = msg["timestamp"].toString("hh:mm:ss")
            # Show delivery status
            status = msg.get("delivery_status", "pending")
            if status == "pending":
                status_icon = "🕒"
            elif status == "sent":
                status_icon = "📤"
            elif status == "delivered":
                status_icon = "✅"
            else:
                status_icon = ""
            self.message_display.append(
                f'<div style="text-align:{align}; color:{color}; margin:4px 0;">'
                f'<span style="font-weight:bold;">{sender}</span>: '
                f'{msg["text"]} '
                f'<span style="font-size:10px; color:#888;">[{ts}]</span> '
                f'<span style="font-size:12px;">{status_icon}</span>'
                f'</div>'
            )
        self.message_display.verticalScrollBar().setValue(
            self.message_display.verticalScrollBar().maximum()
        )

    def update_message_status(self, peer_name, message_id, new_status):
        """Update delivery status for a message and refresh UI. Show notification if delivered."""
        thread = self.peer_threads.get(peer_name, [])
        for msg in thread:
            if msg.get("sender") == "me" and msg.get("message_id", None) == message_id:
                if msg.get("delivery_status") != new_status:
                    msg["delivery_status"] = new_status
                    if new_status == "delivered":
                        self.show_notification("Message Delivered", f"Your message to {peer_name} was delivered.")
        if self.current_peer == peer_name:
            self.display_thread(peer_name)

    def show_device_management(self):
        # Example: show a dialog with device list and management actions
        user_id = self.get_current_user_id()
        device_manager = DeviceManager(DB_PATH)
        dialog = DeviceManagementDialog(device_manager, user_id, self)
        dialog.exec_()
        # Here, you would build a dialog to list devices, allow renaming, revoking, etc.
        # For now, just print devices to console
        devices = self.device_manager.get_devices(user_id)
        for d in devices:
            print(f"Device ID: {d['device_id']}, Name: {d['name']}, Trust Level: {d['trust_level']}, Last Active: {d['last_active']}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
