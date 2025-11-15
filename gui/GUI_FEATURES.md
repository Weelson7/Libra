# Libra v2.0 GUI - Complete Feature Documentation

## Overview

The Libra GUI has been **completely refactored** to expose all backend capabilities with a modern, intuitive interface. All requested features are now fully integrated.

## 🎯 Key Features Implemented

### 1. **Tor Connection Support** ✅
- **Real-time Tor Status**: Status bar shows live Tor connection state (Connected/Disconnected/Error)
- **Tor Control**: Start/stop Tor service from Connections menu
- **Connection Indicators**: Each peer shows whether connected via Tor (orange [Tor] badge)
- **Onion Address Display**: View and manage onion addresses for Tor connections
- **Tor-only Mode**: Settings allow forcing all connections through Tor

### 2. **P2P Direct Connections** ✅
- **Automatic Fallback**: Attempts direct P2P first, falls back to Tor if unavailable
- **Connection Type Indicators**: Peers show [Direct] (blue) or [Tor] (orange) badges
- **Hybrid Mode**: Settings support Auto (prefer direct), Tor Only, or Direct Only modes
- **NAT Traversal**: Backend handles NAT info exchange for direct connections
- **Real-time Switching**: Connections automatically upgrade/downgrade based on availability

### 3. **Message Persistence & Retry** ✅
- **Offline Queue**: Messages sent while peer is offline are queued in database
- **Automatic Retry**: Background thread monitors pending messages and retries when peer comes online
- **Delivery Status Tracking**: 
  - 🕒 **Pending**: Message queued, waiting for peer
  - ✓ **Sent**: Message delivered to peer's socket
  - ✓✓ **Delivered**: Peer confirmed receipt (CRDT sync)
- **Logoff/Login Support**: All pending messages are loaded from database on startup
- **Visual Feedback**: Each message shows delivery status in chat bubble

### 4. **File Transfer Support** ✅
- **Drag & Drop**: Drop files directly into chat window to send
- **Attach Button**: 📎 button for selecting files to send
- **Progress Tracking**: Real-time progress bar shows transfer status
- **File Metadata**: Stored in database with SHA-256 hash, size, timestamp
- **Chunked Transfer**: Large files split into chunks for reliable transmission
- **File Storage**: Files saved to `data/files/` with hash-based naming
- **File Queuing**: Files queued when peer offline, sent when they reconnect

### 5. **Onion Address Rotation** ✅
- **Manual Rotation**: "Rotate Onion Address" option in Connections menu
- **Auto-Rotation**: Settings allow scheduling rotation (1-168 hours)
- **Seamless Reconnection**: Rotation doesn't break existing peer connections
- **Notification**: Users notified when rotation occurs with new address
- **Rotation Timer**: Background timer handles automatic rotation at intervals

### 6. **Enhanced Peer Management** ✅
- **Multiple Discovery Methods**:
  - Manual entry (IP:PORT or onion address)
  - QR code scanning (JSON-based peer info)
  - Alias discovery (three-word phrase lookup)
  - LAN discovery (UDP beacon-based)
- **Peer Status**: Real-time online/offline status with colored indicators (● green/gray)
- **Last Seen**: Timestamps show "Just now", "5m ago", "Yesterday", etc.
- **Unread Count**: Red badges show unread message count per peer
- **Search/Filter**: Search bar to filter peer list by nickname
- **Peer Details**: View full peer info (ID, key fingerprint, addresses, last seen)

### 7. **Alias System Integration** ✅
- **Alias Manager**: Separate dialog for managing published aliases
- **Three-Word Phrases**: User-friendly identifiers (e.g., "happy-dolphin-sky")
- **Alias Publishing**: Publish your alias to registry for discovery
- **Alias Search**: Find peers by searching for their alias
- **Alias Revocation**: Unpublish aliases when no longer needed
- **Auto-Generation**: Option to auto-generate memorable aliases

### 8. **Connection Management UI** ✅
- **Connection Manager Dialog**: Dedicated dialog for peer connections
- **Connection Status Overview**: Shows Tor status, P2P status, total peers
- **Context Menu Actions**:
  - View Details
  - Change Nickname
  - Connect/Disconnect
  - Remove Peer
- **Real-time Updates**: Connection status updates live as peers connect/disconnect

### 9. **Settings & Preferences** ✅
- **Connection Mode**: Choose Auto (Prefer Direct), Tor Only, or Direct P2P Only
- **Tor Settings**: Configure control port (default 9051)
- **Auto-Rotation**: Enable/disable with configurable interval (1-168 hours)
- **Enable/Disable Features**: Toggle Tor integration and P2P separately
- **Persistent Settings**: Settings saved and applied across sessions

### 10. **System Integration** ✅
- **System Tray**: Minimize to tray, quick show/quit actions
- **Notifications**: Desktop notifications for new messages and events
- **Menu Bar**: Full menu system for File, Connections, Settings, Help
- **Export Chat**: Export conversation history to text file
- **Keyboard Shortcuts**: Enter to send message, standard hotkeys

## 📁 File Structure

```
gui/
├── main_ui.py           # Main application window (refactored)
│   ├── LibraMainWindow: Main window class
│   ├── PeerItemWidget: Enhanced peer list item with status
│   ├── MessageBackendThread: Background processing thread
│   ├── SettingsDialog: Settings configuration dialog
│   └── All message/file handling logic
│
└── connection_view.py   # Connection management (refactored)
    ├── ConnectionView: Main connection dialog
    ├── AddPeerDialog: Multiple connection methods
    ├── PeerDetailWidget: Detailed peer information
    └── AliasManagerDialog: Alias publishing/discovery
```

## 🚀 Running the GUI

### Basic Startup

```powershell
# From project root
python gui/main_ui.py
```

### With Tor Already Running

```powershell
# Start Tor first (if not auto-starting)
# Then run GUI
python gui/main_ui.py
```

### First-Time Setup

1. **Start Application**: `python gui/main_ui.py`
2. **Tor Initialization**: 
   - GUI attempts to start Tor automatically
   - Check status bar: "Tor: Connected" (green)
   - If fails, go to Connections → Start Tor Service
3. **Add Peers**:
   - Click "+ Add Peer" button
   - Choose discovery method (manual, QR, alias, LAN)
   - Enter peer information
4. **Start Messaging**:
   - Select peer from list
   - Type message and press Enter
   - Attach files with 📎 button or drag-drop

## 💬 Usage Scenarios

### Scenario 1: Sending Messages While Peer is Offline

1. Select peer from list (shows "Offline")
2. Type message and send
3. Message appears with 🕒 (pending) status
4. Message saved to database
5. When peer comes online:
   - Background thread detects online status
   - Automatically retries sending pending messages
   - Status updates to ✓ (sent) then ✓✓ (delivered)

### Scenario 2: Peer Logoff then Login

1. **Before Logoff**:
   - Peer A sends messages to offline Peer B
   - Messages queued in A's database as pending
2. **After B Logs In**:
   - B's app loads all peers and pending messages from database
   - B connects to A via Tor/P2P
   - A's background thread detects B is online
   - A automatically sends all pending messages to B
   - B processes messages and syncs via CRDT
   - Both sides show ✓✓ (delivered) status

### Scenario 3: File Transfer

1. **Sending**:
   - Drag file into chat window OR click 📎 button
   - File saved to `data/files/` with hash
   - Metadata stored in database
   - Progress bar shows transfer status
   - Message shows "📎 Sending file: filename.txt"
2. **Receiving** (when peer online):
   - Chunks transmitted via connection
   - Progress tracked in real-time
   - File reassembled on recipient side
   - Notification shown on completion

### Scenario 4: Onion Address Rotation

1. **Manual Rotation**:
   - Go to Connections → Rotate Onion Address
   - New ephemeral onion service created
   - Notification shows new address
   - All connected peers notified of new address
   - Connections seamlessly transition to new address
2. **Automatic Rotation**:
   - Go to Settings → Preferences
   - Check "Auto-rotate Onion Address"
   - Set interval (e.g., 24 hours)
   - Timer runs in background
   - Rotation happens automatically at interval

### Scenario 5: Connecting via Different Methods

**Auto Mode (Default)**:
- Attempts direct P2P first (fast, low latency)
- If NAT traversal fails, falls back to Tor
- Connection badge shows [Direct] or [Tor]

**Tor Only Mode**:
- All connections forced through Tor
- Enhanced anonymity
- Slightly higher latency

**Direct P2P Only Mode**:
- Only allows direct connections
- Fastest performance
- Only works on same network or with port forwarding

## 🎨 UI Components Explained

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ File  Connections  Settings  Help                    Tor: ● Connected │
├──────────────┬──────────────────────────────────────────────────┤
│              │ Alice • Online • Direct                          │
│ Search...    ├──────────────────────────────────────────────────┤
│ ───────────  │                                                   │
│              │  [Alice] Hi there!                    10:30 ✓✓  │
│ ● Alice      │  [You] Hello! How are you?            10:31 ✓✓  │
│   [Direct]   │  [Alice] Great, thanks!               10:32 ✓✓  │
│   5m ago  2  │                                                   │
│              │                                                   │
│ ● Bob        │                                                   │
│   [Tor]      │                                                   │
│   1h ago     │ ─────────────────────────────────────────────── │
│              │ [Progress: ███████░░░ 70%]                       │
│ ○ Charlie    │                                                   │
│   [None]     │ Type your message here...          📎  [Send]   │
│   Yesterday  │                                                   │
│              │                                                   │
│ + Add Peer   │                                                   │
└──────────────┴──────────────────────────────────────────────────┘
                Peers: 2 online / 3 total
```

### Connection Manager Dialog

```
┌─────────────────────────────────────────────────────────┐
│ Connection Manager                                    × │
├─────────────────────────────────────────────────────────┤
│ Connection Status                                       │
│ Total peers: 3                                          │
│ Tor: Connected                                          │
│ P2P: Enabled                                            │
├─────────────────────────────────────────────────────────┤
│ Connected Peers                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Alice - Online (Direct)                             │ │
│ │ Bob - Online (Tor)                                  │ │
│ │ Charlie - Offline (None)                            │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [Add Peer] [My QR Code] [Refresh]                      │
│                                                         │
│                                       [Close]           │
└─────────────────────────────────────────────────────────┘
```

### Add Peer Dialog (Tabbed)

```
┌─────────────────────────────────────────────────────────┐
│ Add New Peer                                          × │
├─────────────────────────────────────────────────────────┤
│ [Manual Entry] [QR Code] [Alias Discovery] [LAN Discovery] │
├─────────────────────────────────────────────────────────┤
│ Manual Entry Tab:                                       │
│                                                         │
│ Peer ID: [abc123.onion                           ]     │
│ Nickname: [Alice                                 ]     │
│ IP Address: [192.168.1.100:12345                ]     │
│ Connection Type: [Auto ▼]                              │
│                                                         │
│                                        [Add Peer]       │
├─────────────────────────────────────────────────────────┤
│ Alias Discovery Tab:                                    │
│                                                         │
│ Search for peer by alias:                              │
│ [happy-dolphin-sky                         ] [Search]  │
│                                                         │
│ Search Results:                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ happy-dolphin-sky - peer_abc123...                  │ │
│ │ brave-tiger-moon - peer_def456...                   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│                                [Add Selected Peer]      │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Technical Implementation

### Backend Thread Architecture

The `MessageBackendThread` runs continuously and handles:

1. **Pending Message Retry**:
   - Queries database for messages with `sync_status=0` (pending)
   - For each pending message, checks if peer is in `active_connections`
   - If online, attempts to send via socket
   - Updates status to `1` (sent) on success

2. **Connection Monitoring**:
   - Sends heartbeat packets to all connected peers
   - Detects disconnections and emits `peer_status_changed` signal
   - Updates GUI peer list with current status

3. **Tor Status Checking**:
   - Polls Tor controller for connection status
   - Emits `tor_status_updated` signal to update GUI

4. **Message Reception**:
   - Processes incoming messages from sockets
   - Emits `message_received` signal with message data
   - GUI updates chat display and shows notifications

### Database Schema Integration

The GUI fully integrates with the existing database schema:

**Messages Table**:
```sql
- message_id: Unique identifier
- peer_id: Recipient/sender peer ID
- content: Encrypted message content (BLOB)
- timestamp: Unix timestamp
- sync_status: 0=pending, 1=sent, 2=delivered
```

**Files Table**:
```sql
- file_name: Original filename
- file_path: Storage path
- file_hash: SHA-256 hash
- file_size: Bytes
- peer_id: Associated peer
- message_id: Associated message (if any)
- timestamp: Unix timestamp
```

**Peers Table**:
```sql
- peer_id: Unique peer identifier
- public_key: RSA public key (BLOB)
- nickname: User-assigned name
- last_seen: Unix timestamp of last connection
```

### Connection Type Detection

The GUI determines connection type by:

1. Checking if socket is using Tor SOCKS proxy (port 9050)
2. Checking if socket is direct TCP connection
3. Querying `ConnectionManager` for connection metadata
4. Displaying appropriate badge color:
   - **Blue [Direct]**: Direct P2P connection
   - **Orange [Tor]**: Tor onion service connection
   - **Gray [None]**: Not connected

### Message Delivery Flow

```
1. User types message and presses Send
   ↓
2. Message saved to database with sync_status=0 (pending)
   ↓
3. Message added to in-memory peer_threads
   ↓
4. GUI displays message with 🕒 status
   ↓
5. Backend thread detects pending message
   ↓
6. If peer online:
   → Send via socket
   → Update sync_status=1 (sent)
   → GUI updates to ✓ status
   ↓
7. Peer sends ACK (CRDT sync)
   ↓
8. Update sync_status=2 (delivered)
   ↓
9. GUI updates to ✓✓ status
```

## 🐛 Troubleshooting

### Issue: Tor Status Shows "Disconnected"

**Solution**:
1. Check if Tor is installed
2. Verify port 9051 is available
3. Go to Connections → Start Tor Service
4. Check logs in `logs/` directory for Tor errors

### Issue: Messages Stuck in Pending (🕒)

**Solution**:
1. Check if peer is online (should show green ● in peer list)
2. Verify connection type badge shows [Tor] or [Direct]
3. Try manually connecting via Connection Manager
4. Check backend thread is running (should see status updates)

### Issue: File Transfer Not Starting

**Solution**:
1. Verify peer is online
2. Check `data/files/` directory has write permissions
3. Ensure file size is within limits
4. Look for progress bar (should appear when transfer starts)

### Issue: Onion Rotation Breaks Connections

**Solution**:
1. This shouldn't happen - rotation is seamless
2. If connections drop, check if peers were notified of new address
3. Try manually reconnecting to peer
4. Check Tor logs for errors

## 🎓 Best Practices

1. **Always Check Tor Status**: Ensure Tor is connected before expecting anonymous connections
2. **Use Auto Mode**: Lets Libra choose best connection type automatically
3. **Set Reasonable Rotation Intervals**: 24-48 hours is good balance between security and stability
4. **Monitor Delivery Status**: Check for 🕒 icons indicating pending messages
5. **Keep Peer List Organized**: Use nicknames and remove inactive peers
6. **Backup Chat History**: Use File → Export Chat History regularly
7. **Verify Peer Identity**: Check key fingerprints in peer details before sharing sensitive info

## 📊 Feature Comparison

| Feature | Old GUI | New GUI |
|---------|---------|---------|
| Tor Status | ❌ Not shown | ✅ Real-time indicator |
| P2P Connections | ❌ Not supported | ✅ Full support |
| Message Persistence | ❌ Lost on restart | ✅ Database-backed |
| Delivery Status | ❌ No tracking | ✅ Pending/Sent/Delivered |
| File Transfer | ❌ Basic only | ✅ Progress + retry |
| Onion Rotation | ❌ Manual only | ✅ Auto + seamless |
| Alias System | ❌ Not integrated | ✅ Full integration |
| Connection Manager | ❌ Basic list | ✅ Advanced management |
| Settings | ❌ Hardcoded | ✅ Configurable |
| Notifications | ❌ None | ✅ System tray |

## 🚀 Future Enhancements (Beyond v2.0)

- Voice/video calling over Tor
- Group messaging with multi-peer CRDT sync
- Encrypted file sharing with expiration
- Mobile app with QR code scanning camera
- Plugin system for extensions
- Theme customization
- Message reactions and threading
- Search across all conversations
- Backup/restore to encrypted archive

## 📝 Summary

The refactored Libra GUI now provides a **complete, production-ready interface** that exposes all backend capabilities:

✅ **Tor connections** with real-time status monitoring
✅ **P2P direct connections** with automatic fallback
✅ **Message persistence** with offline queue and retry
✅ **File transfers** with progress tracking and queuing
✅ **Onion address rotation** without breaking connections
✅ **Alias system** for easy peer discovery
✅ **Advanced connection management** with multiple discovery methods
✅ **Settings & preferences** for full customization
✅ **System integration** with tray and notifications

All requirements have been met and the GUI is ready for testing and deployment!
