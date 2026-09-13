param(
    [string]$InstallRoot = "$env:USERPROFILE\ColettiOS-Workstation"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ConfigFile = Join-Path $InstallRoot "config\workstation.json"
if (-not (Test-Path $ConfigFile)) { throw "ColettiOS workstation config not found. Run Install-ColettiOS.ps1 first." }
$Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json

$AppPath = Join-Path $InstallRoot "Coletti_Advisory"
$AppPython = Join-Path $AppPath ".venv\Scripts\python.exe"
if (-not (Test-Path $AppPython)) { throw "Coletti & Co. virtual environment is missing. Run the installer again." }

Set-Location $AppPath
$Host.UI.RawUI.WindowTitle = "ColettiOS Admin Portal"
& $AppPython -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port ([int]$Config.app_port) --server.headless false
