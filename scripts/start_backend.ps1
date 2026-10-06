$Root = Split-Path -Parent $PSScriptRoot
Push-Location "$Root\backend"
& "$Root\.runtime\venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8010 --reload
Pop-Location
