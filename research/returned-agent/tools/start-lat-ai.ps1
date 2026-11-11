param([switch]$EnableModel, [switch]$NoBrowser, [switch]$Restart, [switch]$OriginalProfile)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if ((Test-Path -LiteralPath (Join-Path $root 'work/local-pc/profile.json')) -and -not $OriginalProfile) {
    & (Join-Path $PSScriptRoot 'start-local-pc-profile.ps1') -EnableModel:$EnableModel -NoBrowser:$NoBrowser -Restart:$Restart
    return
}
if ($Restart) { & (Join-Path $PSScriptRoot 'start-local-pc-profile.ps1') -Restart -StopOnly }
$python = Join-Path $root 'work/lat-ai-runtime/python/python.exe'
$nodeDir = Join-Path $root 'work/lat-ai-runtime/node'
$originalPath = $env:PATH
try {
    $env:PATH = $nodeDir + [IO.Path]::PathSeparator + $originalPath
    & (Join-Path $root 'lat-ai/tools/start-ai-review.ps1') -PythonExe $python -EnableModel:$EnableModel -NoBrowser:$NoBrowser
} finally { $env:PATH = $originalPath }
