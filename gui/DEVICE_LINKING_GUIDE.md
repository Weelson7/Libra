# Device Linking & Multi-Device Support Guide

## Overview

Libra now supports **multi-device synchronization**, allowing you to link multiple devices (phones, laptops, tablets) to the same account. All devices stay synchronized for messages, files, and peer connections.

## Features

✅ **Pairing Code System** - Simple 3-word codes for device linking  
✅ **QR Code Support** - Scan QR codes for instant pairing  
✅ **Device Trust Levels** - Control which devices have access  
✅ **Automatic Expiry** - Pairing codes expire after 5 minutes for security  
✅ **Device Management** - Rename, revoke, and monitor all linked devices  
✅ **Activity Tracking** - See when each device was last active  

---

## How to Link Devices

### Method 1: Using Pairing Codes

**On Device A (Generate Code):**
1. Open Libra and go to **Settings → Manage Devices**
2. Click on **"Add New Device"** tab
3. Enter a name for the device you're linking (e.g., "My Phone")
4. Set expiry time (default: 5 minutes)
5. Click **"🔑 Generate Pairing Code"**
6. You'll see a 3-word code like: `happy-jump-tree`

**On Device B (Accept Code):**
1. Open Libra and go to **Settings → Manage Devices**
2. Click on **"Add New Device"** tab
3. Scroll to **"Enter Pairing Code"** section
4. Type the 3-word code from Device A
5. Click **"✅ Accept Pairing"**
6. ✓ Devices are now linked!

### Method 2: Using QR Codes

**On Device A:**
1. Generate a pairing code (steps above)
2. A QR code will automatically appear below the code
3. Keep the QR code visible on your screen

**On Device B:**
1. Use a QR scanner app or camera to scan the code
2. The QR contains the pairing code and device info
3. Enter the scanned code in Libra's "Enter Pairing Code" field
4. ✓ Pairing complete!

---

## Managing Your Devices

### View Linked Devices

1. Go to **Settings → Manage Devices**
2. Click **"Linked Devices"** tab
3. See all devices with:
   - Device name
   - Device ID
   - Last active time
   - Trust level indicator (🟢/🟡)

### Rename a Device

1. Select the device in the list
2. Click **"✏️ Rename"**
3. Enter new name
4. Click OK

### Revoke Device Access

1. Select the device to remove
2. Click **"🗑️ Revoke Access"**
3. Confirm the action
4. Device will no longer sync with your account

### Refresh Device List

Click **"🔄 Refresh"** to update the device list with latest activity.

---

## Technical Details

### Pairing Code Format

- **Format:** `word-word-word` (3 words separated by hyphens)
- **Example:** `happy-jump-tree`
- **Security:** Codes expire after 5 minutes (configurable)
- **Validation:** Only valid words from dictionary are used

### Device Trust Levels

| Level | Indicator | Description |
|-------|-----------|-------------|
| 1 | 🟡 | Limited access - pending verification |
| 2 | 🟢 | Standard access - newly paired devices |
| 3 | 🟢 | Full access - verified trusted devices |

### QR Code Structure

QR codes contain JSON data:
```json
{
  "type": "libra_device_pairing",
  "code": "word-word-word",
  "device_id": "abc123...",
  "public_key": "-----BEGIN PUBLIC KEY-----...",
  "expiry": 1234567890
}
```

### Database Storage

Devices are stored in the `devices` table:
- `device_id` (Primary Key)
- `user_id` (Links devices to same user)
- `device_key` (RSA public key for encryption)
- `trust_level` (1-3)
- `name` (User-friendly name)
- `last_active` (ISO timestamp)

---

## Security Considerations

🔒 **Time-Limited Codes** - Pairing codes expire quickly to prevent unauthorized access  
🔒 **Device Revocation** - Instantly remove compromised devices  
🔒 **Trust Levels** - Control access granularity per device  
🔒 **Activity Monitoring** - Track when devices were last active  
🔒 **Public Key Exchange** - Each device has unique RSA keypair  

### Best Practices

1. **Use short expiry times** for pairing codes (1-5 minutes)
2. **Revoke immediately** if a device is lost or stolen
3. **Monitor device activity** regularly
4. **Use descriptive names** for easy identification
5. **Only pair in secure locations** (avoid public WiFi)

---

## Troubleshooting

### "Pairing code expired"
- Codes expire after 5 minutes
- Generate a new code and try again

### "Invalid pairing code format"
- Ensure format is: `word-word-word`
- Check for typos or extra spaces

### "Device already linked"
- This device is already paired
- Check the Linked Devices list

### "User ID mismatch"
- Codes only work for the same user account
- Ensure both devices use the same user_id

### QR Code not scanning
- Ensure good lighting
- Try entering the code manually
- Check camera permissions

---

## API Reference

### DeviceLinking Class

```python
from utils.device_linking import DeviceLinking

dl = DeviceLinking()

# Generate pairing code
code, info = dl.create_pairing_request(
    device_name="My Phone",
    user_id="user123",
    expiry_seconds=300  # 5 minutes
)

# Accept pairing
success = dl.accept_pairing(code, user_id="user123")

# Get linked devices
devices = dl.get_linked_devices(user_id="user123")

# Revoke device
dl.revoke_device(device_id="abc123...")

# Rename device
dl.rename_device(device_id="abc123...", new_name="Work Phone")

# Generate QR code data
qr_data = dl.generate_qr_data(code)

# Parse QR code
parsed = dl.parse_qr_data(qr_data)

# Cleanup expired codes
dl.cleanup_expired_codes()
```

---

## GUI Integration

### Menu Location
**Settings → 🔗 Manage Devices**

### Dialog Components

1. **Linked Devices Tab**
   - Device list with status indicators
   - Refresh, Rename, Revoke buttons

2. **Add New Device Tab**
   - Pairing code generation
   - QR code display
   - Code input and acceptance

### Status Indicators

- 🟢 Green dot = Device is trusted (level 2-3)
- 🟡 Yellow dot = Device has limited access (level 1)
- Last active timestamp shows device activity

---

## Configuration

### Environment Variables

```bash
# Set custom user ID (default: "default_user")
export LIBRA_USER_ID="myuser123"

# Use custom data directory
export LIBRA_DATA_DIR="/path/to/data"
```

### Code Configuration

In `config.py`:
```python
# User identification for multi-device support
USER_ID = os.getenv("LIBRA_USER_ID", "default_user")
```

In `utils/device_linking.py`:
```python
# Adjust default expiry time
expiry_seconds = 300  # 5 minutes (default)
```

---

## Future Enhancements

🔮 **Planned Features:**
- Automatic device discovery on local network
- Push notifications for pairing requests
- Device-to-device message synchronization
- Conflict resolution for simultaneous edits
- Biometric authentication for pairing
- Device groups and hierarchies

---

## Support

For issues or questions:
1. Check this guide first
2. Review the test files: `tests/test_device_linking.py`
3. Check logs in `logs/` directory
4. Open an issue on GitHub

---

**Last Updated:** 2025-01-XX  
**Version:** 2.0  
**Module:** `gui/device_manager_dialog.py`, `utils/device_linking.py`
