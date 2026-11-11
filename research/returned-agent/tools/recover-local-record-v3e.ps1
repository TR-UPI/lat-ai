# One-time recovery of the recorded, proven LAT AI processes after a failed sandbox launch.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$runtime=Join-Path $root 'lat-ai/.runtime/i02'
$report=Join-Path $root 'outputs/ai-continuation-2026-11-11'
$expected=@{8372=28456;8000=4820;5173=22728}
$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$_.LocalPort -in $expected.Keys})
if($listeners.Count -ne 3){throw 'Listener set changed; no recovery performed'}
foreach($listener in $listeners){if($listener.OwningProcess -ne $expected[[int]$listener.LocalPort]){throw 'Listener owner changed'}}
$proof=@()
foreach($processId in @(28456,4820,22728)){
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
 $exe=if($processId -eq 4820){Join-Path $root 'work/lat-ai-runtime/python/python.exe'}else{Join-Path $root 'work/lat-ai-runtime/node/node.exe'}
 $needle=switch($processId){28456 {'integration/ai/worker.mjs'} 4820 {'runserver 127.0.0.1:8000'} 22728 {'server.cjs'}}
 if(-not $proc -or $proc.ExecutablePath -ine $exe -or -not $proc.CommandLine.Contains($needle) -or [math]::Abs(($proc.CreationDate-[datetime]'2026-11-11T06:26:23+05:00').TotalSeconds) -gt 2){throw 'Process identity changed'}
 $proof+=$proc | Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate
}
$proof | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $report 'process-ownership-proof.json') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $runtime 'processes.json') -Destination (Join-Path $report 'failed-launch-process-record.json')
$failed=Get-CimInstance Win32_Process -Filter 'ProcessId=17220'
if($failed){
 if($failed.ExecutablePath -ine (Join-Path $root 'work/lat-ai-runtime/python/python.exe') -or -not $failed.CommandLine.Contains('runserver 127.0.0.1:8000') -or [math]::Abs(($failed.CreationDate-[datetime]'2026-11-11T06:39:09+05:00').TotalSeconds) -gt 2){throw 'Failed-launch child identity changed'}
 Stop-Process -Id 17220 -Force -ErrorAction Stop
}
@{worker=28456;django=4820;site=22728;started='2026-11-11T06:26:22.830+05:00';profile='this-pc';build=(Join-Path $root 'work/local-pc/builds/20261111-062618-552038');logs=(Join-Path $runtime 'local-pc-20261111-062622-824')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'processes.json') -Encoding utf8
Write-Output 'Recorded ownership restored; normal launcher must still verify ownership, idle status and retirement before stopping anything.'
