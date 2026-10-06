$Root = Split-Path -Parent $PSScriptRoot
Push-Location "$Root\frontend"; npm run dev -- --hostname 127.0.0.1 --port 3010; Pop-Location
