param(
    [string]$InstallRoot = "$env:USERPROFILE\ColettiOS-Workstation"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ConfigFile = Join-Path $InstallRoot "config\workstation.json"
if (-not (Test-Path $ConfigFile)) { throw "ColettiOS workstation config not found. Run Install-ColettiOS.ps1 first." }
$Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json

$CorePath = Join-Path $InstallRoot "ColettiOS"
$CorePython = Join-Path $CorePath ".venv\Scripts\python.exe"
if (-not (Test-Path $CorePython)) { throw "ColettiOS Core virtual environment is missing. Run the installer again." }

$env:COLETTIOS_SERVICE_TOKEN = [string]$Config.core_token
$env:COLETTIOS_DB_PATH = [string]$Config.core_database

Set-Location $CorePath
$Host.UI.RawUI.WindowTitle = "ColettiOS Core"
& $CorePython -m uvicorn colettios_core.service:app --host 127.0.0.1 --port ([int]$Config.core_port)
