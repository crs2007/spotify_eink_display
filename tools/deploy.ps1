# Copy the firmware to a Pico 2 W running MicroPython (needs: pip install mpremote).
#   .\tools\deploy.ps1            # auto-detect port
#   .\tools\deploy.ps1 -Port COM5
param([string]$Port = "auto")

$ErrorActionPreference = "Stop"
$fw = Join-Path $PSScriptRoot "..\firmware"
$secrets = Join-Path $PSScriptRoot "..\secrets.yaml"
if (-not (Test-Path $secrets)) {
    throw "secrets.yaml missing: copy secrets.example.yaml to secrets.yaml and fill it in."
}
$conn = if ($Port -eq "auto") { @() } else { @("connect", $Port) }

mpremote @conn mkdir :lib 2>$null
foreach ($f in Get-ChildItem (Join-Path $fw "lib") -Filter *.py) {
    mpremote @conn cp $f.FullName ":lib/$($f.Name)"
}
mpremote @conn cp (Join-Path $fw "config.py") :config.py
mpremote @conn cp $secrets :secrets.yaml
mpremote @conn cp (Join-Path $fw "main.py") :main.py
mpremote @conn reset
Write-Host "Deployed. Watch the log with: mpremote $($conn -join ' ') repl"
