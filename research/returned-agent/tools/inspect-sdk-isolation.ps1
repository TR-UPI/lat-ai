param([Parameter(Mandatory=$true)][string]$NewOutput)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$target=[IO.Path]::GetFullPath((Join-Path $root $NewOutput))
if (-not $target.StartsWith(([IO.Path]::GetFullPath((Join-Path $root 'outputs'))+[IO.Path]::DirectorySeparatorChar))) { throw 'Output must be under workspace outputs' }
if (Test-Path -LiteralPath $target) { throw 'Evidence output already exists' }
$os=Get-CimInstance Win32_OperatingSystem
$processes=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(LM Studio|llmster|llm-engine|lms)\.exe$' } | ForEach-Object {
    [ordered]@{pid=$_.ProcessId;parent_pid=$_.ParentProcessId;name=$_.Name;executable=$_.ExecutablePath;created_utc=$_.CreationDate.ToUniversalTime().ToString('o')}
})
$listeners=@(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 1234 -or $_.OwningProcess -in $processes.pid } | Select-Object LocalAddress,LocalPort,OwningProcess)
$settings='E:/Horror game/LocalAI/lmstudio-home/settings.json'
$serverInfo='E:/Horror game/LocalAI/lmstudio-home/.internal/http-server.json'
$metadata=@{}
foreach($path in @($settings,$serverInfo)) { if(Test-Path -LiteralPath $path){$metadata[$path]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()} }
$data=[ordered]@{
    captured_utc=[DateTime]::UtcNow.ToString('o');scope='READ_ONLY_RUNTIME_ISOLATION_INVENTORY';
    free_physical_bytes=([int64]$os.FreePhysicalMemory*1024);total_physical_bytes=([int64]$os.TotalVisibleMemorySize*1024);
    runtime_processes=$processes;runtime_listeners=$listeners;shared_settings_sha256=$metadata;
    daemon_install_record_present=(Test-Path -LiteralPath 'E:/Horror game/LocalAI/lmstudio-home/.internal/llmster-install-location.json');
    docker_command_present=($null -ne (Get-Command docker -ErrorAction SilentlyContinue));
    desktop_version=(Get-Content -Raw -LiteralPath 'E:/AI model/LM Studio/resources/app/package.json' | ConvertFrom-Json).version;
    shared_models=(Invoke-RestMethod -Uri 'http://127.0.0.1:1234/api/v1/models' -TimeoutSec 5);
    load_unload_inference_calls=0;processes_started_or_stopped=0
}
$json=$data | ConvertTo-Json -Depth 20
$stream=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json+"`n");$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
[ordered]@{output=$target;free_physical_bytes=$data.free_physical_bytes;runtime_count=$processes.Count;daemon_install_record_present=$data.daemon_install_record_present;model_mutations=0}|ConvertTo-Json
