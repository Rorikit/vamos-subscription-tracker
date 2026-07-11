$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Client = Join-Path $Root "client"
$Server = Join-Path $Root "server"

Write-Host "Building frontend..."
Push-Location $Client
npm install
npm run build
Pop-Location

Write-Host "Preparing Python build dependencies..."
Push-Location $Server
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller
Pop-Location

Write-Host "Building Windows EXE..."
Push-Location $Root
& (Join-Path $Server ".venv\Scripts\pyinstaller.exe") .\launcher\vamos-launcher.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}
Pop-Location

Write-Host "Done. EXE:"
Write-Host (Join-Path $Root "dist\Vamos Subscription Tracker.exe")
