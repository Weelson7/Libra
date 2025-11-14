<#
Simple setup script for Windows PowerShell to create a venv and install dependencies.
Run from project root in PowerShell (may require adjusting ExecutionPolicy):

> .\scripts\setup_env.ps1

#>

python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Environment setup complete. Activate with .\.venv\Scripts\Activate.ps1"
