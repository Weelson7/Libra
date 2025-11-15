# Libra GUI Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies

```powershell
cd c:\Users\weel-\Desktop\Weel_toolkit\Libra
pip install -r requirements.txt
```

### Step 2: Run the GUI

```powershell
python gui/main_ui.py
```

### Step 3: First-Time Setup

When the GUI launches:

1. **Check Tor Status** (bottom-right):
   - Should show "Tor: Connected" in green
   - If not, go to **Connections → Start Tor Service**

2. **Add Your First Peer**:
   - Click **"+ Add Peer"** button
   - Choose a connection method:
     - **Manual Entry**: Enter peer ID or onion address
     - **QR Code**: Paste peer's QR code data
     - **Alias Discovery**: Search by three-word phrase
     - **LAN Discovery**: Find peers on local network

### Step 4: Start Messaging

1. Select peer from left panel
2. Type message in bottom text box
3. Press **Enter** or click **Send**
4. Attach files with **📎** button or drag-drop

## 💡 Key Features at a Glance

### Connection Indicators

- **● Green**: Peer is online
- **○ Gray**: Peer is offline
- **[Direct]** (blue): Connected via direct P2P
- **[Tor]** (orange): Connected via Tor
- **[None]** (gray): Not connected

### Message Status Icons

- **🕒**: Message pending (queued for delivery)
- **✓**: Message sent to peer
- **✓✓**: Message delivered and confirmed

### Quick Actions

| Action | Shortcut |
|--------|----------|
| Send message | Enter |
| Attach file | Ctrl+A or 📎 button |
| Search peers | Click search box |
| Add peer | + Add Peer button |
| Connection manager | Connections menu |
| Settings | Settings → Preferences |

## 📋 Common Tasks

### How to Send a Message to Offline Peer

1. Select peer (even if showing "Offline")
2. Type and send message normally
3. Message shows 🕒 (pending) status
4. When peer comes online, message auto-sends
5. Status updates to ✓ then ✓✓

### How to Send a File

**Method 1**: Drag & Drop
- Drag file from Explorer into chat window
- File queues for transfer
- Progress bar shows status

**Method 2**: Attach Button
- Click 📎 button
- Select file from dialog
- Confirm to send

### How to Connect via Tor

1. Ensure Tor status shows "Connected"
2. Go to **Settings → Preferences**
3. Select "Tor Only" connection mode
4. All connections now use Tor

### How to Rotate Onion Address

**Manual**:
- Go to **Connections → Rotate Onion Address**
- Confirm rotation
- New address shown in notification

**Automatic**:
- Go to **Settings → Preferences**
- Check "Auto-rotate Onion Address"
- Set interval (e.g., 24 hours)
- Click Save

### How to Add Peer via QR Code

1. Get peer's QR code (they go to **Connections → My QR Code**)
2. Click **+ Add Peer**
3. Go to **QR Code** tab
4. Paste QR data in text box
5. Click "Add from QR Data"

### How to Find Peer by Alias

1. Click **+ Add Peer**
2. Go to **Alias Discovery** tab
3. Enter three-word alias (e.g., "happy-dolphin-sky")
4. Click **Search**
5. Select peer from results
6. Click "Add Selected Peer"

### How to Export Chat History

1. Select peer from list
2. Go to **File → Export Chat History**
3. Choose save location
4. Click Save
5. Chat exported as text file

## ⚙️ Configuration

### Settings Dialog (Settings → Preferences)

**Connection Preferences**:
- **Auto (Prefer Direct)**: Try P2P first, fallback to Tor
- **Tor Only**: All connections via Tor (most anonymous)
- **Direct P2P Only**: Only direct connections (fastest)

**Tor Settings**:
- **Tor Control Port**: Default 9051 (change if needed)
- **Auto-rotate Onion Address**: Enable/disable
- **Rotation Interval**: 1-168 hours

**Checkboxes**:
- ☑ Enable Tor Integration
- ☑ Enable Direct P2P (when possible)

## 🔍 Troubleshooting Quick Fixes

### Problem: Tor Won't Connect

**Fix**:
```powershell
# Check if Tor is running
Get-Process tor

# If not, start manually
cd utils/tor-expert-bundle-windows-x86_64-15.0.1/tor
.\tor.exe
```

### Problem: Messages Stuck at 🕒

**Fix**:
- Verify peer shows green ● (online)
- Check connection badge shows [Tor] or [Direct]
- Try reconnecting via Connection Manager
- Restart GUI to reload pending messages

### Problem: File Transfer Fails

**Fix**:
- Ensure peer is online (green ●)
- Check `data/files/` directory exists
- Try smaller file first (< 10MB)
- Check disk space available

### Problem: Can't Find Peer by Alias

**Fix**:
- Verify alias spelling (three words with hyphens)
- Check peer has published their alias
- Try manual connection with peer ID instead
- Use LAN discovery if on same network

## 🎯 Testing Checklist

Test these scenarios to verify GUI works:

- [ ] Start GUI and see main window
- [ ] Check Tor status in status bar
- [ ] Add a peer manually
- [ ] Send a message to online peer
- [ ] Send a message to offline peer (check 🕒 status)
- [ ] Attach and send a file
- [ ] See file transfer progress bar
- [ ] Open Connection Manager dialog
- [ ] View peer details
- [ ] Change peer nickname
- [ ] Open Settings and change connection mode
- [ ] View "My QR Code"
- [ ] Export chat history
- [ ] Minimize to system tray
- [ ] Receive notification for new message
- [ ] Close and reopen GUI (pending messages reload)

## 📚 Additional Resources

- **Full Feature Documentation**: `gui/GUI_FEATURES.md`
- **Backend API**: See `peer/connection_manager.py`
- **Database Schema**: `db/schema.sql`
- **Tor Setup**: `utils/tor-expert-bundle-windows-x86_64-15.0.1/`
- **Logs**: Check `logs/` directory for errors

## 💬 Quick Tips

1. **Keep Tor Running**: Tor status should always show "Connected" for best experience
2. **Use Nicknames**: Assign friendly names to peers for easy identification
3. **Monitor Status Icons**: Watch for 🕒 → ✓ → ✓✓ progression
4. **Enable Notifications**: Don't miss messages while minimized
5. **Regular Backups**: Export chat histories periodically
6. **Verify Identities**: Check key fingerprints in peer details

## 🎉 You're Ready!

The GUI is now fully functional with all features:
- ✅ Tor connections with status monitoring
- ✅ P2P direct connections with fallback
- ✅ Message persistence and offline queue
- ✅ File transfer with progress tracking
- ✅ Onion address rotation
- ✅ Alias-based peer discovery
- ✅ Advanced connection management

**Happy messaging! 🚀**

---

For detailed feature documentation, see `gui/GUI_FEATURES.md`
