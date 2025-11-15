# Libra deployment script for Windows
$ErrorActionPreference = 'Stop'

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Optional: create logs and data folders
if (!(Test-Path logs)) { New-Item -ItemType Directory -Path logs }
if (!(Test-Path data\files)) { New-Item -ItemType Directory -Path data\files }

Write-Host "Libra deployed on Windows. Activate venv and run ./run_windows.ps1 to start."
