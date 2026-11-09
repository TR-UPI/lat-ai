param([string]$RuntimeDir, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
if (-not $RuntimeDir) {
    $workspaceRuntime = Join-Path (Split-Path -Parent (Split-Path -Parent $projectDir)) 'work/runtime'
    if (Test-Path -LiteralPath (Join-Path $workspaceRuntime 'python-env/python.exe')) {
        $RuntimeDir = $workspaceRuntime
    } else {
        $RuntimeDir = Join-Path $projectDir '.runtime'
    }
}
$RuntimeDir = [IO.Path]::GetFullPath($RuntimeDir)
& (Join-Path $PSScriptRoot 'setup-runtime.ps1') -RuntimeDir $RuntimeDir
if ($LASTEXITCODE -ne 0) { throw 'Runtime setup failed.' }
$env:LAT_RUNTIME_DIR = $RuntimeDir
$env:PYTHONUTF8 = '1'
$pythonExe = Join-Path $RuntimeDir 'python-env/python.exe'
& $pythonExe (Join-Path $PSScriptRoot 'cache-model.py') --runtime-dir $RuntimeDir
if ($LASTEXITCODE -ne 0) { throw 'Search model preparation failed. See the output above.' }
& $pythonExe (Join-Path $PSScriptRoot 'local_stack.py') prepare
if ($LASTEXITCODE -ne 0) { throw 'Database or Django setup failed. See the output above.' }
& $pythonExe (Join-Path $PSScriptRoot 'local_stack.py') verify
if ($LASTEXITCODE -ne 0) { throw 'API verification failed. See the output above.' }
Write-Host ''
Write-Host 'LAT AI is ready: http://localhost:5173/'
Write-Host 'Demo login: demo@lat-ai.local'
Write-Host 'Demo password: LatAI-Demo-2026!'
if (-not $NoBrowser) { Start-Process 'http://localhost:5173/' }
