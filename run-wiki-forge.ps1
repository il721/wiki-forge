<#
.SYNOPSIS
    Launch the Wiki-Forge desktop cockpit.

.DESCRIPTION
    Runs `python -m cockpit.app` from the repo root using the Python found on PATH.
    By default it launches with pythonw.exe so no console window stays open (it's a
    GUI app). Use -Console to keep a console attached and see logs / tracebacks.

.EXAMPLE
    .\run-wiki-forge.ps1
        Launch the app silently (no console window).

.EXAMPLE
    .\run-wiki-forge.ps1 -Console
        Launch with a console window so you can see output and errors.
#>
[CmdletBinding()]
param(
    [switch]$Console
)

$ErrorActionPreference = 'Stop'

# Repo root = folder this script lives in.
$Root = $PSScriptRoot

# Find a Python interpreter on PATH.
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Error "Python was not found on PATH. Install Python 3.10+ and try again."
    exit 1
}

if ($Console) {
    # Keep console attached: run python and wait, so output/errors are visible.
    Push-Location $Root
    try {
        & $python.Source -m cockpit.app @args
    }
    finally {
        Pop-Location
    }
}
else {
    # GUI launch with pythonw.exe (no lingering console window).
    $pythonw = Join-Path (Split-Path $python.Source) 'pythonw.exe'
    if (-not (Test-Path $pythonw)) {
        $pythonw = $python.Source   # fall back to plain python if pythonw is missing
    }
    Start-Process -FilePath $pythonw -ArgumentList '-m', 'cockpit.app' -WorkingDirectory $Root
}
