$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'local-launch-guard.ps1')
$checks=0
function Must-Fail([scriptblock]$Action,[string]$Expected) {
    $caught=$false
    try { & $Action } catch { if(-not $_.Exception.Message.Contains($Expected)){throw};$caught=$true }
    if(-not $caught){throw "Expected failure: $Expected"}
}
$expected=@{5173=1;8000=2;8372=3}
$healthy=@([pscustomobject]@{HasExited=$false})
$ports={@([pscustomobject]@{LocalPort=5173;OwningProcess=1},[pscustomobject]@{LocalPort=8000;OwningProcess=2},[pscustomobject]@{LocalPort=8372;OwningProcess=3})}
Assert-LatStartedServices -Children $healthy -ExpectedPorts $expected -Reader $ports
$checks++
Must-Fail {Get-LatLaunchListeners -Reader {throw 'WMI port read failed'}} 'WMI port read failed';$checks++
Must-Fail {Assert-LatStartedServices -Children $healthy -ExpectedPorts $expected -Reader {@([pscustomobject]@{LocalPort=8372;OwningProcess=999})}} 'do not own';$checks++
Must-Fail {Assert-LatStartedServices -Children @([pscustomobject]@{HasExited=$true}) -ExpectedPorts $expected -Reader $ports} 'child exited';$checks++
$guardPath=Join-Path ([IO.Path]::GetTempPath()) ('lat-launch-test-'+[guid]::NewGuid()+'.lock')
$guard=Open-LatLaunchGuard $guardPath
try {Must-Fail {Open-LatLaunchGuard $guardPath} 'Another local launcher';$checks++}finally{$guard.Dispose()}
$again=Open-LatLaunchGuard $guardPath;$again.Dispose();$checks++
# This is our single test file, never a model lock or a lock selected by age.
Remove-Item -LiteralPath $guardPath
@{passed=$checks;scope='Mocked port discovery/occupied ports/child exit (database-lock startup symptom), real exclusive-file serialization. No services stopped or databases modified.'} | ConvertTo-Json
