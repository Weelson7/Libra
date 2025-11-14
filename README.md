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

