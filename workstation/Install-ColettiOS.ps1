param(
    [string]$InstallRoot = "$env:USERPROFILE\ColettiOS-Workstation"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3.12 --version *> $null
            if ($LASTEXITCODE -eq 0) { return @("py", "-3.12") }
        } catch {}
        try {
            & py -3.11 --version *> $null
            if ($LASTEXITCODE -eq 0) { return @("py", "-3.11") }
        } catch {}
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ([version]$version -ge [version]"3.11") { return @("python") }
    }
    throw "Python 3.11 or 3.12 is required. Install Python, then run this installer again."
}

function Invoke-Python {
    param([string[]]$PythonCommand, [string[]]$Arguments)
    $exe = $PythonCommand[0]
    $prefix = @()
    if ($PythonCommand.Count -gt 1) { $prefix = $PythonCommand[1..($PythonCommand.Count - 1)] }
    & $exe @prefix @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed." }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git for Windows is required. Install Git, then run this installer again."
}

$PythonCommand = Resolve-Python
$CorePath = Join-Path $InstallRoot "ColettiOS"
$AppPath = Join-Path $InstallRoot "Coletti_Advisory"
$ConfigPath = Join-Path $InstallRoot "config"
$DataPath = Join-Path $InstallRoot "data"
$LauncherPath = Join-Path $InstallRoot "launcher"

New-Item -ItemType Directory -Force -Path $InstallRoot, $ConfigPath, $DataPath, $LauncherPath | Out-Null

if (-not (Test-Path (Join-Path $CorePath ".git"))) {
    Write-Host "Cloning private ColettiOS Core..."
    git clone https://github.com/dtreezcoletti/ColettiOS.git $CorePath
    if ($LASTEXITCODE -ne 0) { throw "Could not clone the private ColettiOS repository. Sign in to GitHub when prompted and run again." }
} else {
    Write-Host "Updating ColettiOS Core..."
    git -C $CorePath pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw "Could not update ColettiOS Core." }
}

if (-not (Test-Path (Join-Path $AppPath ".git"))) {
    Write-Host "Cloning Coletti & Co. application..."
    git clone https://github.com/dtreezcoletti/Coletti_Advisory.git $AppPath
    if ($LASTEXITCODE -ne 0) { throw "Could not clone the Coletti & Co. application repository." }
} else {
    Write-Host "Updating Coletti & Co. application..."
    git -C $AppPath pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw "Could not update Coletti & Co. application." }
}

Write-Host "Creating ColettiOS Core environment..."
Invoke-Python -PythonCommand $PythonCommand -Arguments @("-m", "venv", (Join-Path $CorePath ".venv"))
$CorePython = Join-Path $CorePath ".venv\Scripts\python.exe"
& $CorePython -m pip install --upgrade pip
Push-Location $CorePath
try {
    & $CorePython -m pip install -e ".[all]"
    if ($LASTEXITCODE -ne 0) { throw "ColettiOS Core dependency installation failed." }
} finally { Pop-Location }

Write-Host "Creating Coletti & Co. environment..."
Invoke-Python -PythonCommand $PythonCommand -Arguments @("-m", "venv", (Join-Path $AppPath ".venv"))
$AppPython = Join-Path $AppPath ".venv\Scripts\python.exe"
& $AppPython -m pip install --upgrade pip
Push-Location $AppPath
try {
    & $AppPython -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Coletti & Co. dependency installation failed." }
} finally { Pop-Location }

$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$tokenBytes = New-Object byte[] 48
$rng.GetBytes($tokenBytes)
$rng.Dispose()
$LocalToken = [Convert]::ToBase64String($tokenBytes)

$LocalConfig = [ordered]@{
    version = 1
    mode = "local_demo"
    core_url = "http://127.0.0.1:8765"
    core_token = $LocalToken
    core_database = (Join-Path $DataPath "colettios.sqlite3")
    app_port = 8501
    core_port = 8765
}
$LocalConfig | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $ConfigPath "workstation.json")

$SecretsDir = Join-Path $AppPath ".streamlit"
New-Item -ItemType Directory -Force -Path $SecretsDir | Out-Null
$SecretsFile = Join-Path $SecretsDir "secrets.toml"
@"
APP_MODE = "demo"
SESSION_TTL_MINUTES = "480"
COLETTIOS_BACKEND = "http"
STORAGE_BACKEND = "local_demo"
COLETTIOS_API_URL = "http://127.0.0.1:8765"
COLETTIOS_API_TOKEN = "$LocalToken"
"@ | Set-Content -Encoding UTF8 $SecretsFile

$RunCore = @'
param([string]$InstallRoot)
$ErrorActionPreference = "Stop"
$Config = Get-Content (Join-Path $InstallRoot "config\workstation.json") -Raw | ConvertFrom-Json
$CorePath = Join-Path $InstallRoot "ColettiOS"
$CorePython = Join-Path $CorePath ".venv\Scripts\python.exe"
$env:COLETTIOS_SERVICE_TOKEN = [string]$Config.core_token
$env:COLETTIOS_DB_PATH = [string]$Config.core_database
Set-Location $CorePath
$Host.UI.RawUI.WindowTitle = "ColettiOS Core"
& $CorePython -m uvicorn colettios_core.service:app --host 127.0.0.1 --port ([int]$Config.core_port)
'@
$RunCore | Set-Content -Encoding UTF8 (Join-Path $LauncherPath "Run-Core.ps1")

$RunAdmin = @'
param([string]$InstallRoot)
$ErrorActionPreference = "Stop"
$Config = Get-Content (Join-Path $InstallRoot "config\workstation.json") -Raw | ConvertFrom-Json
$AppPath = Join-Path $InstallRoot "Coletti_Advisory"
$AppPython = Join-Path $AppPath ".venv\Scripts\python.exe"
Set-Location $AppPath
$Host.UI.RawUI.WindowTitle = "ColettiOS Admin Portal"
& $AppPython -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port ([int]$Config.app_port) --server.headless true
'@
$RunAdmin | Set-Content -Encoding UTF8 (Join-Path $LauncherPath "Run-Admin.ps1")

$StartColettiOS = @'
param([string]$InstallRoot)
$ErrorActionPreference = "Stop"
$Config = Get-Content (Join-Path $InstallRoot "config\workstation.json") -Raw | ConvertFrom-Json
$LauncherPath = Join-Path $InstallRoot "launcher"
$CoreRunner = Join-Path $LauncherPath "Run-Core.ps1"
$AdminRunner = Join-Path $LauncherPath "Run-Admin.ps1"
Start-Process powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$CoreRunner`"", "-InstallRoot", "`"$InstallRoot`"")
$HealthUrl = "http://127.0.0.1:$([int]$Config.core_port)/health"
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $Response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2
        if ($Response.status -eq "ok") { $Ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $Ready) { throw "ColettiOS Core did not become healthy. Check the ColettiOS Core window." }
Start-Process powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$AdminRunner`"", "-InstallRoot", "`"$InstallRoot`"")
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:$([int]$Config.app_port)"
'@
$StartScript = Join-Path $LauncherPath "Start-ColettiOS.ps1"
$StartColettiOS | Set-Content -Encoding UTF8 $StartScript

Write-Host "Running Core tests..."
Push-Location $CorePath
try {
    & $CorePython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "ColettiOS Core tests failed. The workstation was installed but should not be treated as verified." }
} finally { Pop-Location }

Write-Host "Running commercial application tests..."
Push-Location $AppPath
try {
    & $AppPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Coletti & Co. tests failed. The workstation was installed but should not be treated as verified." }
} finally { Pop-Location }

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "ColettiOS.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`" -InstallRoot `"$InstallRoot`""
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Description = "Launch ColettiOS local workstation"
$Shortcut.Save()

Write-Host ""
Write-Host "ColettiOS workstation installed and tests passed."
Write-Host "Install root: $InstallRoot"
Write-Host "Desktop shortcut: ColettiOS"
Write-Host "Mode: controlled local/demo with the real private ColettiOS Core service running locally."
Write-Host "Real-client production authorization remains closed until the production security and infrastructure gates pass."
