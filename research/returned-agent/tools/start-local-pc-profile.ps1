param([switch]$EnableModel,[switch]$NoBrowser,[switch]$Restart,[switch]$StopOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'local-launch-guard.ps1')
$launchGuard=Open-LatLaunchGuard (Join-Path $root 'work/local-pc/launcher.guard')
try {
$source=Join-Path $root 'lat-ai'
$runtime=Join-Path $source '.runtime/i02'
$python=Join-Path $root 'work/lat-ai-runtime/python/python.exe'
$node=Join-Path $root 'work/lat-ai-runtime/node/node.exe'
$profile=Get-Content -LiteralPath (Join-Path $root 'work/local-pc/profile.json') -Raw | ConvertFrom-Json
if ($profile.machine -ine [Environment]::MachineName) { throw 'Local profile belongs to another computer.' }
if (-not $StopOnly) {
    $built=& $python (Join-Path $PSScriptRoot 'build-local-pc-profile.py')
    if ($LASTEXITCODE -ne 0) { throw 'Local profile build failed; running services were not changed.' }
    $build=($built | ConvertFrom-Json).build
}
$ports=@(5173,8000,8372)
$listeners=@(Get-LatLaunchListeners)
if ($listeners.Count) {
    $record=Get-Content -LiteralPath (Join-Path $runtime 'processes.json') -Raw | ConvertFrom-Json
    $ids=@([int]$record.site,[int]$record.worker,[int]$record.django)
    if (@($listeners | Where-Object { $_.OwningProcess -notin $ids }).Count) { throw 'A port belongs to a different process; no processes stopped.' }
    $started=[datetime]::Parse($record.started)
    $processes=@()
    foreach ($kind in @('site','worker','django')) {
        $processId=[int]$record.$kind
        $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
        $expectedExe=if ($kind -eq 'django') {$python} else {$node}
        $needle=switch ($kind) {'site' {'server.cjs'} 'worker' {'integration/ai/worker.mjs'} 'django' {'runserver 127.0.0.1:8000'}}
        if (-not $proc -or $proc.ExecutablePath -ine $expectedExe -or -not $proc.CommandLine.Contains($needle) -or [math]::Abs(($proc.CreationDate-$started).TotalSeconds) -gt 15) { throw "Cannot prove ownership of $kind process; nothing stopped." }
        $processes += $proc
    }
    $headers=@{'X-LAD-IPC'=(Get-Content -LiteralPath (Join-Path $runtime 'ipc-secret.txt') -Raw).Trim()}
    $health=Invoke-RestMethod 'http://127.0.0.1:8372/health' -Headers $headers -TimeoutSec 5
    if (-not $Restart) {
        if ($EnableModel -and -not $health.tutor.enabled) {
            $null=Invoke-RestMethod 'http://127.0.0.1:8372/control' -Headers $headers -Method Post -ContentType 'application/json' -Body '{"action":"enable"}' -TimeoutSec 150
        }
        Write-Host 'Recorded LAT AI instance already running; no duplicate services started.'
        return
    }
    if ($health.loading -or $health.tutor.busy -or $health.tutor.queued) { throw 'Requests or provisioning are active; cannot restart.' }
    if ($health.model) {
        $null=Invoke-RestMethod 'http://127.0.0.1:8372/control' -Headers $headers -Method Post -ContentType 'application/json' -Body '{"action":"retire"}' -TimeoutSec 15
        $health=Invoke-RestMethod 'http://127.0.0.1:8372/health' -Headers $headers -TimeoutSec 5
    }
    if ($health.model -or $health.tutor.quarantined -or (Test-Path -LiteralPath (Join-Path $runtime 'model-inflight.lock'))) { throw 'Model retirement is not proven; no restart.' }
    foreach ($proc in $processes) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop }
}
if ($StopOnly) { Write-Host 'Recorded LAT AI services stopped; shared LM Studio remains running.'; return }
$saved=@{}
$startedChildren=@()
$servicesVerified=$false
foreach ($key in @('PATH','PYTHONUTF8','DJANGO_SETTINGS_MODULE','LAD_AI_RUNTIME','LAD_AI_TEST')) { $saved[$key]=[Environment]::GetEnvironmentVariable($key,'Process') }
try {
    $env:PATH=(Split-Path -Parent $node)+[IO.Path]::PathSeparator+$env:PATH
    $env:PYTHONUTF8='1'
    $env:DJANGO_SETTINGS_MODULE='config.ai_local'
    $env:LAD_AI_RUNTIME=$runtime
    Remove-Item Env:LAD_AI_TEST -ErrorAction SilentlyContinue
    & $python (Join-Path $source 'tools/prepare-ai.py')
    if ($LASTEXITCODE -ne 0) { throw 'Existing AI runtime preparation failed.' }
    $logDir=Join-Path $runtime ('local-pc-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    $null=New-Item -ItemType Directory -Path $logDir
    $started=(Get-Date).ToString('o')
    $worker=Start-Process $node -ArgumentList 'integration/ai/worker.mjs' -WorkingDirectory $build -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'worker.stdout.log') -RedirectStandardError (Join-Path $logDir 'worker.stderr.log') -PassThru
    $startedChildren+=$worker
    $django=Start-Process $python -ArgumentList @('run-local-django.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory $build -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'django.stdout.log') -RedirectStandardError (Join-Path $logDir 'django.stderr.log') -PassThru
    $startedChildren+=$django
    $site=Start-Process $node -ArgumentList 'server.cjs' -WorkingDirectory $build -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'site.stdout.log') -RedirectStandardError (Join-Path $logDir 'site.stderr.log') -PassThru
    $startedChildren+=$site
    $headers=@{'X-LAD-IPC'=(Get-Content -LiteralPath (Join-Path $runtime 'ipc-secret.txt') -Raw).Trim()}
    $ready=$false
    for($i=0;$i -lt 30;$i++) {
        foreach($child in $startedChildren) { if($child.HasExited) { throw "New LAT AI child exited; see $logDir. Existing process record preserved." } }
        try {
            $null=Invoke-RestMethod 'http://127.0.0.1:8372/health' -Headers $headers -TimeoutSec 2
            $null=Invoke-WebRequest 'http://127.0.0.1:8000/admin/' -TimeoutSec 2
            $null=Invoke-WebRequest 'http://127.0.0.1:5173/' -TimeoutSec 2
            $ready=$true;break
        } catch { Start-Sleep -Milliseconds 300 }
    }
    if (-not $ready) { throw "Services did not become ready. See $logDir" }
    Assert-LatStartedServices -Children $startedChildren -ExpectedPorts @{5173=$site.Id;8000=$django.Id;8372=$worker.Id}
    $servicesVerified=$true
    @{worker=$worker.Id;django=$django.Id;site=$site.Id;started=$started;profile='this-pc';build=$build;logs=$logDir} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'processes.json') -Encoding UTF8
    if ($EnableModel) {
        & lms server start
        if ($LASTEXITCODE -ne 0) { throw 'LM Studio is unavailable.' }
        $null=Invoke-RestMethod 'http://127.0.0.1:8372/control' -Headers $headers -Method Post -ContentType 'application/json' -Body '{"action":"enable"}' -TimeoutSec 150
    }
    Write-Host ('Local PC profile: model '+$profile.model_budget_ms+' ms; worker '+$profile.worker_timeout_seconds+' s; browser '+$profile.browser_timeout_ms+' ms')
    Write-Host 'LAT AI: http://127.0.0.1:5173/#/courses'
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173/#/courses' }
} finally {
    if (-not $servicesVerified) {
        foreach($child in $startedChildren) {
            # Retain the actual Process object created by this launch. Never select a process by age.
            if (-not $child.HasExited) { Stop-Process -InputObject $child -Force -ErrorAction Continue }
        }
    }
    foreach ($key in $saved.Keys) { [Environment]::SetEnvironmentVariable($key,$saved[$key],'Process') }
}
} finally { $launchGuard.Dispose() }
