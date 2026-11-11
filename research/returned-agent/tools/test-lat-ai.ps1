param([string]$ReportDir)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root 'lat-ai'
$node = Join-Path $root 'work/lat-ai-runtime/node/node.exe'
$python = Join-Path $root 'work/lat-ai-runtime/python/python.exe'
if (-not $ReportDir) { $ReportDir = Join-Path $root ('outputs/checks-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')) }
if (Test-Path -LiteralPath $ReportDir) { throw 'Report directory already exists; previous results are preserved.' }
$null = New-Item -ItemType Directory -Path $ReportDir
$saved = @{}
foreach ($name in @('PYTHONUTF8','DJANGO_SETTINGS_MODULE','LAD_AI_TEST','LAD_AI_RUNTIME')) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$results = [ordered]@{}
function Invoke-Check([string]$Name, [string]$Exe, [string[]]$Arguments) {
    $log = Join-Path $ReportDir ($Name + '.log')
    & $Exe @Arguments *> $log
    $code = $LASTEXITCODE
    $results[$Name] = @{ exit_code=$code; log=$log }
    if ($code -ne 0) { Get-Content -LiteralPath $log -Tail 25; throw "Check failed: $Name ($code)" }
    Write-Host "$Name passed"
}
try {
    $env:PYTHONUTF8 = '1'
    $env:DJANGO_SETTINGS_MODULE = 'config.ai_local'
    $env:LAD_AI_TEST = '1'
    $env:LAD_AI_RUNTIME = Join-Path $ReportDir 'test-runtime'
    Invoke-Check 'integration' $node @('--test', (Join-Path $source 'integration/ai/test/*.test.mjs'))
    Invoke-Check 'contracts' $node @((Join-Path $source 'integration/ai/check.mjs'))
    Invoke-Check 'django' $python @((Join-Path $source 'backend/manage.py'), 'test', 'tutor', 'progress', '--verbosity', '1')
    Invoke-Check 'core-baseline' $node @('--test', (Join-Path $root 'LAD-AI-handoff-2026-11-11/project/outputs/ai-module-v10-2026-11-10/test/*.test.mjs'))
} finally {
    foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
    $results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ReportDir 'results.json') -Encoding UTF8
}
Write-Host "Checks complete. Logs: $ReportDir"
Write-Host 'Synthetic/local checks only; no live model or pedagogical acceptance.'
