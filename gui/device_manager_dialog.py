"""
Device Manager Dialog - Multi-device linking and management for Libra
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget, QGroupBox,
    QTextEdit, QFormLayout, QFrame, QSpinBox
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QTimer

from utils.device_linking import DeviceLinking, validate_pairing_code


class DeviceManagerDialog(QDialog):
    """Dialog for managing linked devices and pairing new ones"""
    
    def __init__(self, user_id: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.device_linker = DeviceLinking()
        self.current_pairing_code = None
        
        self.setWindowTitle("Device Manager - Multi-Device Sync")
        self.setModal(True)
        self.resize(700, 500)
        self.init_ui()
        self.refresh_devices()
        
        # Auto-cleanup expired codes every 30 seconds
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.cleanup_expired_codes)
        self.cleanup_timer.start(30000)
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("🔗 Device Linking & Management")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        header.setStyleSheet("color: #0078d7; padding: 10px;")
        layout.addWidget(header)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: Linked Devices
        devices_tab = self.create_devices_tab()
        tabs.addTab(devices_tab, "Linked Devices")
        
        # Tab 2: Add New Device
        add_tab = self.create_add_device_tab()
        tabs.addTab(add_tab, "Add New Device")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def create_devices_tab(self):
        """Create tab showing linked devices"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Info label
        info = QLabel("Devices linked to your account for multi-device synchronization:")
        info.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(info)
        
        # Device list
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #e3f2fd;
                color: black;
            }
        """)
        layout.addWidget(self.device_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_devices)
        btn_layout.addWidget(refresh_btn)
        
        rename_btn = QPushButton("✏️ Rename")
        rename_btn.clicked.connect(self.rename_device)
        btn_layout.addWidget(rename_btn)
        
        revoke_btn = QPushButton("🗑️ Revoke Access")
        revoke_btn.setStyleSheet("background: #e74c3c; color: white;")
        revoke_btn.clicked.connect(self.revoke_device)
        btn_layout.addWidget(revoke_btn)
        
        layout.addLayout(btn_layout)
        
        widget.setLayout(layout)
        return widget
    
    def create_add_device_tab(self):
        """Create tab for adding new devices"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Generate Pairing Code Section
        generate_group = QGroupBox("Generate Pairing Code")
        generate_layout = QVBoxLayout()
        
        generate_layout.addWidget(QLabel("Generate a temporary code to pair another device:"))
        
        form = QFormLayout()
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("e.g., My Phone, Work Laptop")
        form.addRow("Device Name:", self.device_name_input)
        
        self.expiry_input = QSpinBox()
        self.expiry_input.setRange(1, 60)
        self.expiry_input.setValue(5)
        self.expiry_input.setSuffix(" minutes")
        form.addRow("Code Expiry:", self.expiry_input)
        
        generate_layout.addLayout(form)
        
        generate_btn = QPushButton("🔑 Generate Pairing Code")
        generate_btn.setStyleSheet("background: #27ae60; color: white; padding: 10px;")
        generate_btn.clicked.connect(self.generate_code)
        generate_layout.addWidget(generate_btn)
        
        # Display area for generated code
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setMaximumHeight(100)
        self.code_display.setStyleSheet("""
            QTextEdit {
                background: #f0f0f0;
                border: 2px solid #0078d7;
                border-radius: 5px;
                font-size: 16pt;
                font-weight: bold;
                color: #0078d7;
                text-align: center;
            }
        """)
        self.code_display.setPlaceholderText("Generated code will appear here...")
        generate_layout.addWidget(self.code_display)
        
        # QR Code display
        
        generate_group.setLayout(generate_layout)
        layout.addWidget(generate_group)
        
        # Enter Pairing Code Section
        enter_group = QGroupBox("Enter Pairing Code")
        enter_layout = QVBoxLayout()
        
        enter_layout.addWidget(QLabel("Enter code from another device to link it:"))
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("word-word-word")
        self.code_input.setStyleSheet("font-size: 12pt; padding: 8px;")
        enter_layout.addWidget(self.code_input)
        
        accept_btn = QPushButton("✅ Accept Pairing")
        accept_btn.setStyleSheet("background: #3498db; color: white; padding: 10px;")
        accept_btn.clicked.connect(self.accept_pairing)
        enter_layout.addWidget(accept_btn)
        
        enter_group.setLayout(enter_layout)
        layout.addWidget(enter_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def generate_code(self):
        """Generate a new pairing code"""
        device_name = self.device_name_input.text().strip()
        
        if not device_name:
            QMessageBox.warning(self, "Input Required", "Please enter a device name.")
            return
        
        try:
            expiry_seconds = self.expiry_input.value() * 60
            code, device_info = self.device_linker.create_pairing_request(
                device_name=device_name,
                user_id=self.user_id,
                expiry_seconds=expiry_seconds
            )
            
            self.current_pairing_code = code
            
            # Display code
            expiry_time = datetime.fromtimestamp(device_info['expiry']).strftime('%H:%M:%S')
            display_text = f"{code}\n\nExpires at: {expiry_time}"
            self.code_display.setText(display_text)
            
            # Generate and display QR code
            
            QMessageBox.information(
                self,
                "Code Generated",
                f"Pairing code: {code}\n\n"
                f"Share this code with your other device.\n"
                f"Valid for {self.expiry_input.value()} minutes."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate code: {e}")
    
    def show_qr_code(self, data: str):
        """Display QR code"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert PIL image to QPixmap
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            
            # Scale to fit
            scaled = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_label.setPixmap(scaled)
            
        except Exception as e:
            self.qr_label.setText(f"QR generation failed: {e}")
    
    def accept_pairing(self):
        """Accept a pairing code from another device"""
        code = self.code_input.text().strip().lower()
        
        if not code:
            QMessageBox.warning(self, "Input Required", "Please enter a pairing code.")
            return
        
        if not validate_pairing_code(code):
            QMessageBox.warning(self, "Invalid Format", "Code must be in format: word-word-word")
            return
        
        try:
            success = self.device_linker.accept_pairing(code, self.user_id)
            
            if success:
                QMessageBox.information(
                    self,
                    "Device Linked",
                    f"Device successfully linked!\n\n"
                    f"The new device is now synchronized with your account."
                )
                self.code_input.clear()
                self.refresh_devices()
            
        except ValueError as e:
            QMessageBox.warning(self, "Pairing Failed", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to accept pairing: {e}")
    
    def refresh_devices(self):
        """Refresh the list of linked devices"""
        self.device_list.clear()
        
        try:
            devices = self.device_linker.get_linked_devices(self.user_id)
            
            if not devices:
                item = QListWidgetItem("No linked devices")
                item.setFlags(Qt.NoItemFlags)
                self.device_list.addItem(item)
                return
            
            for device in devices:
                # Format last active time
                try:
                    last_active = datetime.fromisoformat(device['last_active'])
                    time_str = last_active.strftime('%Y-%m-%d %H:%M')
                except:
                    time_str = "Unknown"
                
                # Create item text
                trust_emoji = "🟢" if device['trust_level'] >= 2 else "🟡"
                item_text = (
                    f"{trust_emoji} {device['name']}\n"
                    f"   ID: {device['device_id']}\n"
                    f"   Last Active: {time_str}"
                )
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, device['device_id'])
                self.device_list.addItem(item)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load devices: {e}")
    
    def rename_device(self):
        """Rename selected device"""
        current = self.device_list.currentItem()
        if not current or not current.data(Qt.UserRole):
            QMessageBox.warning(self, "No Selection", "Please select a device to rename.")
            return
        
        device_id = current.data(Qt.UserRole)
        
        from PyQt5.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Device",
            "Enter new device name:",
            QLineEdit.Normal
        )
        
        if ok and new_name:
            try:
                self.device_linker.rename_device(device_id, new_name)
                QMessageBox.information(self, "Success", "Device renamed successfully.")
                self.refresh_devices()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename device: {e}")
    
    def revoke_device(self):
        """Revoke access for selected device"""
        current = self.device_list.currentItem()
        if not current or not current.data(Qt.UserRole):
            QMessageBox.warning(self, "No Selection", "Please select a device to revoke.")
            return
        
        device_id = current.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Confirm Revoke",
            "Are you sure you want to revoke access for this device?\n\n"
            "The device will no longer sync with your account.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.device_linker.revoke_device(device_id)
                QMessageBox.information(self, "Success", "Device access revoked.")
                self.refresh_devices()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to revoke device: {e}")
    
    def cleanup_expired_codes(self):
        """Clean up expired pairing codes"""
        try:
            self.device_linker.cleanup_expired_codes()
        except Exception as e:
            print(f"Error cleaning up codes: {e}")
    
    def closeEvent(self, event):
        """Clean up when dialog closes"""
        self.cleanup_timer.stop()
        self.device_linker.close()
        event.accept()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = DeviceManagerDialog(user_id="test_user_123")
    dialog.show()
    sys.exit(app.exec_())
