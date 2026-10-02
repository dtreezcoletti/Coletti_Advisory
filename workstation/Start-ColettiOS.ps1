param(
    [string]$InstallRoot = "$env:USERPROFILE\ColettiOS-Workstation"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AppPath = Join-Path $InstallRoot "Coletti_Advisory"
$CoreRunner = Join-Path $AppPath "workstation\Run-Core.ps1"
$AdminRunner = Join-Path $AppPath "workstation\Run-Admin.ps1"
$ConfigFile = Join-Path $InstallRoot "config\workstation.json"

foreach ($Required in @($CoreRunner, $AdminRunner, $ConfigFile)) {
    if (-not (Test-Path $Required)) { throw "ColettiOS workstation is incomplete. Run Install-ColettiOS.ps1 first." }
}

$Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json

Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$CoreRunner`"",
    "-InstallRoot", "`"$InstallRoot`""
)

$HealthUrl = "http://127.0.0.1:$([int]$Config.core_port)/health"
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $Response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2
        if ($Response.status -eq "ok") { $Ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $Ready) { throw "ColettiOS Core did not become healthy. Check the ColettiOS Core window for the error." }

Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$AdminRunner`"",
    "-InstallRoot", "`"$InstallRoot`""
)

Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:$([int]$Config.app_port)"
