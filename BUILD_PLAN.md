# Libra - 15 Phase Build Plan

## Overview
This build plan ensures incremental delivery with working software after each phase. Each phase includes quality gates to verify functionality before proceeding.

---

## **PHASE 1: Project Foundation & Configuration**

### Objectives
- Set up project structure
- Initialize configuration system
- Create basic logging framework

### Deliverables
- Complete directory structure
- `config.py` with environment variables
- `requirements.txt` with initial dependencies
- Basic logging utility
- README.md with setup instructions

### Implementation Tasks
1. Create all project directories
2. Implement `config.py` with:
   - Default port settings
   - Database path configuration
   - Encryption key management
   - Debug/production modes
3. Create `requirements.txt` with pinned versions
4. Add logging utility in `utils/logger.py`
5. Create virtual environment setup script

### Quality Gates
- [ ] All directories created successfully
- [ ] `config.py` loads without errors
- [ ] Virtual environment activates correctly
- [ ] All dependencies install without conflicts
- [ ] Logging writes to file and console
- [ ] Configuration values accessible from other modules

### Testing Checklist
- Run `python -c "import config; print(config.DB_PATH)"`
- Verify log file creation
- Check all imports resolve

---

## **PHASE 2: Database Schema & Basic Operations**

### Objectives
- Implement SQLite database initialization
- Create schema for messages and peers
- Build CRUD operations for local storage

### Deliverables
- `db/schema.sql` with complete table definitions
- `db/db_handler.py` with database connection management
- Basic message and peer storage/retrieval functions

### Implementation Tasks
1. Design schema:
   - `messages` table (id, peer_id, content, timestamp, message_id, sync_status)
   - `peers` table (peer_id, nickname, public_key, last_seen, fingerprint)
   - `sync_state` table (peer_id, last_sync_timestamp, vector_clock)
   - `devices` table (device_id, user_id, device_key, trust_level)
2. Implement `DBHandler` class:
   - Connection pooling
   - Auto-initialization on first run
   - Transaction management
3. Create methods:
   - `insert_message()`
   - `get_messages_by_peer()`
   - `add_peer()`
   - `update_peer_status()`
   - `get_all_peers()`

### Quality Gates
- [ ] Database file created automatically on first run
- [ ] All tables created with correct schema
- [ ] Can insert and retrieve messages
- [ ] Can add and update peer information
- [ ] Transactions rollback on error
- [ ] No SQL injection vulnerabilities
- [ ] Database locks handled gracefully

### Testing Checklist
- Insert 100 test messages and retrieve them
- Test concurrent database access
- Verify foreign key constraints
- Test database migration on schema changes
- Benchmark query performance (< 10ms for simple queries)

---

## **PHASE 3: Cryptography Foundation**

### Objectives
- Implement end-to-end encryption utilities
- Generate and manage peer identities
- Create secure key storage

### Deliverables
- `utils/crypto_utils.py` with encryption/decryption functions
- Peer identity generation (public/private key pairs)
- Message signing and verification
- Secure key storage with password protection

### Implementation Tasks
1. Implement using `cryptography` library:
   - RSA key pair generation (2048-bit minimum)
   - AES-256 encryption for messages
   - HMAC for message integrity
   - Key derivation (PBKDF2 or Argon2)
2. Create identity management:
   - Generate unique peer ID
   - Store private keys encrypted
   - Export/import key functions
3. Implement message encryption:
   - Hybrid encryption (RSA + AES)
   - Sign all outgoing messages
   - Verify incoming message signatures

### Quality Gates
- [ ] Key generation completes in < 2 seconds
- [ ] Encrypted messages cannot be decrypted without key
- [ ] Signature verification detects tampering
- [ ] Private keys stored encrypted at rest
- [ ] No plaintext secrets in memory dumps
- [ ] Keys can be exported/imported securely
- [ ] Forward secrecy considerations documented

### Testing Checklist
- Generate 10 key pairs and verify uniqueness
- Encrypt/decrypt 1000 messages successfully
- Attempt to decrypt with wrong key (should fail)
- Modify encrypted message and verify signature fails
- Test key backup and restore process
- Performance test: encrypt 1MB file in < 100ms

---

## **PHASE 4: Basic CLI Interface**

### Objectives
- Create minimal command-line interface
- Enable basic message sending/receiving (local only)
- Test database and crypto integration

### Deliverables
- `main.py` with CLI argument parsing
- Commands: init, send-local, read-local
- Integration of database and crypto modules

### Implementation Tasks
1. Implement CLI using `argparse`:
   - `libra init` - Initialize local database and identity
   - `libra send-local <message>` - Store encrypted message locally
   - `libra read-local` - Decrypt and display stored messages
   - `libra identity` - Show peer ID and public key
2. Wire up database and crypto modules
3. Add error handling and user feedback

### Quality Gates
- [ ] CLI commands execute without crashes
- [ ] Messages stored encrypted in database
- [ ] Messages decrypted correctly on read
- [ ] User identity persists between sessions
- [ ] Helpful error messages on invalid input
- [ ] CLI help text is clear and accurate

### Testing Checklist
- Run complete workflow: init → send → read
- Test with special characters and emoji
- Verify database contains encrypted data (not plaintext)
- Test CLI with invalid arguments
- Check exit codes (0 for success, non-zero for errors)

---

## **PHASE 5: LAN Peer Discovery**

### Objectives
- Implement UDP broadcast for local network discovery
- Detect peers on same network automatically
- Exchange identity information securely

### Deliverables
- `peer/peer_discovery.py` with broadcast/listen functionality
- Automatic peer registration in database
- Discovery protocol with handshake

### Implementation Tasks
1. Implement UDP broadcast:
   - Send beacon on port 37020 (or configurable)
   - Include encrypted peer ID and public key
   - Listen for peer beacons
2. Create discovery protocol:
   - Announce presence every 30 seconds
   - Respond to peer announcements
   - Verify peer signatures
3. Peer registration:
   - Store discovered peers in database
   - Track last seen timestamp
   - Handle peer departure (timeout)

### Quality Gates
- [ ] Peers discovered within 30 seconds on same network
- [ ] Multiple instances can discover each other
- [ ] Malformed broadcasts don't crash listener
- [ ] Peer list updates automatically
- [ ] Discovery works across VLANs (if network allows)
- [ ] No sensitive data leaked in broadcasts
- [ ] Discovery can be disabled/enabled

### Testing Checklist
- Start 3 instances on same network, verify mutual discovery
- Test with firewall rules (should fail gracefully)
- Disconnect peer and verify timeout handling
- Test on Windows and Linux
- Verify broadcast traffic is minimal (< 1KB/min)
- Test network with 50+ devices (scalability)

---

## **PHASE 6: Direct Peer Connection (LAN)**

### Objectives
- Establish TCP connections between discovered peers
- Implement basic message exchange protocol
- Handle connection lifecycle (connect, disconnect, reconnect)

### Deliverables
- `peer/connection_manager.py` with connection pooling
- TCP socket handling with TLS encryption
- Message serialization/deserialization protocol

### Implementation Tasks
1. Implement connection manager:
   - Maintain active peer connections
   - Auto-reconnect on disconnect
   - Connection pool with limits
2. Create message protocol:
   - JSON-based message format
   - Message types: HELLO, MESSAGE, ACK, SYNC_REQUEST
   - Sequence numbers for ordering
3. TLS/SSL for transport:
   - Use self-signed certificates
   - Pin peer certificates to prevent MITM
   - Encrypt all traffic

### Quality Gates
- [ ] Peers connect automatically after discovery
- [ ] Messages transmitted reliably
- [ ] Connections recover from network interruptions
- [ ] No message loss during reconnection
- [ ] Connection limit enforced (prevent DoS)
- [ ] TLS handshake completes successfully
- [ ] Connection state tracked accurately

### Testing Checklist
- Send 1000 messages between two peers (100% delivery)
- Simulate network disconnection and verify reconnect
- Test concurrent connections (10+ peers)
- Monitor resource usage (memory, file descriptors)
- Test message ordering preservation
- Verify encrypted transport with Wireshark

---

## **PHASE 7: Message Synchronization Engine**

### Objectives
- Implement CRDT-based message sync
- Handle conflict resolution for concurrent updates
- Enable delta synchronization (only new messages)

### Deliverables
- `sync/crdt_engine.py` with merge logic
- Vector clock implementation for causality tracking
- Sync state management per peer

### Implementation Tasks
1. Implement vector clocks:
   - Track logical time per peer
   - Detect concurrent vs. causal events
   - Update clocks on message send/receive
2. Create CRDT message structure:
   - Last-Write-Wins (LWW) for simple conflicts
   - Tombstones for deletions
   - Operation-based CRDT for collaborative editing (future)
3. Sync protocol:
   - Request missing messages by vector clock
   - Send only delta (new messages since last sync)
   - Handle out-of-order message arrival

### Quality Gates
- [ ] Concurrent messages from different peers merge correctly
- [ ] No message duplicates after sync
- [ ] Causality violations detected and handled
- [ ] Sync completes with minimal data transfer
- [ ] Deleted messages don't reappear
- [ ] Sync state persists across restarts
- [ ] Conflict resolution is deterministic

### Testing Checklist
- Create fork: Peer A and B both send messages while disconnected, then sync
- Verify identical message history after sync
- Test with 10,000 messages (performance)
- Simulate Byzantine peer sending invalid clocks
- Benchmark sync time for 1000 new messages (< 1 second)
- Test sync recovery from interrupted sync

---

## **PHASE 8: HTTPS Tunnel for NAT Traversal**

### Objectives
- Implement HTTPS tunneling for peers behind NAT
- Support WebRTC for peer-to-peer connections
- Fallback to TURN/STUN relay if direct connection fails

### Deliverables
- `peer/tunnel_handler.py` with WebRTC signaling
- HTTPS tunnel establishment
- Optional TURN server configuration

### Implementation Tasks
1. Implement WebRTC setup:
   - Use `aiortc` library for WebRTC in Python
   - ICE candidate exchange via signaling
   - STUN for NAT type detection
2. HTTPS tunnel as fallback:
   - Use `aiohttp` for persistent connections
   - Tunnel messages through HTTPS POST/GET
   - Implement long-polling or WebSocket upgrade
3. TURN relay integration:
   - Configure public TURN server (or self-hosted)
   - Use when direct connection impossible
   - Encrypt all relayed traffic

### Quality Gates
- [ ] Peers behind NAT can connect
- [ ] WebRTC connection established within 10 seconds
- [ ] Fallback to TURN when direct fails
- [ ] HTTPS tunnel maintains connection stability
- [ ] No packet loss over tunnel
- [ ] Tunnel encryption verified
- [ ] Connection method logged for debugging

### Testing Checklist
- Test between peers on different networks
- Simulate symmetric NAT (hardest case)
- Test with corporate firewalls/proxies
- Verify TURN fallback activates correctly
- Monitor bandwidth usage of relay
- Test connection stability for 24 hours

---

## **PHASE 9: Basic GUI Foundation (PyQt5)**

### Objectives
- Create main window with peer list
- Display message threads per peer
- Basic send/receive UI

### Deliverables
- `ui/main_ui.py` with main application window
- Peer list sidebar
- Message display area with scrolling
- Message input field with send button

### Implementation Tasks
1. Design main window layout:
   - Left sidebar: peer list with status indicators
   - Center: message thread view
   - Bottom: message input field
   - Top: menu bar (File, Settings, Help)
2. Implement peer list:
   - Show nickname, status (online/offline), last seen
   - Click to open message thread
   - Badge for unread message count
3. Message display:
   - Chronological message list
   - Differentiate sent vs. received
   - Show timestamps
   - Auto-scroll to newest

### Quality Gates
- [ ] GUI launches without errors
- [ ] Peer list updates in real-time
- [ ] Messages display correctly
- [ ] Send button posts message to backend
- [ ] GUI responsive (no freezing)
- [ ] Window resizing works properly
- [ ] Cross-platform UI rendering (Windows/Linux)

### Testing Checklist
- Open GUI with 50 peers in list (performance)
- Send 100 messages and verify display
- Test window minimize/maximize/close
- Check UI with high DPI displays
- Test keyboard shortcuts (Enter to send)
- Verify thread safety (UI updates from background threads)

---

## **PHASE 10: Real-time Message Updates in GUI**

### Objectives
- Integrate GUI with backend messaging
- Update UI when messages arrive
- Show peer status changes live

### Deliverables
- Signal/slot mechanism for backend-to-GUI communication
- Live message delivery to open threads
- Peer status indicators
- System tray notifications

### Implementation Tasks
1. Implement Qt signals:
   - `message_received` signal
   - `peer_status_changed` signal
   - `sync_completed` signal
2. Connect backend to UI:
   - Run connection manager in background thread
   - Emit signals on events
   - Update UI components safely
3. Add notifications:
   - Desktop notifications for new messages
   - Sound alerts (optional, configurable)
   - System tray icon with unread count

### Quality Gates
- [ ] Messages appear instantly when received
- [ ] No UI freezing during message processing
- [ ] Peer status accurate (online/offline/typing)
- [ ] Notifications work on Windows/Linux
- [ ] No race conditions in UI updates
- [ ] Memory usage stable during long sessions
- [ ] Notification preferences persist

### Testing Checklist
- Send rapid-fire messages (10/second) and verify UI handles it
- Test with GUI minimized (notifications work)
- Simulate peer going online/offline
- Run overnight stress test (stability)
- Check thread safety with thread sanitizer
- Test notification click action (bring window to front)

---

## **PHASE 11: Connection Management UI**

### Objectives
- Manual peer connection via IP/QR code
- View all connections and sync status
- Peer management (block, remove, nickname)

### Deliverables
- `ui/connection_view.py` with connection dialog
- QR code generation/scanning
- Peer settings dialog

### Implementation Tasks
1. Manual connection dialog:
   - Input field for peer IP:PORT
   - QR code scanner using camera (optional)
   - Connection status feedback
2. Generate QR codes:
   - Encode peer ID, public key, IP
   - Display in settings
   - Copy to clipboard option
3. Peer management:
   - Right-click context menu on peer
   - Block/unblock peer
   - Change nickname
   - View peer details (public key, fingerprint)
   - Remove peer (delete history)

### Quality Gates
- [ ] Manual connection establishes successfully
- [ ] QR code encodes all necessary data
- [ ] QR scanning decodes correctly (if implemented)
- [ ] Peer settings changes persist
- [ ] Blocked peers cannot send messages
- [ ] UI feedback clear and helpful
- [ ] QR code generation < 1 second

### Testing Checklist
- Connect to peer via manual IP entry
- Generate QR code and verify encoding
- Test block functionality (no messages received)
- Change peer nickname and verify in UI
- Remove peer and verify history deleted
- Test invalid IP/QR code handling

---

## **PHASE 12: Offline Message Queue & Auto-Sync**

### Objectives
- Buffer messages when peer offline
- Auto-send when peer reconnects
- Sync status indicators

### Deliverables
- Message queue in database with pending status
- Auto-retry mechanism
- UI indicators for pending/sent/delivered

### Implementation Tasks
1. Message queue system:
   - Mark messages as pending when peer offline
   - Store in `messages` table with sync_status
   - Retry sending on peer reconnection
2. Delivery status:
   - Track: pending → sent → delivered
   - ACK messages from recipient
   - Update UI with status icons
3. Sync recovery:
   - Resume interrupted syncs
   - Handle partial message delivery
   - Request resend for missing messages

### Quality Gates
- [ ] Messages queued when peer offline
- [ ] Queue processed automatically on reconnect
- [ ] No message loss during offline periods
- [ ] Delivery status accurate
- [ ] Queue survives application restart
- [ ] UI shows pending message count
- [ ] Retry logic has exponential backoff

### Testing Checklist
- Send 50 messages while peer offline, verify delivery after reconnect
- Test queue with 1000+ messages (performance)
- Simulate app crash during send (recovery)
- Verify message order preserved in queue
- Test ACK timeout and retry logic
- Monitor queue memory usage

---

## **PHASE 13: File Transfer Support**

### Objectives
- Attach files to messages
- Chunked transfer for large files
- Resume interrupted transfers

### Deliverables
- File attachment UI (drag-drop, file picker)
- Chunked file transfer protocol
- Progress indicators
- File storage and retrieval

### Implementation Tasks
1. File attachment:
   - UI button to attach files
   - Drag-and-drop support
   - File preview for images
   - Size limit warnings
2. Transfer protocol:
   - Split files into 64KB chunks
   - Send chunks with sequence numbers
   - Reassemble on receiver
   - Verify integrity with SHA-256 hash
3. Storage:
   - Store files in `data/files/` directory
   - Reference in database with file metadata
   - Automatic cleanup of orphaned files

### Quality Gates
- [ ] Files up to 100MB transfer successfully
- [ ] Transfer resumes after interruption
- [ ] Progress bar updates smoothly
- [ ] File integrity verified (hash match)
- [ ] Multiple files can transfer concurrently
- [ ] UI remains responsive during transfer
- [ ] Disk space checked before receiving

### Testing Checklist
- Transfer 10MB, 50MB, 100MB files
- Interrupt transfer and verify resume
- Send multiple files simultaneously
- Test with various file types (images, PDFs, videos)
- Verify received files are identical (hash check)
- Test insufficient disk space handling
- Benchmark transfer speed (should saturate bandwidth)

---

## **PHASE 14: Multi-Device Support**

### Objectives
- Link multiple devices to same user identity
- Sync messages across devices
- Device trust management

### Deliverables
- Device linking protocol
- Cross-device message synchronization
- Device management UI
- Device-specific encryption keys

### Implementation Tasks
1. Device linking:
   - Generate pairing QR code on primary device
   - Scan QR on secondary device to link
   - Share user identity securely
   - Generate device-specific keys
2. Multi-device sync:
   - Sync messages to all linked devices
   - Avoid duplicate notifications
   - Track read status per device
   - Sync peer list and settings
3. Device management:
   - List all linked devices in settings
   - Revoke device access
   - Rename devices
   - View last active time per device

### Quality Gates
- [ ] Devices link within 30 seconds
- [ ] Messages appear on all devices
- [ ] No duplicate messages delivered
- [ ] Revoked devices cannot access messages
- [ ] Device sync works across networks
- [ ] Read status synced correctly
- [ ] Device keys stored securely

### Testing Checklist
- Link 3 devices and verify sync
- Send message from device A, verify appears on B and C
- Revoke device and verify access denied
- Test sync with one device offline
- Verify read receipts sync
- Test device re-linking after revocation

---

## **PHASE 15: Polish, Security Audit, & Documentation**

### Objectives
- Comprehensive security review
- Performance optimization
- Complete user documentation
- Installer/packaging

### Deliverables
- Security audit report with mitigations
- Optimized database queries
- User manual and developer docs
- Windows installer, Linux AppImage
- CI/CD pipeline for builds

### Implementation Tasks
1. Security audit:
   - Penetration testing (message tampering, replay attacks)
   - Code review for vulnerabilities
   - Dependency security scan
   - Implement rate limiting
   - Add input validation everywhere
2. Performance optimization:
   - Profile CPU/memory usage
   - Optimize database indexes
   - Reduce message latency
   - Minimize bandwidth usage
3. Documentation:
   - User manual (setup, usage, troubleshooting)
   - Developer docs (architecture, API, contributing)
   - Security best practices guide
4. Packaging:
   - PyInstaller for Windows executable
   - AppImage for Linux
   - Auto-update mechanism
   - Digital signature for installers

### Quality Gates
- [ ] Zero critical security vulnerabilities
- [ ] Message delivery < 100ms on LAN
- [ ] Memory usage < 200MB with 100 peers
- [ ] All user-facing features documented
- [ ] Installers work on fresh systems
- [ ] Auto-update tested successfully
- [ ] Code coverage > 70%

### Testing Checklist
- Full security penetration test
- Performance benchmark suite passes
- Install on clean Windows/Linux VMs
- User acceptance testing with 10 users
- Documentation review by non-developers
- Stress test: 1000 messages, 100 peers, 24 hours
- Verify auto-update from old version

---

## Summary & Timeline

### Estimated Timeline
- **Phases 1-5:** 3-4 weeks (Foundation & Local Features)
- **Phases 6-8:** 3-4 weeks (Networking & Sync)
- **Phases 9-11:** 2-3 weeks (GUI Development)
- **Phases 12-14:** 3-4 weeks (Advanced Features)
- **Phase 15:** 2-3 weeks (Polish & Release)

**Total: ~13-18 weeks** (3-4 months for single developer)

### Critical Success Factors
1. **Working Software After Each Phase:** Every phase produces runnable, testable software
2. **Incremental Testing:** Quality gates prevent technical debt accumulation
3. **Security First:** Encryption and authentication from day one
4. **User Feedback:** Early GUI phases enable user testing
5. **Performance Monitoring:** Track metrics throughout development

### Risk Mitigation
- **NAT Traversal Complexity:** Phase 8 is high-risk; budget extra time
- **CRDT Implementation:** Phase 7 requires careful design; consider using existing libraries
- **Cross-platform Issues:** Test on both Windows/Linux continuously
- **Dependency Management:** Pin versions, audit security regularly

### Post-Launch Roadmap
- Android app (Kivy/Flutter)
- End-to-end encrypted voice/video calls
- Group messaging support
- Message search and archiving
- Backup/restore functionality
- Plugin system for extensions

---

## Appendix: Testing Standards

### Unit Test Requirements
- Minimum 70% code coverage
- All crypto functions 100% covered
- Database operations fully tested
- Mocking for network operations

### Integration Test Requirements
- Full message flow: send → receive → decrypt
- Multi-peer scenarios
- Network interruption recovery
- GUI workflow tests

### Performance Benchmarks
- Message encryption: < 10ms
- Database query: < 10ms
- Message delivery (LAN): < 100ms
- GUI responsiveness: < 16ms frame time (60 FPS)
- Memory usage: < 200MB base, +10MB per peer

### Security Testing
- Penetration testing checklist
- Fuzzing inputs (messages, network packets)
- Timing attack resistance
- Memory dump analysis
- Dependency vulnerability scanning
