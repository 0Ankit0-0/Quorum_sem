param(
  [string]$OutputDir = "..\\frontend\\src-tauri\\bin"
)

$ErrorActionPreference = "Stop"

Write-Host "Building backend executable..." -ForegroundColor Cyan

if (-not (Test-Path $OutputDir)) {
  New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

python -m pip install --upgrade pip | Out-Null
python -m pip install -r ..\\requirements.txt
python -m pip install pyinstaller

Push-Location ..
try {
  pyinstaller --noconfirm --onefile `
    --name quorum-backend `
    --add-data "data;data" `
    --add-data "logs;logs" `
    --add-data "reports_output;reports_output" `
    run_backend.py
  Copy-Item -Force "dist\\quorum-backend.exe" $OutputDir
  Write-Host "Copied backend exe to $OutputDir\\quorum-backend.exe" -ForegroundColor Green
} finally {
  Pop-Location
}
