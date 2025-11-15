"""
Libra v2.0 Connection Management UI - Complete Refactored
Supports: Tor/P2P connections, alias management, onion address handling, peer discovery
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QInputDialog, QTextEdit,
    QTabWidget, QGroupBox, QComboBox, QCheckBox, QSpinBox, QFormLayout, QScrollArea
)
from PyQt5.QtGui import QIcon, QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, pyqtSignal
import json
import socket

from peer.connection_manager import ConnectionManager
from db.db_handler import DBHandler
from utils.alias_registry import AliasRegistry
from peer.peer_discovery import PeerDiscovery


class AddPeerDialog(QDialog):
    """Dialog for adding a new peer connection"""
    def __init__(self, connection_manager, db_handler, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager
        self.db = db_handler
        # Use parent's alias registry if available, otherwise create one
        self.alias_registry = getattr(parent, 'alias_registry', None) or AliasRegistry()
        self.setWindowTitle("Add New Peer")
        self.setModal(True)
        self.resize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        # Title
        title_label = QLabel("Add New Peer")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        # Onion address subtitle
        from config import USER_ID
        self.onion_label = QLabel("My Onion Address:")
        self.onion_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.onion_label)
        self.onion_value_label = QLabel()
        self.onion_value_label.setFont(QFont("Arial", 11))
        self.onion_value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.onion_value_label)
        self.refresh_onion_address()
        
        # Tab widget for different connection methods
        tabs = QTabWidget()
        
        # Manual connection tab
        manual_tab = QWidget()
        manual_layout = QFormLayout()
        
        self.peer_id_input = QLineEdit()
        self.peer_id_input.setPlaceholderText("Enter peer ID or onion address")
        manual_layout.addRow("Peer ID:", self.peer_id_input)
        
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("Optional nickname")
        manual_layout.addRow("Nickname:", self.nickname_input)
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP:PORT (for direct connection)")
        manual_layout.addRow("IP Address:", self.ip_input)
        
        self.conn_type = QComboBox()
        self.conn_type.addItems(["Auto", "Tor Only", "Direct P2P Only"])
        manual_layout.addRow("Connection Type:", self.conn_type)
        
        connect_btn = QPushButton("Add Peer")
        connect_btn.clicked.connect(self.add_peer_manual)
        manual_layout.addRow(connect_btn)
        
        manual_tab.setLayout(manual_layout)
        tabs.addTab(manual_tab, "Manual Entry")
        
        alias_tab = QWidget()
        alias_layout = QVBoxLayout()
        alias_layout.addWidget(QLabel("Search for peer by alias (three-word phrase):"))
        alias_search_layout = QHBoxLayout()
        self.alias_search_input = QLineEdit()
        self.alias_search_input.setPlaceholderText("e.g., happy-dolphin-sky")
        alias_search_layout.addWidget(self.alias_search_input)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_alias)
        alias_search_layout.addWidget(search_btn)
        alias_layout.addLayout(alias_search_layout)
        self.alias_results = QListWidget()
        alias_layout.addWidget(QLabel("Search Results:"))
        alias_layout.addWidget(self.alias_results)
        add_alias_btn = QPushButton("Add Selected Peer")
        add_alias_btn.clicked.connect(self.add_peer_from_alias)
        alias_layout.addWidget(add_alias_btn)
        alias_tab.setLayout(alias_layout)
        tabs.addTab(alias_tab, "Alias Discovery")
        
        # LAN discovery tab
        lan_tab = QWidget()
        lan_layout = QVBoxLayout()
        
        lan_layout.addWidget(QLabel("Discover peers on local network:"))
        
        discover_btn = QPushButton("Start Discovery")
        discover_btn.clicked.connect(self.start_lan_discovery)
        lan_layout.addWidget(discover_btn)
        
        self.lan_peers = QListWidget()
        lan_layout.addWidget(QLabel("Discovered Peers:"))
        lan_layout.addWidget(self.lan_peers)
        
        add_lan_btn = QPushButton("Add Selected Peer")
        add_lan_btn.clicked.connect(self.add_peer_from_lan)
        lan_layout.addWidget(add_lan_btn)
        
        lan_tab.setLayout(lan_layout)
        tabs.addTab(lan_tab, "LAN Discovery")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def refresh_onion_address(self):
        """Refresh the displayed onion address from the database."""
        try:
            from config import USER_ID
            onion_address = self.db.get_my_onion_address(USER_ID)
            if onion_address:
                self.onion_value_label.setText(onion_address)
            else:
                self.onion_value_label.setText("Not available (Tor not started)")
        except Exception as e:
            self.onion_value_label.setText(f"Error: {str(e)}")
    
    def add_peer_manual(self):
        """Add peer manually"""
        peer_id = self.peer_id_input.text().strip()
        nickname = self.nickname_input.text().strip()
        ip_port = self.ip_input.text().strip()
        
        if not peer_id:
            QMessageBox.warning(self, "Input Error", "Please enter a peer ID or onion address.")
            return
        
        try:
            # Add peer to database
            self.db.add_peer(
                peer_id=peer_id,
                public_key="",
                nickname=nickname or peer_id,
                fingerprint=""
            )
            
            QMessageBox.information(self, "Peer Added", f"Peer '{nickname or peer_id}' added successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add peer: {e}")
        
    
    def search_alias(self):
        """Search for peers by alias"""
        alias = self.alias_search_input.text().strip()
        
        if not alias:
            QMessageBox.warning(self, "Input Error", "Please enter an alias to search.")
            return
        
        # Search alias registry (use instance registry)
        result = self.alias_registry.lookup_alias(alias)
        
        self.alias_results.clear()
        
        if not result:
            QMessageBox.information(self, "No Results", f"No peers found with alias '{alias}'.\n\nNote: Aliases must be published by peers on the network first.")
            return
        
        # lookup_alias returns a single AliasRecord object, not a list
        item = QListWidgetItem(f"{result.alias} - {result.onion[:16]}...")
        item.setData(Qt.UserRole, {
            'alias': result.alias,
            'peer_id': result.onion,
            'public_key': result.public_key,
            'onion_address': result.onion
        })
        self.alias_results.addItem(item)
    
    def add_peer_from_alias(self):
        """Add peer from alias search results"""
        selected = self.alias_results.currentItem()
        
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a peer from the results.")
            return
        
        data = selected.data(Qt.UserRole)
        peer_id = data['peer_id']
        alias = data['alias']
        public_key = data.get('public_key', '')
        
        try:
            self.db.add_peer(
                peer_id=peer_id,
                public_key=public_key,
                nickname=alias
            )
            
            QMessageBox.information(self, "Peer Added", f"Peer {alias} added successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add peer: {e}")
    
    def start_lan_discovery(self):
        """Start LAN peer discovery and update UI with discovered peers.
        
        How it works:
        - Your device broadcasts a signed UDP beacon on the local network
        - The beacon contains your peer_id, public_key, and timestamp
        - Other Libra peers on the same network do the same
        - Each peer verifies the signature and adds discovered peers to the database
        - This dialog periodically refreshes to show newly discovered peers
        """
        self.lan_peers.clear()
        try:
            from config import USER_ID, key_paths, ensure_dirs
            from utils.crypto_utils import generate_rsa_keypair, save_keys_for_peer
            
            # Ensure key directory exists
            ensure_dirs()
            
            # Check if keys exist, generate if needed
            priv_path, pub_path = key_paths(USER_ID)
            if not priv_path.exists() or not pub_path.exists():
                QMessageBox.information(
                    self,
                    "Generating Keys",
                    f"Generating cryptographic keys for peer discovery...\n\nKeys will be stored at:\n{priv_path}"
                )
                passphrase = b"test_passphrase"  # TODO: Retrieve from secure storage
                priv, pub = generate_rsa_keypair()
                save_keys_for_peer(priv, pub, passphrase, USER_ID)
            else:
                passphrase = b"test_passphrase"  # TODO: Retrieve from secure storage
            
            # Initialize peer discovery (broadcasts UDP beacons)
            self.discovery = PeerDiscovery(USER_ID, passphrase)
            self.discovery.start()
            
            QMessageBox.information(
                self,
                "Discovery Started",
                "LAN discovery started via UDP broadcast beacons.\n\n"
                "Your device is broadcasting signed beacons containing:\n"
                "• Your peer ID\n"
                "• Your public key\n"
                "• Current timestamp\n\n"
                "Other Libra peers on this network will:\n"
                "• Receive your beacon\n"
                "• Verify the signature\n"
                "• Add you to their peer list\n\n"
                "Discovered peers will appear below within a few seconds."
            )
            
            # Periodically refresh LAN peers from DB
            from PyQt5.QtCore import QTimer
            self.lan_timer = QTimer(self)
            self.lan_timer.timeout.connect(self.refresh_lan_peers)
            self.lan_timer.start(2000)  # Refresh every 2 seconds
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start discovery: {e}")

    def refresh_lan_peers(self):
        """Refresh the LAN peers list from the DB."""
        # Save current selection
        current_item = self.lan_peers.currentItem()
        selected_peer_id = current_item.data(Qt.UserRole)['peer_id'] if current_item else None
        
        self.lan_peers.clear()
        peers = self.db.get_all_peers()
        new_selected_item = None
        
        for peer in peers:
            peer_dict = dict(peer)  # Convert Row to dict
            peer_id = peer_dict.get('peer_id')
            if peer_id and peer_id != 'default_user':  # Exclude self
                display = peer_dict.get('nickname', peer_id)
                item = QListWidgetItem(f"{display} - {peer_id[:16]}...")
                item.setData(Qt.UserRole, peer_dict)
                self.lan_peers.addItem(item)
                
                # Re-select previously selected item
                if selected_peer_id and peer_id == selected_peer_id:
                    new_selected_item = item
        
        # Restore selection
        if new_selected_item:
            self.lan_peers.setCurrentItem(new_selected_item)
    
    def add_peer_from_lan(self):
        """Add peer from LAN discovery results"""
        selected = self.lan_peers.currentItem()
        
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a peer from the discovered list.")
            return
        
        data = selected.data(Qt.UserRole)
        peer_id = data['peer_id']
        nickname = data.get('nickname', peer_id)
        public_key = data.get('public_key', '')
        
        try:
            # Peer should already be in DB from discovery, but ensure it's there
            existing = self.db.get_all_peers()
            peer_exists = any(p['peer_id'] == peer_id for p in existing)
            
            if not peer_exists:
                self.db.add_peer(
                    peer_id=peer_id,
                    public_key=public_key,
                    nickname=nickname
                )
            
            QMessageBox.information(self, "Peer Added", f"Peer {nickname} added successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add peer: {e}")


class PeerDetailWidget(QWidget):
    """Widget showing detailed peer information"""
    def __init__(self, peer_data):
        super().__init__()
        # Convert Row to dict if needed
        if hasattr(peer_data, 'keys'):
            peer_data = dict(peer_data)
        self.peer_data = peer_data
        layout = QVBoxLayout()
        
        # Peer ID
        layout.addWidget(QLabel(f"<b>Peer ID:</b> {peer_data['peer_id']}"))
        
        # Nickname
        layout.addWidget(QLabel(f"<b>Nickname:</b> {peer_data.get('nickname', 'N/A')}"))
        
        # Connection status
        status = peer_data.get('status', 'Offline')
        conn_type = peer_data.get('connection_type', 'None')
        layout.addWidget(QLabel(f"<b>Status:</b> {status} ({conn_type})"))
        
        # Onion address (if applicable)
        if 'onion_address' in peer_data and peer_data['onion_address']:
            layout.addWidget(QLabel(f"<b>Onion Address:</b> {peer_data['onion_address']}"))
        
        # IP address (if applicable)
        if 'ip_address' in peer_data and peer_data.get('ip_address'):
            layout.addWidget(QLabel(f"<b>IP Address:</b> {peer_data['ip_address']}"))
        
        # Public key fingerprint
        if 'public_key' in peer_data and peer_data['public_key']:
            import hashlib
            pub_key = peer_data['public_key']
            # Handle both string and bytes
            if isinstance(pub_key, str):
                pub_key = pub_key.encode()
            fingerprint = hashlib.sha256(pub_key).hexdigest()[:16]
            layout.addWidget(QLabel(f"<b>Key Fingerprint:</b> {fingerprint}"))
        
        # Last seen
        last_seen = peer_data.get('last_seen', 0)
        if last_seen and last_seen > 0:
            from datetime import datetime
            dt = datetime.fromtimestamp(last_seen)
            layout.addWidget(QLabel(f"<b>Last Seen:</b> {dt.strftime('%Y-%m-%d %H:%M:%S')}"))
        
        self.setLayout(layout)


class AliasManagerDialog(QDialog):
    """Dialog for managing aliases"""
    def __init__(self, alias_registry, parent=None):
        super().__init__(parent)
        self.alias_registry = alias_registry
        self.setWindowTitle("Alias Manager")
        self.setModal(True)
        self.resize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # My aliases section
        my_group = QGroupBox("My Published Aliases")
        my_layout = QVBoxLayout()
        
        self.my_alias_list = QListWidget()
        my_layout.addWidget(self.my_alias_list)
        
        my_btn_layout = QHBoxLayout()
        
        publish_btn = QPushButton("Publish New Alias")
        publish_btn.clicked.connect(self.publish_alias)
        my_btn_layout.addWidget(publish_btn)
        
        revoke_btn = QPushButton("Revoke Selected")
        revoke_btn.clicked.connect(self.revoke_alias)
        my_btn_layout.addWidget(revoke_btn)
        
        my_layout.addLayout(my_btn_layout)
        my_group.setLayout(my_layout)
        layout.addWidget(my_group)
        
        # Discovered aliases section
        discovered_group = QGroupBox("Discovered Peer Aliases")
        discovered_layout = QVBoxLayout()
        
        self.discovered_list = QListWidget()
        discovered_layout.addWidget(self.discovered_list)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_aliases)
        discovered_layout.addWidget(refresh_btn)
        
        discovered_group.setLayout(discovered_layout)
        layout.addWidget(discovered_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_aliases()
    
    def publish_alias(self):
        """Publish a new alias"""
        # Generate or input alias
        alias, ok = QInputDialog.getText(
            self,
            "Publish Alias",
            "Enter alias (leave empty to auto-generate):"
        )
        
        if not ok:
            return
        
        try:
            # Get local device info (would come from config)
            onion = "local_onion_address"  # Placeholder
            public_key = b"public_key_bytes"  # Placeholder
            if not alias:
                from utils.alias_generator import generate_alias
                alias = generate_alias()
            # Publish to registry
            self.alias_registry.publish_alias(onion=onion, public_key=public_key, alias=alias, is_public=True)
            QMessageBox.information(self, "Success", f"Alias '{alias}' published successfully.")
            self.refresh_aliases()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to publish alias: {e}")
    
    def revoke_alias(self):
        """Revoke selected alias"""
        selected = self.my_alias_list.currentItem()
        
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select an alias to revoke.")
            return
        
        alias = selected.text().split(' ')[0]  # Extract alias from display text
        
        confirm = QMessageBox.question(
            self,
            "Confirm Revoke",
            f"Are you sure you want to revoke alias '{alias}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                removed = self.alias_registry.remove_alias(alias)
                if removed:
                    QMessageBox.information(self, "Success", f"Alias '{alias}' revoked.")
                else:
                    QMessageBox.warning(self, "Not Found", f"Alias '{alias}' not found in registry.")
                self.refresh_aliases()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to revoke alias: {e}")
    
    def refresh_aliases(self):
        """Refresh alias lists"""
        # Refresh my aliases
        self.my_alias_list.clear()
        # Query local published aliases from registry
        for alias, record in self.alias_registry._public_registry.items():
            self.my_alias_list.addItem(f"{alias} (published)")
        # Refresh discovered aliases
        self.discovered_list.clear()
        # In real implementation, query registry for discovered aliases
        # Example:
        # for alias, record in self.alias_registry._public_registry.items():
        #     self.discovered_list.addItem(f"{alias} ({record.onion[:8]}...)")


class ConnectionView(QDialog):
    """Main connection management dialog"""
    
    peer_connected = pyqtSignal(str)  # peer_id
    peer_disconnected = pyqtSignal(str)  # peer_id
    
    def __init__(self, connection_manager, db_handler, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager
        self.db = db_handler
        self.setWindowTitle("Connection Manager")
        self.resize(800, 600)
        self.init_ui()
        self.refresh_peer_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Connection status overview
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        status_layout.addWidget(self.status_label)
        
        self.tor_status_label = QLabel("Tor: Unknown")
        status_layout.addWidget(self.tor_status_label)
        
        self.p2p_status_label = QLabel("P2P: Unknown")
        status_layout.addWidget(self.p2p_status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Peer list
        peers_group = QGroupBox("Connected Peers")
        peers_layout = QVBoxLayout()
        
        self.peer_list = QListWidget()
        self.peer_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.peer_list.customContextMenuRequested.connect(self.show_peer_context_menu)
        self.peer_list.itemDoubleClicked.connect(self.show_peer_details)
        peers_layout.addWidget(self.peer_list)
        
        peers_group.setLayout(peers_layout)
        layout.addWidget(peers_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        add_peer_btn = QPushButton("Add Peer")
        add_peer_btn.clicked.connect(self.show_add_peer_dialog)
        btn_layout.addWidget(add_peer_btn)
        
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_peer_list)
        btn_layout.addWidget(refresh_btn)
        
        layout.addLayout(btn_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def refresh_peer_list(self):
        """Refresh the peer list"""
        self.peer_list.clear()
        
        peers = self.db.get_all_peers()
        
        for peer in peers:
            peer_id = peer['peer_id']
            nickname = peer['nickname'] or peer_id
            status = "Online"  # Would be determined by connection manager
            conn_type = "Tor"  # Would be determined by connection type
            
            item = QListWidgetItem(f"{nickname} - {status} ({conn_type})")
            item.setData(Qt.UserRole, peer)
            self.peer_list.addItem(item)
        
        # Update status label
        self.status_label.setText(f"Total peers: {len(peers)}")
    
    def show_peer_context_menu(self, position):
        """Show context menu for peer"""
        item = self.peer_list.itemAt(position)
        
        if not item:
            return
        
        peer = item.data(Qt.UserRole)
        
        menu = QMenu()
        
        details_action = menu.addAction("View Details")
        nickname_action = menu.addAction("Change Nickname")
        menu.addSeparator()
        connect_action = menu.addAction("Connect")
        disconnect_action = menu.addAction("Disconnect")
        menu.addSeparator()
        remove_action = menu.addAction("Remove Peer")
        
        action = menu.exec_(self.peer_list.viewport().mapToGlobal(position))
        
        if action == details_action:
            self.show_peer_details(item)
        elif action == nickname_action:
            self.change_peer_nickname(peer)
        elif action == connect_action:
            self.connect_to_peer(peer)
        elif action == disconnect_action:
            self.disconnect_from_peer(peer)
        elif action == remove_action:
            self.remove_peer(peer)
    
    def show_peer_details(self, item):
        """Show detailed peer information"""
        peer = item.data(Qt.UserRole)
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Peer Details - {peer['nickname']}")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout()
        
        detail_widget = PeerDetailWidget(peer)
        layout.addWidget(detail_widget)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def change_peer_nickname(self, peer):
        """Change peer nickname"""
        new_nickname, ok = QInputDialog.getText(
            self,
            "Change Nickname",
            "Enter new nickname:",
            text=peer['nickname']
        )
        
        if ok and new_nickname:
            try:
                self.db.update_peer_nickname(peer['peer_id'], new_nickname)
                QMessageBox.information(self, "Success", "Nickname updated successfully.")
                self.refresh_peer_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update nickname: {e}")
    
    def connect_to_peer(self, peer):
        """Connect to peer"""
        try:
            # Attempt connection via connection manager
            QMessageBox.information(self, "Connecting", f"Attempting to connect to {peer['nickname']}...")
            # In real implementation, would call connection manager
            self.peer_connected.emit(peer['peer_id'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect: {e}")
    
    def disconnect_from_peer(self, peer):
        """Disconnect from peer"""
        try:
            # Disconnect via connection manager
            QMessageBox.information(self, "Disconnecting", f"Disconnecting from {peer['nickname']}...")
            # In real implementation, would call connection manager
            self.peer_disconnected.emit(peer['peer_id'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to disconnect: {e}")
    
    def remove_peer(self, peer):
        """Remove peer"""
        confirm = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Are you sure you want to remove {peer['nickname']}?\nThis will delete all messages and files.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                self.db.delete_peer(peer['peer_id'])
                QMessageBox.information(self, "Success", "Peer removed successfully.")
                self.refresh_peer_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove peer: {e}")
    
    def show_add_peer_dialog(self):
        """Show add peer dialog"""
        dialog = AddPeerDialog(self.conn_mgr, self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_peer_list()
    


def main():
    """Test the connection view"""
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    db = DBHandler()
    db.init_db()
    conn_mgr = ConnectionManager()
    
    window = ConnectionView(conn_mgr, db)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
