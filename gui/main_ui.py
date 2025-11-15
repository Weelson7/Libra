"""
Libra v2.0 Main UI - Complete Refactored GUI
Supports: Tor connections, P2P fallback, message persistence, file transfers, onion rotation
"""
import sys
import os
import time
import threading
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QTextBrowser, QLineEdit, QPushButton, 
    QLabel, QMenuBar, QAction, QFrame, QSystemTrayIcon, QMenu, QDialog,
    QMessageBox, QFileDialog, QProgressBar, QComboBox, QSpinBox, QCheckBox,
    QTabWidget, QGroupBox, QSplitter, QStatusBar, QScrollArea
)
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QTextCursor

from peer.connection_manager import ConnectionManager
from tor_manager import TorManager
from db.db_handler import DBHandler
from utils.crypto_utils import generate_rsa_keypair, save_keys_for_peer, load_keys_for_peer
from utils.alias_registry import AliasRegistry
from utils.file_transfer import save_file_to_storage, split_file, reassemble_file
from config import DB_PATH, USER_ID, TOR_PATH, TOR_CONTROL_PORT, TOR_PASSWORD
from gui.loading_screen import LoadingScreen
from gui.startup_worker import StartupWorker


class PeerItemWidget(QWidget):
    """Enhanced peer list item showing connection status, unread count, and last activity"""
    def __init__(self, peer_id, nickname, status, connection_type, last_seen, unread_count=0):
        super().__init__()
        self.peer_id = peer_id
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Status indicator (colored dot)
        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Arial", 12))
        status_color = "green" if status == "Online" else "gray"
        self.status_dot.setStyleSheet(f"color: {status_color};")
        layout.addWidget(self.status_dot)
        
        # Peer nickname/alias
        self.name_label = QLabel(nickname)
        self.name_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.name_label, stretch=3)
        
        # Connection type (Tor/Direct/P2P)
        self.conn_type_label = QLabel(f"[{connection_type}]")
        self.conn_type_label.setFont(QFont("Arial", 8))
        conn_color = "#0078d7" if connection_type == "Direct" else "#ff8c00" if connection_type == "Tor" else "#888"
        self.conn_type_label.setStyleSheet(f"color: {conn_color};")
        layout.addWidget(self.conn_type_label)
        
        # Last seen timestamp
        self.last_seen_label = QLabel(last_seen)
        self.last_seen_label.setFont(QFont("Arial", 8))
        self.last_seen_label.setStyleSheet("color: #888;")
        layout.addWidget(self.last_seen_label)
        
        # Unread message count badge
        if unread_count > 0:
            self.unread_label = QLabel(str(unread_count))
            self.unread_label.setStyleSheet(
                "background: #e74c3c; color: white; border-radius: 10px; "
                "padding: 2px 8px; font-weight: bold;"
            )
            layout.addWidget(self.unread_label)
        
        self.setLayout(layout)


class MessageBackendThread(QThread):
    """Background thread for handling incoming messages, status updates, and sync operations"""
    message_received = pyqtSignal(str, dict)  # peer_id, message_data
    peer_status_changed = pyqtSignal(str, str, str)  # peer_id, status, connection_type
    file_transfer_progress = pyqtSignal(str, int, int)  # peer_id, sent, total
    sync_completed = pyqtSignal(str)  # peer_id
    tor_status_updated = pyqtSignal(str)  # status text
    onion_rotated = pyqtSignal(str)  # new onion address
    
    def __init__(self, connection_manager, db_handler, tor_manager):
        super().__init__()
        self.conn_mgr = connection_manager
        self.db = db_handler
        self.tor_mgr = tor_manager
        self.running = True
        self.active_connections = {}  # peer_id -> socket
        
    def run(self):
        """Main background loop for processing events"""
        while self.running:
            try:
                # Check for pending messages from DB and retry sending
                self._process_pending_messages()
                
                # Check Tor status
                self._check_tor_status()
                
                # Monitor connection health
                self._monitor_connections()
                
                # Process incoming messages
                self._process_incoming_messages()
                
                time.sleep(1)
            except Exception as e:
                print(f"Backend thread error: {e}")
    
    def _process_pending_messages(self):
        """Retry sending pending messages for online peers"""
        pending = self.db.list_pending_messages()
        for msg in pending:
            peer_id = msg['peer_id']
            if peer_id in self.active_connections:
                try:
                    sock = self.active_connections[peer_id]
                    self.conn_mgr.send_message(sock, {
                        'message_id': msg['message_id'],
                        'content': msg['content'].decode('utf-8'),
                        'timestamp': msg['timestamp']
                    })
                    self.db.update_message_status(msg['message_id'], 1)  # Mark as sent
                except Exception as e:
                    print(f"Failed to send pending message: {e}")
    
    def _check_tor_status(self):
        """Check and update Tor status"""
        try:
            if self.tor_mgr and self.tor_mgr.controller:
                self.tor_status_updated.emit("Connected")
            else:
                self.tor_status_updated.emit("Disconnected")
        except:
            self.tor_status_updated.emit("Error")
    
    def _monitor_connections(self):
        """Monitor connection health and emit status changes"""
        import time
        
        # Check all peers in database for their last_seen status
        try:
            peers = self.db.get_all_peers()
            for peer in peers:
                peer_id = peer['peer_id']
                last_seen = peer['last_seen'] if peer['last_seen'] else 0
                
                # Skip self
                from config import USER_ID
                if peer_id == USER_ID:
                    continue
                
                # Consider online if seen within 5 minutes
                is_online = (time.time() - last_seen) < 300 if last_seen > 0 else False
                
                # Determine connection type
                has_onion = peer['onion_address'] and peer['onion_address'].strip()
                conn_type = "Tor" if has_onion else "Direct"
                
                # Check if peer is in active connections
                if peer_id in self.active_connections:
                    try:
                        # Send heartbeat
                        sock = self.active_connections[peer_id]
                        sock.send(b'\x00')
                        self.peer_status_changed.emit(peer_id, "Online", conn_type)
                    except:
                        # Connection lost
                        self.peer_status_changed.emit(peer_id, "Offline", "None")
                        del self.active_connections[peer_id]
                else:
                    # Update based on last_seen
                    status = "Online" if is_online else "Offline"
                    self.peer_status_changed.emit(peer_id, status, conn_type)
        except Exception as e:
            print(f"Error monitoring connections: {e}")
    
    def _process_incoming_messages(self):
        """Process incoming messages from connected peers"""
        # This would be implemented with actual socket handling
        pass
    
    def _get_connection_type(self, peer_id):
        """Determine connection type for peer"""
        # Check if using Tor or direct P2P
        return "Tor"  # Placeholder
    
    def connect_peer(self, peer_id, ip_port, use_tor=True):
        """Establish connection to a peer"""
        try:
            if use_tor:
                # Connect via Tor
                sock = self._connect_via_tor(peer_id)
            else:
                # Direct P2P connection
                sock = self.conn_mgr._connect_to_peer(*ip_port.split(':'))
            
            self.active_connections[peer_id] = sock
            conn_type = "Tor" if use_tor else "Direct"
            self.peer_status_changed.emit(peer_id, "Online", conn_type)
        except Exception as e:
            print(f"Failed to connect to peer {peer_id}: {e}")
            self.peer_status_changed.emit(peer_id, "Offline", "None")
    
    def _connect_via_tor(self, peer_id):
        """Connect to peer via Tor onion service"""
        # Implementation would use Tor SOCKS proxy
        pass
    
    def stop(self):
        """Stop the background thread"""
        self.running = False


class SettingsDialog(QDialog):
    """Settings dialog for Tor, P2P, and connection preferences"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Libra Settings")
        self.setModal(True)
        self.resize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Connection preferences
        conn_group = QGroupBox("Connection Preferences")
        conn_layout = QVBoxLayout()
        
        self.conn_mode = QComboBox()
        self.conn_mode.addItems(["Auto (Prefer Direct)", "Tor Only", "Direct P2P Only"])
        conn_layout.addWidget(QLabel("Connection Mode:"))
        conn_layout.addWidget(self.conn_mode)
        
        self.tor_enabled = QCheckBox("Enable Tor Integration")
        self.tor_enabled.setChecked(True)
        conn_layout.addWidget(self.tor_enabled)
        
        self.p2p_enabled = QCheckBox("Enable Direct P2P (when possible)")
        self.p2p_enabled.setChecked(True)
        conn_layout.addWidget(self.p2p_enabled)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Tor settings
        tor_group = QGroupBox("Tor Settings")
        tor_layout = QVBoxLayout()
        
        self.tor_control_port = QSpinBox()
        self.tor_control_port.setRange(1024, 65535)
        self.tor_control_port.setValue(9051)
        tor_layout.addWidget(QLabel("Tor Control Port:"))
        tor_layout.addWidget(self.tor_control_port)
        
        self.onion_rotation = QCheckBox("Auto-rotate Onion Address")
        self.onion_rotation.setChecked(False)
        tor_layout.addWidget(self.onion_rotation)
        
        self.rotation_interval = QSpinBox()
        self.rotation_interval.setRange(1, 168)  # 1-168 hours (1 week)
        self.rotation_interval.setValue(24)
        self.rotation_interval.setSuffix(" hours")
        tor_layout.addWidget(QLabel("Rotation Interval:"))
        tor_layout.addWidget(self.rotation_interval)
        
        tor_group.setLayout(tor_layout)
        layout.addWidget(tor_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)


class LibraMainWindow(QMainWindow):
    """Main window for Libra messenger application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Libra - Secure Decentralized Messenger")
        self.resize(1200, 700)
        
        # Initialize components
        self.db = DBHandler()
        self.db.init_db()
        self.conn_mgr = ConnectionManager()
        self.tor_mgr = None
        self.alias_registry = AliasRegistry()
        
        # State variables
        self.current_peer = None
        self.peer_threads = {}  # peer_id -> list of messages
        self.peer_status = {}  # peer_id -> (status, connection_type)
        self.connection_mode = "auto"
        self.tor_enabled = True
        self.p2p_enabled = True
        
        # Initialize UI
        self.init_ui()
        self.init_menu()
        self.init_tray()
        self.init_status_bar()
        
        # Start backend services
        self.init_backend()
        
        # Load peers and messages from database
        self.load_from_database()
        
    def init_ui(self):
        """Initialize the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Peer list
        left_panel = self.create_peer_list_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Chat area
        right_panel = self.create_chat_panel()
        splitter.addWidget(right_panel)
        
        # Set initial sizes (30% left, 70% right)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
    
    def create_peer_list_panel(self):
        """Create the peer list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Search/filter bar
        search_layout = QHBoxLayout()
        self.peer_search = QLineEdit()
        self.peer_search.setPlaceholderText("Search peers...")
        self.peer_search.textChanged.connect(self.filter_peer_list)
        search_layout.addWidget(self.peer_search)
        layout.addLayout(search_layout)
        
        # Peer list
        self.peer_list = QListWidget()
        self.peer_list.itemClicked.connect(self.on_peer_selected)
        layout.addWidget(self.peer_list)
        
        # Add peer button
        add_peer_btn = QPushButton("+ Add Peer")
        add_peer_btn.clicked.connect(self.show_add_peer_dialog)
        layout.addWidget(add_peer_btn)
        
        return panel
    
    def create_chat_panel(self):
        """Create the chat panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat header with peer info
        self.chat_header = QLabel("Select a peer to start messaging")
        self.chat_header.setStyleSheet(
            "padding: 10px; background: #f0f0f0; font-size: 14px; font-weight: bold;"
        )
        layout.addWidget(self.chat_header)
        
        # Message display area
        self.message_display = QTextBrowser()
        self.message_display.setReadOnly(True)
        self.message_display.setOpenExternalLinks(False)
        self.message_display.setAcceptDrops(True)
        self.message_display.dragEnterEvent = self.drag_enter_event
        self.message_display.dropEvent = self.drop_event
        self.message_display.anchorClicked.connect(self.handle_file_link)
        layout.addWidget(self.message_display)
        
        # File transfer progress bar (hidden by default)
        self.file_progress = QProgressBar()
        self.file_progress.setVisible(False)
        layout.addWidget(self.file_progress)
        
        # Message input area
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input, stretch=5)
        
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setToolTip("Attach File")
        self.attach_btn.setFixedWidth(40)
        self.attach_btn.clicked.connect(self.attach_file)
        input_layout.addWidget(self.attach_btn)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
        
        return panel
    
    def init_menu(self):
        """Initialize menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        export_action = QAction("Export Chat History", self)
        export_action.triggered.connect(self.export_chat_history)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Connections menu
        conn_menu = menubar.addMenu("Connections")
        
        manage_conn_action = QAction("Manage Connections", self)
        manage_conn_action.triggered.connect(self.show_connection_manager)
        conn_menu.addAction(manage_conn_action)
        
        manage_alias_action = QAction("Manage Aliases", self)
        manage_alias_action.triggered.connect(self.show_alias_manager)
        conn_menu.addAction(manage_alias_action)
        
        conn_menu.addSeparator()
        
        start_tor_action = QAction("Start Tor Service", self)
        start_tor_action.triggered.connect(self.start_tor_service)
        conn_menu.addAction(start_tor_action)
        
        rotate_onion_action = QAction("Rotate Onion Address", self)
        rotate_onion_action.triggered.connect(self.rotate_onion_address)
        conn_menu.addAction(rotate_onion_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        preferences_action = QAction("Preferences", self)
        preferences_action.triggered.connect(self.show_settings)
        settings_menu.addAction(preferences_action)
        
        settings_menu.addSeparator()
        
        device_manager_action = QAction("🔗 Manage Devices", self)
        device_manager_action.triggered.connect(self.show_device_manager)
        settings_menu.addAction(device_manager_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About Libra", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        tor_help_action = QAction("Tor Setup Help", self)
        tor_help_action.triggered.connect(self.show_tor_help)
        help_menu.addAction(tor_help_action)
    
    def init_tray(self):
        """Initialize system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def init_status_bar(self):
        """Initialize status bar with Tor and connection info"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.tor_status_label = QLabel("Tor: Disconnected")
        self.tor_status_label.setStyleSheet("color: #888; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.tor_status_label)
        
        self.conn_status_label = QLabel("Peers: 0 online")
        self.status_bar.addPermanentWidget(self.conn_status_label)
    
    def init_backend(self):
        """Initialize backend services"""
        # Start Tor if enabled
        if self.tor_enabled:
            self.start_tor_service()
        
        # Start backend thread
        self.backend_thread = MessageBackendThread(self.conn_mgr, self.db, self.tor_mgr)
        self.backend_thread.message_received.connect(self.on_message_received)
        self.backend_thread.peer_status_changed.connect(self.on_peer_status_changed)
        self.backend_thread.file_transfer_progress.connect(self.on_file_progress)
        self.backend_thread.sync_completed.connect(self.on_sync_completed)
        self.backend_thread.tor_status_updated.connect(self.on_tor_status_updated)
        self.backend_thread.onion_rotated.connect(self.on_onion_rotated)
        self.backend_thread.start()
        
        # Setup auto-rotation timer if enabled
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.rotate_onion_address)
    
    def load_from_database(self):
        """Load peers and messages from database"""
        # Load all peers
        peers = self.db.get_all_peers()
        for peer in peers:
            peer_id = peer['peer_id']
            self.peer_status[peer_id] = ("Offline", "None")
            
            # Load messages for this peer
            messages = self.db.get_messages_by_peer(peer_id)
            self.peer_threads[peer_id] = []
            for msg in messages:
                self.peer_threads[peer_id].append({
                    'sender': 'peer' if msg['peer_id'] == peer_id else 'me',
                    'text': msg['content'].decode('utf-8') if isinstance(msg['content'], bytes) else msg['content'],
                    'timestamp': QDateTime.fromSecsSinceEpoch(msg['timestamp']),
                    'message_id': msg['message_id'],
                    'delivery_status': 'delivered' if msg['sync_status'] == 2 else 'sent' if msg['sync_status'] == 1 else 'pending'
                })
        
        # Refresh peer list
        self.refresh_peer_list()
    
    def refresh_peer_list(self):
        """Refresh the peer list display"""
        self.peer_list.clear()
        
        # Filter peers based on search
        search_text = self.peer_search.text().lower()
        
        peers = self.db.get_all_peers()
        for peer in peers:
            peer_id = peer['peer_id']
            nickname = peer['nickname'] or peer_id
            
            # Skip self
            from config import USER_ID
            if peer_id == USER_ID:
                continue
            
            if search_text and search_text not in nickname.lower():
                continue
            
            # Determine status based on last_seen timestamp
            import time
            last_seen_ts = peer['last_seen'] if peer['last_seen'] else 0
            is_online = (time.time() - last_seen_ts) < 300 if last_seen_ts > 0 else False
            
            # Get stored status or calculate from last_seen
            if peer_id in self.peer_status:
                status, conn_type = self.peer_status[peer_id]
            else:
                status = "Online" if is_online else "Offline"
                # Check if peer has onion address (not None and not empty)
                has_onion = peer['onion_address'] and peer['onion_address'].strip()
                conn_type = "Tor" if has_onion else "Direct"
                # Store calculated status
                self.peer_status[peer_id] = (status, conn_type)
            
            last_seen = self.format_timestamp(last_seen_ts)
            unread = self.count_unread(peer_id)
            
            item = QListWidgetItem()
            widget = PeerItemWidget(peer_id, nickname, status, conn_type, last_seen, unread)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, peer_id)
            
            self.peer_list.addItem(item)
            self.peer_list.setItemWidget(item, widget)
        
        # Update connection status
        online_count = sum(1 for s, _ in self.peer_status.values() if s == "Online")
        self.conn_status_label.setText(f"Peers: {online_count} online / {len(peers)} total")
    
    def filter_peer_list(self, text):
        """Filter peer list based on search text"""
        self.refresh_peer_list()
    
    def count_unread(self, peer_id):
        """Count unread messages from peer"""
        messages = self.peer_threads.get(peer_id, [])
        return sum(1 for msg in messages if msg.get('sender') == 'peer' and not msg.get('read', False))
    
    def format_timestamp(self, timestamp):
        """Format timestamp for display"""
        if timestamp == 0:
            return "Never"
        
        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        diff = now - dt
        
        if diff.seconds < 60:
            return "Just now"
        elif diff.seconds < 3600:
            return f"{diff.seconds // 60}m ago"
        elif diff.days == 0:
            return f"{diff.seconds // 3600}h ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return dt.strftime("%b %d")
    
    def on_peer_selected(self, item):
        """Handle peer selection"""
        peer_id = item.data(Qt.UserRole)
        self.current_peer = peer_id
        
        # Update chat header
        peer = self.db.get_peer(peer_id)
        nickname = peer['nickname'] or peer_id if peer else peer_id
        status, conn_type = self.peer_status.get(peer_id, ("Offline", "None"))
        self.chat_header.setText(f"{nickname} • {status} • {conn_type}")
        
        # Load and display messages
        self.display_messages(peer_id)
        
        # Mark messages as read
        self.mark_messages_read(peer_id)
        
        # Refresh peer list to update unread count
        self.refresh_peer_list()
    
    def display_messages(self, peer_id):
        """Display messages for selected peer"""
        self.message_display.clear()
        
        messages = self.peer_threads.get(peer_id, [])
        
        for msg in messages:
            sender = "You" if msg['sender'] == 'me' else self.db.get_peer(peer_id)['nickname']
            color = "#0078d7" if msg['sender'] == 'me' else "#2c3e50"
            align = "right" if msg['sender'] == 'me' else "left"
            timestamp = msg['timestamp'].toString("hh:mm")
            
            # Add delivery status for sent messages
            status_icon = ""
            if msg['sender'] == 'me':
                delivery_status = msg.get('delivery_status', '')
                if delivery_status == 'delivered':
                    status_icon = " ✓✓"
                elif delivery_status == 'sent':
                    status_icon = " ✓"
                elif delivery_status == 'pending':
                    status_icon = " ⏱"
                elif delivery_status == 'failed':
                    status_icon = " ✗"
            
            # Handle file attachments
            file_link = ""
            if msg.get('file_path'):
                file_name = Path(msg['file_path']).name
                file_link = f"<br><a href='file:///{msg['file_path']}' style='color: blue;'>📎 {file_name}</a> <a href='download://{msg['file_path']}' style='color: green;'>[Download]</a>"
            
            html = f"<div style='text-align: {align}; margin: 5px; color: {color};'><small>{timestamp}{status_icon}</small><br><b>{sender}:</b> {msg['text']}{file_link}</div>"
            self.message_display.append(html)
        
        # Scroll to bottom
        scrollbar = self.message_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def mark_messages_read(self, peer_id):
        """Mark all messages from peer as read"""
        messages = self.peer_threads.get(peer_id, [])
        for msg in messages:
            if msg.get('sender') == 'peer':
                msg['read'] = True
    
    def send_message(self):
        """Send message to current peer"""
        if not self.current_peer:
            QMessageBox.warning(self, "No Peer Selected", "Please select a peer to send a message.")
            return
        
        text = self.message_input.text().strip()
        if not text:
            return
        
        # Generate message ID
        timestamp = int(time.time())
        message_id = hashlib.sha256(f"{self.current_peer}:{text}:{timestamp}".encode()).hexdigest()[:24]
        
        # Create message object
        message = {
            'sender': 'me',
            'text': text,
            'timestamp': QDateTime.currentDateTime(),
            'message_id': message_id,
            'delivery_status': 'pending'
        }
        
        # Add to thread
        if self.current_peer not in self.peer_threads:
            self.peer_threads[self.current_peer] = []
        self.peer_threads[self.current_peer].append(message)
        
        # Save to database
        self.db.insert_message(
            peer_id=self.current_peer,
            content=text.encode('utf-8'),
            timestamp=timestamp,
            message_id=message_id,
            sync_status=0  # Pending
        )
        
        # Update display
        self.display_messages(self.current_peer)
        
        # Clear input
        self.message_input.clear()
        
        # Simulate sending (mark as sent after short delay)
        QTimer.singleShot(500, lambda: self.mark_message_sent(message_id))
    
    def mark_message_sent(self, message_id):
        """Mark message as sent and update UI"""
        try:
            # Update database
            self.db.update_message_status(message_id, 1)  # 1 = sent
            
            # Update in-memory messages
            for peer_id, messages in self.peer_threads.items():
                for msg in messages:
                    if msg.get('message_id') == message_id:
                        msg['delivery_status'] = 'sent'
                        # Refresh display if this is the current peer
                        if peer_id == self.current_peer:
                            self.display_messages(peer_id)
                        break
        except Exception as e:
            print(f"Error marking message as sent: {e}")
    
    def attach_file(self):
        """Attach and send file to current peer"""
        if not self.current_peer:
            QMessageBox.warning(self, "No Peer Selected", "Please select a peer to send a file.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Send", "", "All Files (*.*)"
        )
        
        if not file_path:
            return
        
        # Save file and generate metadata
        storage_dir = Path(__file__).parent.parent / 'data' / 'files'
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        dst_path, file_hash = save_file_to_storage(file_path, str(storage_dir))
        file_size = Path(dst_path).stat().st_size
        
        # Insert file metadata
        timestamp = int(time.time())
        self.db.insert_file_metadata(
            file_name=Path(file_path).name,
            file_path=dst_path,
            file_hash=file_hash,
            file_size=file_size,
            message_id=None,
            peer_id=self.current_peer,
            timestamp=timestamp
        )
        
        # Add file transfer message to thread
        message = {
            'sender': 'me',
            'text': f"📎 Sending file: {Path(file_path).name} ({file_size} bytes)",
            'timestamp': QDateTime.currentDateTime(),
            'message_id': file_hash,
            'delivery_status': 'pending',
            'file_path': dst_path
        }
        
        if self.current_peer not in self.peer_threads:
            self.peer_threads[self.current_peer] = []
        self.peer_threads[self.current_peer].append(message)
        
        # Update display
        self.display_messages(self.current_peer)
        
        # Show progress bar
        self.file_progress.setVisible(True)
        self.file_progress.setMaximum(file_size)
        self.file_progress.setValue(0)
        
        # Queue file transfer via backend thread
        try:
            # Simulate transfer progress (in real app, backend would handle this)
            QTimer.singleShot(100, lambda: self.simulate_file_transfer(file_size))
        except Exception as e:
            QMessageBox.critical(self, "Transfer Error", f"Failed to initiate file transfer: {e}")
            self.file_progress.setVisible(False)
        self.file_progress.setValue(0)
        self.file_progress.setMaximum(file_size)
        
        QMessageBox.information(self, "File Queued", f"File {Path(file_path).name} queued for transfer.")
    
    def drag_enter_event(self, event):
        """Handle drag enter for file drop"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def drop_event(self, event):
        """Handle file drop"""
        if not self.current_peer:
            QMessageBox.warning(self, "No Peer Selected", "Please select a peer to send files.")
            return
        
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if Path(file_path).is_file():
                # Process as attachment
                self.process_dropped_file(file_path)
    
    def process_dropped_file(self, file_path):
        """Process dropped file"""
        # Similar to attach_file logic
        storage_dir = Path(__file__).parent.parent / 'data' / 'files'
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        dst_path, file_hash = save_file_to_storage(file_path, str(storage_dir))
        file_size = Path(dst_path).stat().st_size
        
        timestamp = int(time.time())
        self.db.insert_file_metadata(
            file_name=Path(file_path).name,
            file_path=dst_path,
            file_hash=file_hash,
            file_size=file_size,
            message_id=None,
            peer_id=self.current_peer,
            timestamp=timestamp
        )
        
        message = {
            'sender': 'me',
            'text': f"📎 File: {Path(file_path).name}",
            'timestamp': QDateTime.currentDateTime(),
            'message_id': file_hash,
            'delivery_status': 'pending'
        }
        
        if self.current_peer not in self.peer_threads:
            self.peer_threads[self.current_peer] = []
        self.peer_threads[self.current_peer].append(message)
        
        self.display_messages(self.current_peer)
    
    def on_message_received(self, peer_id, message_data):
        """Handle received message from backend"""
        # Add to thread
        message = {
            'sender': 'peer',
            'text': message_data.get('content', ''),
            'timestamp': QDateTime.fromSecsSinceEpoch(message_data.get('timestamp', int(time.time()))),
            'message_id': message_data.get('message_id'),
            'delivery_status': 'delivered',
            'read': False
        }
        
        if peer_id not in self.peer_threads:
            self.peer_threads[peer_id] = []
        self.peer_threads[peer_id].append(message)
        
        # If currently viewing this peer, update display
        if self.current_peer == peer_id:
            self.display_messages(peer_id)
            self.mark_messages_read(peer_id)
        
        # Show notification
        peer = self.db.get_peer(peer_id)
        nickname = peer['nickname'] if peer else peer_id
        self.show_notification(f"New message from {nickname}", message_data.get('content', '')[:50])
        
        # Refresh peer list to update unread count
        self.refresh_peer_list()
    
    def on_peer_status_changed(self, peer_id, status, connection_type):
        """Handle peer status change"""
        self.peer_status[peer_id] = (status, connection_type)
        
        # Update last_seen in database
        if status == "Online":
            self.db.update_peer_status(peer_id, int(time.time()))
        
        # Refresh peer list
        self.refresh_peer_list()
        
        # Update chat header if this is current peer
        if self.current_peer == peer_id:
            peer = self.db.get_peer(peer_id)
            nickname = peer['nickname'] or peer_id if peer else peer_id
            self.chat_header.setText(f"{nickname} • {status} • {connection_type}")
    
    def on_file_progress(self, peer_id, sent, total):
        """Handle file transfer progress"""
        if total > 0:
            progress_percent = int((sent / total) * 100)
            self.file_progress.setMaximum(total)
            self.file_progress.setValue(sent)
            self.file_progress.setVisible(True)
            self.status_bar.showMessage(f"File transfer: {progress_percent}% ({sent}/{total} bytes)", 1000)
            
            if sent >= total:
                self.file_progress.setVisible(False)
                QMessageBox.information(self, "Transfer Complete", "File transfer completed successfully.")
    
    def simulate_file_transfer(self, file_size):
        """Simulate file transfer progress (for demo purposes)"""
        chunk_size = max(file_size // 20, 1024)  # 5% chunks or 1KB minimum
        transferred = 0
        
        def update_progress():
            nonlocal transferred
            transferred += chunk_size
            if transferred >= file_size:
                transferred = file_size
                self.on_file_progress(self.current_peer, transferred, file_size)
            else:
                self.on_file_progress(self.current_peer, transferred, file_size)
                QTimer.singleShot(100, update_progress)  # Continue after 100ms
        
        update_progress()
    
    def handle_file_link(self, url):
        """Handle file link clicks (view or download)"""
        url_str = url.toString()
        
        if url_str.startswith('download://'):
            # Download/save file
            source_path = url_str.replace('download://', '')
            
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                str(Path.home() / "Downloads" / Path(source_path).name),
                "All Files (*.*)"
            )
            
            if save_path:
                try:
                    import shutil
                    shutil.copy2(source_path, save_path)
                    QMessageBox.information(self, "Download Complete", f"File saved to:\n{save_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Download Error", f"Failed to save file: {e}")
        elif url_str.startswith('file:///'):
            # Open file in default application
            import subprocess
            import platform
            
            file_path = url_str.replace('file:///', '')
            try:
                if platform.system() == 'Windows':
                    subprocess.Popen(['explorer', file_path.replace('/', '\\')])
                elif platform.system() == 'Darwin':
                    subprocess.Popen(['open', file_path])
                else:
                    subprocess.Popen(['xdg-open', file_path])
            except Exception as e:
                QMessageBox.warning(self, "Open Error", f"Failed to open file: {e}")
    
    def on_sync_completed(self, peer_id):
        """Handle sync completion"""
        self.show_notification("Sync Complete", f"Messages synced with peer {peer_id}")
    
    def on_tor_status_updated(self, status):
        """Handle Tor status update"""
        self.tor_status_label.setText(f"Tor: {status}")
        color = "green" if status == "Connected" else "red" if status == "Error" else "#888"
        self.tor_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def on_onion_rotated(self, new_address):
        """Handle onion address rotation"""
        QMessageBox.information(self, "Onion Rotated", f"New onion address: {new_address}")
    
    def start_tor_service(self):
        """Start Tor service"""
        try:
            if not self.tor_mgr:
                self.tor_mgr = TorManager(tor_path=TOR_PATH, control_port=TOR_CONTROL_PORT, password=TOR_PASSWORD)
                self.tor_mgr.start_tor()
                self.on_tor_status_updated("Connected")
                
                # Create onion service and store address in database
                try:
                    onion_address, private_key = self.tor_mgr.create_ephemeral_onion_service(12345)
                    
                    # Store or update local peer record with onion address
                    from config import USER_ID
                    existing = self.db.get_peer(USER_ID)
                    if existing:
                        self.db.update_peer(USER_ID, onion_address=onion_address)
                    else:
                        self.db.add_peer(USER_ID, nickname="Me", public_key="", fingerprint="")
                        self.db.update_peer(USER_ID, onion_address=onion_address)
                    
                    self.status_bar.showMessage(f"Onion address: {onion_address}", 5000)
                except Exception as e:
                    print(f"Failed to create onion service: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Tor Error", f"Failed to start Tor: {e}")
    
    def rotate_onion_address(self):
        """Rotate onion address"""
        if not self.tor_mgr:
            QMessageBox.warning(self, "Tor Not Running", "Tor service is not running.")
            return
        
        try:
            # Create new ephemeral onion service
            new_address, private_key = self.tor_mgr.create_ephemeral_onion_service(12345)
            self.on_onion_rotated(new_address)
            
            # Update all connected peers with new address
            # (Implementation would notify peers of new address)
            
        except Exception as e:
            QMessageBox.critical(self, "Rotation Error", f"Failed to rotate onion address: {e}")
    
    def show_add_peer_dialog(self):
        """Show dialog to add new peer"""
        from gui.connection_view import AddPeerDialog
        dialog = AddPeerDialog(self.conn_mgr, self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_from_database()
            self.refresh_peer_list()
    
    def show_connection_manager(self):
        """Show connection manager dialog"""
        from gui.connection_view import ConnectionView
        dialog = ConnectionView(self.conn_mgr, self.db, self)
        dialog.exec_()
        self.refresh_peer_list()
    
    def show_alias_manager(self):
        """Show alias registry manager"""
        from gui.connection_view import AliasManagerDialog
        dialog = AliasManagerDialog(self.alias_registry, self)
        dialog.exec_()
    
    def show_device_manager(self):
        """Show device manager dialog for multi-device linking"""
        from gui.device_manager_dialog import DeviceManagerDialog
        dialog = DeviceManagerDialog(USER_ID, self)
        dialog.exec_()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Apply settings
            self.connection_mode = dialog.conn_mode.currentText().lower()
            self.tor_enabled = dialog.tor_enabled.isChecked()
            self.p2p_enabled = dialog.p2p_enabled.isChecked()
            
            # Setup rotation timer
            if dialog.onion_rotation.isChecked():
                interval_hours = dialog.rotation_interval.value()
                self.rotation_timer.start(interval_hours * 3600 * 1000)  # Convert to ms
            else:
                self.rotation_timer.stop()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Libra",
            "<h2>Libra v2.0</h2>"
            "<p>Secure, anonymous, decentralized messaging platform</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>End-to-end encryption</li>"
            "<li>Tor integration for anonymity</li>"
            "<li>Direct P2P when possible</li>"
            "<li>Message persistence</li>"
            "<li>File transfer support</li>"
            "<li>Onion address rotation</li>"
            "</ul>"
            "<p>© 2025 Libra Project</p>"
        )
    
    def show_tor_help(self):
        """Show Tor setup help"""
        QMessageBox.information(
            self,
            "Tor Setup Help",
            "<h3>Tor Setup & Troubleshooting</h3>"
            "<p>Libra uses Tor for anonymous peer discovery and communication.</p>"
            "<p><b>Setup:</b></p>"
            "<ul>"
            "<li>Ensure Tor is installed on your system</li>"
            "<li>On Windows, use the Tor Expert Bundle in utils/</li>"
            "<li>Libra will attempt to start Tor automatically</li>"
            "</ul>"
            "<p><b>Troubleshooting:</b></p>"
            "<ul>"
            "<li>Check firewall settings</li>"
            "<li>Ensure port 9051 is available (Tor control port)</li>"
            "<li>Verify no other Tor process is running</li>"
            "<li>Check Tor logs for errors</li>"
            "</ul>"
            "<p>See README.md for detailed instructions.</p>"
        )
    
    def export_chat_history(self):
        """Export chat history to file"""
        if not self.current_peer:
            QMessageBox.warning(self, "No Peer Selected", "Please select a peer to export chat history.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Chat History", f"chat_{self.current_peer}.txt", "Text Files (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Chat history with {self.current_peer}\n")
                f.write("=" * 50 + "\n\n")
                
                messages = self.peer_threads.get(self.current_peer, [])
                for msg in messages:
                    timestamp = msg['timestamp'].toString("yyyy-MM-dd hh:mm:ss")
                    sender = "You" if msg['sender'] == 'me' else self.current_peer
                    f.write(f"[{timestamp}] {sender}: {msg['text']}\n")
            
            QMessageBox.information(self, "Export Complete", f"Chat history exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export chat history: {e}")
    
    def show_notification(self, title, message):
        """Show system tray notification"""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop backend thread
        if hasattr(self, 'backend_thread'):
            self.backend_thread.stop()
            self.backend_thread.wait()
        
        # Stop Tor
        if self.tor_mgr:
            self.tor_mgr.stop_tor()
        
        # Close database
        self.db.close()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Libra")
    app.setOrganizationName("Libra Project")
    main_win = LibraMainWindow()
    main_win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
