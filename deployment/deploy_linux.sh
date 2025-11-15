#!/bin/bash
# Libra deployment script for Linux
set -e

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional: create logs and data folders
mkdir -p logs data/files

echo "Libra deployed on Linux. Activate venv and run ./run_linux.sh to start."
