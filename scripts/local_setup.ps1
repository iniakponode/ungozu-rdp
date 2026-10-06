$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$Py = "$Root\.runtime\venv\Scripts\python.exe"
$Pip = "$Root\.runtime\venv\Scripts\pip.exe"
$Npm = (Get-Command npm.cmd -ErrorAction Stop).Source

function Invoke-Checked {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][scriptblock]$Command
    )

    Write-Host "`n==> $Label"
    & $Command
    $code = $LASTEXITCODE
    if ($null -ne $code -and $code -ne 0) {
        throw "$Label failed with exit code $code."
    }
}

if (!(Test-Path "$Root\backend\.env")) {
    Copy-Item "$Root\backend\.env.example" "$Root\backend\.env"
    Write-Host "Created backend/.env - edit secrets before production."
}
if (!(Test-Path "$Root\frontend\.env.local")) {
    Copy-Item "$Root\frontend\.env.local.example" "$Root\frontend\.env.local"
}
if (!(Test-Path "$Root\.runtime\venv")) {
    Write-Host "Creating Python virtual environment..."
    & python -m venv "$Root\.runtime\venv"
    if ($LASTEXITCODE -ne 0) { throw "Python virtual environment creation failed with exit code $LASTEXITCODE." }
}

Invoke-Checked "Upgrade pip" { & $Py -m pip install --upgrade pip }
Invoke-Checked "Install backend dependencies" { & $Pip install -r "$Root\backend\requirements.txt" }

Push-Location "$Root\frontend"
try {
    Invoke-Checked "Install frontend dependencies" { & $Npm ci }
}
finally {
    Pop-Location
}

Write-Host "`nSetup complete. Start MariaDB with: docker compose -f docker-compose.local.yml up -d db" -ForegroundColor Green
