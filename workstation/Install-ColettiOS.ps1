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

New-Item -ItemType Directory -Force -Path $InstallRoot, $ConfigPath, $DataPath | Out-Null

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

$StartScript = Join-Path $AppPath "workstation\Start-ColettiOS.ps1"
if (Test-Path $StartScript) {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $Desktop "ColettiOS.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`" -InstallRoot `"$InstallRoot`""
    $Shortcut.WorkingDirectory = $AppPath
    $Shortcut.Description = "Launch ColettiOS local workstation"
    $Shortcut.Save()
}

Write-Host ""
Write-Host "ColettiOS workstation installed and tests passed."
Write-Host "Install root: $InstallRoot"
Write-Host "Desktop shortcut: ColettiOS"
Write-Host "This workstation is configured for controlled local/demo use only; it does not authorize production or real-client data."
