$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Client = Join-Path $Root "client"
$Server = Join-Path $Root "server"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$ErrorMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$ErrorMessage Exit code: $LASTEXITCODE"
    }
}

Write-Host "Building frontend..."
Push-Location $Client
Invoke-Checked { npm install } "npm install failed."
Invoke-Checked { npm run build } "Frontend build failed."
Pop-Location

Write-Host "Preparing Python build dependencies..."
Push-Location $Server
if (-not (Test-Path ".venv")) {
    Invoke-Checked { python -m venv .venv } "Python virtual environment creation failed."
}
Invoke-Checked { .\.venv\Scripts\python.exe -m pip install -r requirements.txt } "Backend dependency installation failed."
Invoke-Checked { .\.venv\Scripts\python.exe -m pip install pyinstaller } "PyInstaller installation failed."
Pop-Location

Write-Host "Building Windows EXE..."
Push-Location $Root
Invoke-Checked { & (Join-Path $Server ".venv\Scripts\pyinstaller.exe") .\launcher\vamos-launcher.spec --noconfirm --clean } "PyInstaller build failed."
Pop-Location

Write-Host "Done. EXE:"
Write-Host (Join-Path $Root "dist\Vamos Subscription Tracker.exe")
