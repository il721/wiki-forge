<#
.SYNOPSIS
    Create a "Wiki-Forge" shortcut on the Desktop (and optionally the Start Menu).

.DESCRIPTION
    Creates a .lnk that launches the cockpit with pythonw.exe (no console window),
    with the working directory set to this repo. Run it once; re-run any time to
    refresh the shortcut (e.g. after moving the repo or upgrading Python).

.EXAMPLE
    .\Install-Shortcut.ps1
        Create the shortcut on the Desktop.

.EXAMPLE
    .\Install-Shortcut.ps1 -StartMenu
        Also add it to the Start Menu.
#>
[CmdletBinding()]
param(
    [switch]$StartMenu
)

$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot

# Resolve a GUI Python interpreter (pythonw.exe) from PATH.
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error "Python was not found on PATH. Install Python 3.10+ and try again."
    exit 1
}
$pythonw = Join-Path (Split-Path $python.Source) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = $python.Source }

# Use the bundled .ico if present, otherwise fall back to Python's own icon.
$icon = Join-Path $Root 'assets\wiki-forge.ico'
if (Test-Path $icon) { $iconLocation = "$icon,0" } else { $iconLocation = "$pythonw,0" }

function New-WikiForgeShortcut([string]$Path) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($Path)
    $lnk.TargetPath       = $pythonw
    $lnk.Arguments        = '-m cockpit.app'
    $lnk.WorkingDirectory = $Root
    $lnk.Description       = 'Wiki-Forge - desktop cockpit for LLM Wiki vaults'
    $lnk.IconLocation      = $iconLocation
    $lnk.Save()
    Write-Host "Created shortcut: $Path"
}

$desktop = [Environment]::GetFolderPath('Desktop')
New-WikiForgeShortcut (Join-Path $desktop 'Wiki-Forge.lnk')

if ($StartMenu) {
    $programs = [Environment]::GetFolderPath('Programs')
    New-WikiForgeShortcut (Join-Path $programs 'Wiki-Forge.lnk')
}

Write-Host "Done. Double-click the Wiki-Forge icon to launch."
