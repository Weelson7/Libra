## Security & Privacy Hardening (Phase 6)

### Container/Sandbox Isolation
- Recommended: Run Libra in Docker or Podman with minimal base image, read-only root filesystem, and no privileged mode.
- For Linux: Use Firejail, AppArmor, or SELinux to restrict system calls and file system access.
- Use network namespace isolation to prevent unauthorized access to host network.
- Principle of Least Privilege: Run as non-root user with minimal permissions; drop capabilities after startup.

### Network Isolation
- Only allow outbound Tor connections and authenticated peer connections.
- No listening on public interfaces except through Tor onion service.

### Data Protection
- All local data is encrypted at rest using strong encryption (AES-256 via Fernet).
- Sensitive data is sanitized from logs and securely wiped from memory.

### Application Security
- Input validation is enforced on all user and network inputs.
- No code execution from external sources.
- Intrusion detection and dependency scanning stubs included.

### Privacy Hardening
- Onion addresses can be rotated for enhanced privacy.
- Dummy traffic stubs included to prevent fingerprinting.
- Metadata leak audit utility included.
# Libra — Phase 1 Setup

This repository contains the initial skeleton for the Libra decentralized messaging project.

Quick start (Windows PowerShell):

```powershell
# create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt

# run the basic stub
python main.py
```

Notes:
- `config.py` contains configuration defaults and `ensure_dirs()` to create `data/` and `logs/`.
- `utils/logger.py` provides a lightweight logger used by `main.py`.
- See `BUILD_PLAN.md` for the full 15 phase build plan.

CLI Usage

The repository includes a simple CLI entrypoint in `main.py`. Available commands:

- `python main.py init` — initialize data directories, the database, and create a keypair (you will be prompted for a passphrase unless `LIBRA_KEY_PASSPHRASE` is set).
- `python main.py identity` — show local identity (public key and fingerprint).
- `python main.py send-local "message text"` — encrypt, sign and store a local message for the current peer.
- `python main.py read-local` — read and decrypt stored local messages for the current peer.

Examples (PowerShell):

```powershell
python main.py init
python main.py send-local "Hello from Libra"
python main.py read-local
```

Notes on automation

For automated tests or scripts you can set the passphrase via the `LIBRA_KEY_PASSPHRASE` environment variable, but avoid this in production.


## Tor Setup & Troubleshooting (Phase 7)

Libra uses Tor for anonymous peer discovery and communication. To use Tor features:

### Setup
- Ensure Tor is installed and accessible (see `tor_manager.py` for configuration).
- On Windows, the Tor Expert Bundle is included in `utils/tor-expert-bundle-windows-x86_64-15.0.1/`.
- By default, Libra will attempt to start Tor automatically if enabled in config.

### Direct P2P Setup
For direct peer-to-peer connections (faster than Tor), you need SSL certificates:
- Run `python main.py generate-cert` to create self-signed certificates.
- This creates `server.crt` and `server.key` files for secure direct connections.
- Without certificates, direct P2P will fall back to unencrypted or Tor-only mode.

### CLI Commands
- `python main.py tor-status` — Show Tor connection status.
- `python main.py set-connection-preference [tor|direct|auto]` — Set preferred connection mode.
- `python main.py show-connection-status` — Show current connection status (Tor, direct, fallback).
- `python main.py generate-cert` — Generate self-signed SSL certificates for direct P2P.

### Troubleshooting
- If Tor fails to start, check your firewall and ensure no other Tor process is running.
- For custom Tor paths, edit your config or use the CLI to specify the path.
- If you cannot connect to peers, verify your onion address and network settings.
- If direct P2P shows "[Errno 2] No such file or directory", run `generate-cert` to create certificates.

For advanced Tor configuration, see `tor_manager.py` and consult the official Tor documentation.

