# Corne layout overlay installer (Windows, no admin needed).
#
# From GitHub (any PC):
#   irm https://raw.githubusercontent.com/Dfulop98/corne-zmk-view/master/overlay/install.ps1 | iex
# From a copied overlay folder:
#   double-click install.cmd
# Uninstall:
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/Dfulop98/corne-zmk-view/master/overlay/install.ps1))) -Uninstall
#   or: install.cmd -Uninstall
#
# Re-running it updates the files (e.g. after a new layout.png).

param(
    [switch]$Uninstall,
    [string]$Dest = (Join-Path $env:LOCALAPPDATA 'CorneLayout'),
    [switch]$NoAutostart
)

$ErrorActionPreference = 'Stop'
$repoRaw = 'https://raw.githubusercontent.com/Dfulop98/corne-zmk-view/master/overlay'
$files = 'layout_overlay.ps1', 'layout.png'
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Corne layout.lnk'

function Stop-Overlay {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like '*layout_overlay.ps1*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

Stop-Overlay

if ($Uninstall) {
    Remove-Item $lnk -ErrorAction SilentlyContinue
    Remove-Item $Dest -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host 'Corne layout overlay eltavolitva.' -ForegroundColor Green
    return
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$local = $PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot 'layout_overlay.ps1'))
foreach ($f in $files) {
    $target = Join-Path $Dest $f
    if ($local) {
        Copy-Item (Join-Path $PSScriptRoot $f) $target -Force
    } else {
        Invoke-WebRequest "$repoRaw/$f" -OutFile $target -UseBasicParsing
    }
}

$script = Join-Path $Dest 'layout_overlay.ps1'
$psArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""

if (-not $NoAutostart) {
    $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $sc.TargetPath = 'powershell.exe'
    $sc.Arguments = $psArgs
    $sc.WindowStyle = 7
    $sc.Save()
}

Start-Process powershell.exe -ArgumentList $psArgs -WindowStyle Hidden

Write-Host "Corne layout overlay telepitve: $Dest" -ForegroundColor Green
if (-not $NoAutostart) { Write-Host 'Windows inditasakor automatikusan elindul.' }
Write-Host 'Kiprobalas: EDIT + N a billentyuzeten (F24).'
