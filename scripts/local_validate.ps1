$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$Py = "$Root\.runtime\venv\Scripts\python.exe"
$Alembic = "$Root\.runtime\venv\Scripts\alembic.exe"
$Npm = (Get-Command npm.cmd -ErrorAction Stop).Source

if (!(Test-Path $Py)) { throw "Run scripts/local_setup.ps1 first." }
if (!(Test-Path $Alembic)) { throw "Alembic is not installed in the project virtual environment. Run scripts/local_setup.ps1 first." }

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

Push-Location "$Root\backend"
try {
    Invoke-Checked "Python source compilation" { & $Py -m compileall -q app }
    Invoke-Checked "Alembic head check" { & $Alembic heads }
    Invoke-Checked "Database migration to head" { & $Alembic upgrade head }
    Invoke-Checked "Alembic current revision" { & $Alembic current }
}
finally {
    Pop-Location
}

Push-Location "$Root\frontend"
try {
    Invoke-Checked "TypeScript type check" { & $Npm run type-check }
    Invoke-Checked "Next.js production build" { & $Npm run build }
}
finally {
    Pop-Location
}

Write-Host "`nValidation passed: Python compile, Alembic migration, TypeScript check and Next.js build." -ForegroundColor Green
