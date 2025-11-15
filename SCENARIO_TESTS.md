# Libra Scenario Test Documentation

## Overview

This document describes the comprehensive test suite for the five critical scenarios in Libra's peer-to-peer communication system. These tests validate backend logic for Tor connections, P2P establishment, message persistence, file transfers, and onion rotation.

## Test Suite Structure

### 1. Tor Reconnection Tests (`test_tor_reconnection.py`)

**Purpose**: Validate that peers can connect via Tor and automatically reconnect when a peer goes offline then back online.

**Test Cases**:

#### Unit Tests (TestTorReconnection)
- `test_initial_connection`: Verify initial Tor connection establishes correctly
- `test_peer_goes_offline`: Handle peer going offline during active session
- `test_peer_comes_back_online`: Detect and reconnect when peer returns
- `test_automatic_message_retry`: Retry pending messages with exponential backoff
- `test_connection_status_tracking`: Track connection states (connected, offline, reconnecting)
- `test_pending_message_queue`: Queue messages when peer is offline
- `test_multiple_reconnection_cycles`: Handle multiple offline/online cycles
- `test_partial_message_delivery`: Resume delivery after partial completion

#### Integration Tests (TestTorReconnectionIntegration)
- `test_full_reconnection_workflow`: Complete workflow from connect → offline → reconnect → deliver
- `test_reconnection_with_database_persistence`: Messages persist across app restarts

**Key Features Tested**:
- Exponential backoff retry (max 5 attempts)
- Message status tracking (0=pending, 1=sent, 2=delivered)
- Database persistence of pending messages
- Automatic reconnection on peer availability

---

### 2. P2P Connection Tests (`test_p2p_connection.py`)

**Purpose**: Validate that peers can establish direct P2P connections when conditions are met, with automatic Tor fallback.

**Test Cases**:

#### TestP2PConnection
- `test_successful_p2p_upgrade`: Upgrade from Tor to P2P when conditions met
- `test_p2p_connection_conditions`: Verify P2P requirements (NAT info exchange)
- `test_parallel_connection_attempts`: Attempt Tor and P2P in parallel (7s timeout)
- `test_p2p_health_monitoring`: Monitor connection health with heartbeats
- `test_connection_type_detection`: Detect and track connection type (tor/direct)

#### TestP2PFallback
- `test_fallback_to_tor_on_p2p_failure`: Automatic fallback when P2P fails
- `test_fallback_preserves_messages`: No message loss during fallback
- `test_tor_to_p2p_upgrade_after_fallback`: Retry P2P after successful Tor connection
- `test_graceful_degradation`: Handle connection degradation without disruption

#### TestNATTraversal
- `test_nat_info_exchange`: Exchange NAT information for hole punching
- `test_hole_punching_simulation`: Simulate UDP hole punching
- `test_symmetric_nat_handling`: Handle symmetric NAT scenarios
- `test_nat_detection`: Detect NAT type accurately

**Key Features Tested**:
- Parallel connection attempts (Tor + P2P)
- NAT traversal via UDP hole punching
- Automatic upgrade/downgrade based on availability
- Connection health monitoring
- Zero message loss during transitions

---

### 3. File Transfer Tests (`test_file_transfer.py`)

**Purpose**: Validate that file attachments are sent and received properly with integrity verification.

**Test Cases**:

#### TestFileTransfer
- `test_file_storage`: Save files to storage directory with hash
- `test_file_metadata`: Store metadata (name, path, hash, size) in database
- `test_chunked_transfer`: Split files into chunks (default 64KB)
- `test_chunk_reassembly`: Reassemble chunks correctly
- `test_file_integrity_verification`: Verify SHA-256 hash matches
- `test_progress_tracking`: Track transfer progress
- `test_large_file_transfer`: Handle files > 10MB
- `test_multiple_file_transfers`: Send multiple files concurrently
- `test_file_message_association`: Associate files with messages

#### TestFileTransferEdgeCases
- `test_empty_file_transfer`: Handle 0-byte files
- `test_single_byte_file`: Handle 1-byte files
- `test_exact_chunk_size_file`: Handle files exactly matching chunk size
- `test_chunk_order_preservation`: Maintain chunk sequence during transfer
- `test_interrupted_transfer_resume`: Resume interrupted transfers

**Key Features Tested**:
- Chunked transfer with configurable chunk size
- SHA-256 integrity verification
- Progress callback mechanism
- Database metadata tracking
- Resume capability for interrupted transfers
- Edge cases (empty, single byte, exact chunk size)

---

### 4. Onion Rotation Tests (`test_onion_rotation.py`)

**Purpose**: Validate that onion address rotation doesn't break connections between peers.

**Test Cases**:

#### TestOnionRotation
- `test_generate_new_onion_address`: Generate new v3 onion address
- `test_notify_peers_of_rotation`: Notify all connected peers
- `test_old_address_grace_period`: Maintain old address temporarily
- `test_peer_updates_address_record`: Peers update stored address
- `test_message_continuity_during_rotation`: No message loss during rotation
- `test_connection_preservation`: Maintain active connections
- `test_multiple_rotation_cycles`: Handle multiple rotations
- `test_rotation_with_offline_peers`: Handle peers offline during rotation

#### TestOnionRotationIntegration
- `test_seamless_rotation_workflow`: Complete rotation without interruption
- `test_rotation_with_pending_messages`: Queue messages during rotation
- `test_rotation_notification_retry`: Retry notifications with backoff
- `test_graceful_transition_period`: Gradual transition to new address
- `test_rotation_during_file_transfer`: Rotate without breaking file transfers
- `test_automatic_reconnection_after_rotation`: Auto-reconnect with new address
- `test_rotation_error_handling`: Handle rotation failures gracefully

**Key Features Tested**:
- Ephemeral v3 onion service generation
- Peer notification mechanism
- Grace period for dual address operation
- Message preservation during transition
- File transfer continuity
- Automatic reconnection
- Error recovery

---

### 5. Integration Tests (`test_integration_scenarios.py`)

**Purpose**: End-to-end validation of complete workflows combining multiple features.

**Test Cases**:

#### TestEndToEndScenarios
- `test_complete_offline_online_cycle`: Full workflow: offline → queue → online → deliver → confirm
- `test_complete_file_transfer_workflow`: End-to-end file transfer with all steps
- `test_p2p_with_tor_fallback_scenario`: Combined P2P attempt with Tor fallback
- `test_onion_rotation_with_active_session`: Rotate during active messaging
- `test_user_logoff_login_cycle`: Persist and restore state across app restarts
- `test_concurrent_operations`: Handle simultaneous message/file/rotation operations

#### TestEdgeCases
- `test_peer_goes_offline_mid_transfer`: Handle unexpected disconnection
- `test_duplicate_message_handling`: Prevent duplicate message insertion

**Key Features Tested**:
- Complete workflows from start to finish
- Feature interaction and integration
- State persistence across sessions
- Concurrent operation handling
- Edge case resilience

---

## Running Tests

### Run All Tests
```powershell
python tests/run_all_tests.py --mode all
```

### Run Scenario Tests Only
```powershell
python tests/run_all_tests.py --mode scenario
```

### Run Quick/Critical Tests
```powershell
python tests/run_all_tests.py --mode quick
```

### Run Individual Test Suites
```powershell
# Tor reconnection
python tests/test_tor_reconnection.py

# P2P connections
python tests/test_p2p_connection.py

# File transfers
python tests/test_file_transfer.py

# Onion rotation
python tests/test_onion_rotation.py

# Integration scenarios
python tests/test_integration_scenarios.py
```

---

## Test Coverage Summary

| Scenario | Test Files | Test Cases | Coverage |
|----------|-----------|-----------|----------|
| Tor Reconnection | 1 | 10 | Connection lifecycle, retry logic, state tracking |
| P2P Connections | 1 | 13 | Upgrade/fallback, NAT traversal, health monitoring |
| File Transfers | 1 | 14 | Chunking, reassembly, integrity, edge cases |
| Onion Rotation | 1 | 15 | Address generation, notification, continuity |
| Integration | 1 | 8 | End-to-end workflows, feature interaction |
| **Total** | **5** | **60** | **All critical scenarios** |

---

## Test Environment

### Prerequisites
- Python 3.8+
- All dependencies from `requirements.txt`
- Tor Expert Bundle (for Tor-related tests)
- SQLite3
- Temporary directories for test isolation

### Test Isolation
- Each test creates isolated temporary directories
- Separate database instances per test
- Mock external dependencies (Tor, sockets)
- Cleanup in `tearDown()` methods

### Mocking Strategy
- **Tor Process**: Mocked to avoid launching actual Tor
- **Sockets**: Mocked for P2P connections
- **File I/O**: Real files in temp directories
- **Database**: Real SQLite operations for integration fidelity

---

## Validation Criteria

### Pass Criteria
✓ All test cases pass without errors  
✓ No resource leaks (connections, files, database)  
✓ Proper cleanup in tearDown  
✓ State transitions tracked correctly  
✓ Messages delivered with correct status  
✓ Files transferred with integrity verification  

### Failure Indicators
✗ Test assertion failures  
✗ Uncaught exceptions  
✗ Resource leaks (open connections/files)  
✗ Database constraint violations  
✗ Hash mismatches in file transfers  
✗ Lost messages during transitions  

---

## Backend Logic Verified

### ConnectionManager (`peer/connection_manager.py`)
- ✓ `connect_to_peer()`: Initial connection establishment
- ✓ `attempt_direct_p2p()`: Parallel P2P attempts with fallback
- ✓ `monitor_connection_health()`: Heartbeat monitoring
- ✓ `send_file_chunks()`: Chunked file sending
- ✓ `receive_file_chunks()`: Chunk reassembly
- ✓ Retry logic for pending messages

### DBHandler (`db/db_handler.py`)
- ✓ `insert_message()`: Message storage
- ✓ `update_message_status()`: Status tracking
- ✓ `retry_pending_messages()`: Exponential backoff retry
- ✓ `mark_message_delivered()`: Delivery confirmation
- ✓ `insert_file_metadata()`: File metadata storage
- ✓ `get_pending_messages_for_peer()`: Pending queue retrieval

### TorManager (`tor_manager.py`)
- ✓ `start_tor()`: Tor process launch
- ✓ `create_ephemeral_onion_service()`: v3 onion generation
- ✓ `stop_tor()`: Graceful shutdown
- ✓ Address rotation mechanism

### FileTransfer (`utils/file_transfer.py`)
- ✓ `save_file_to_storage()`: File storage with hashing
- ✓ `split_file()`: Chunked splitting
- ✓ `reassemble_file()`: Chunk reassembly
- ✓ Integrity verification

---

## Known Limitations

1. **Tor Tests**: Some tests mock Tor process due to resource constraints
2. **Network Tests**: P2P tests use mocked sockets to avoid actual network operations
3. **Timing**: Tests use short timeouts for speed; production uses longer timeouts
4. **Concurrency**: Limited concurrent operation testing due to test environment constraints

---

## Future Enhancements

- [ ] Performance benchmarking for large file transfers
- [ ] Stress testing with hundreds of concurrent peers
- [ ] Network partition simulation
- [ ] Tor circuit failure recovery
- [ ] Byzantine peer behavior handling
- [ ] Coverage reporting with `coverage.py`
- [ ] Continuous integration pipeline

---

## Maintenance

### Adding New Tests
1. Create test file in `tests/` directory
2. Follow naming convention: `test_<feature>.py`
3. Inherit from `unittest.TestCase`
4. Implement `setUp()` and `tearDown()`
5. Add to relevant category in `run_all_tests.py`
6. Update this documentation

### Updating Tests
1. Maintain backward compatibility where possible
2. Update documentation to reflect changes
3. Run full test suite before committing
4. Add regression tests for bug fixes

---

## Support

For issues or questions about tests:
- Check test output for detailed error messages
- Review test documentation above
- Examine test source code for implementation details
- Verify test environment setup (dependencies, Tor)

---

**Last Updated**: 2025-01-10  
**Test Suite Version**: 1.0  
**Total Test Cases**: 60  
**Coverage**: All 5 critical scenarios
