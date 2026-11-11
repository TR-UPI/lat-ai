function Open-LatLaunchGuard([string]$Path) {
    # OS-held exclusive handle; no age-based stealing or deletion of locks.
    try { return [IO.File]::Open($Path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch { throw 'Another local launcher holds the guard, or guard access failed. No launch performed.' }
}
function Get-LatLaunchListeners([scriptblock]$Reader = { Get-NetTCPConnection -State Listen -ErrorAction Stop }) {
    $rows=@(& $Reader)
    return @($rows | Where-Object { $_.LocalPort -in @(5173,8000,8372) })
}
function Assert-LatStartedServices([object[]]$Children,[hashtable]$ExpectedPorts,[scriptblock]$Reader = { Get-NetTCPConnection -State Listen -ErrorAction Stop }) {
    foreach($child in $Children) {
        if($child.HasExited) { throw 'A newly started LAT AI child exited; inspect its log (including possible database lock). Existing process record is preserved.' }
    }
    $listeners=@(Get-LatLaunchListeners -Reader $Reader)
    foreach($port in $ExpectedPorts.Keys) {
        $owners=@($listeners | Where-Object { $_.LocalPort -eq $port })
        if($owners.Count -ne 1 -or $owners[0].OwningProcess -ne $ExpectedPorts[$port]) { throw 'New services do not own every expected port. Existing process record is preserved.' }
    }
}
