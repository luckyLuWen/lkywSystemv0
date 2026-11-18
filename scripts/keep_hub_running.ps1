$repo = Split-Path $PSScriptRoot -Parent
$pythonExe = $env:LKYW_PYTHON_EXE
if (-not $pythonExe) { $pythonExe = 'D:\Miniconda\envs\layolo_traffic_dev\python.exe' }
if (-not (Test-Path $pythonExe)) { $pythonExe = (Get-Command python -ErrorAction Stop).Source }
$port = 18701
if ($env:INTEGRATION_HUB_PORT) { $port = [int]$env:INTEGRATION_HUB_PORT }
$mutex = New-Object System.Threading.Mutex($false, "Local\LKYW-Hub-$port")
if (-not $mutex.WaitOne(0)) { exit }
$logs = Join-Path $repo 'artifacts'
New-Item -ItemType Directory -Force $logs | Out-Null
try {
 while ($true) {
  $client = New-Object System.Net.Sockets.TcpClient
  try { $client.Connect('127.0.0.1', $port); $running = $true } catch { $running = $false } finally { $client.Dispose() }
  if ($running) { Start-Sleep 5; continue }
  Add-Content "$logs\hub-supervisor.log" "$(Get-Date -Format o) Starting Hub"
  $env:PYTHONIOENCODING = 'utf-8'
  & $pythonExe -u "$repo\Integration_Hub\server.py" >> "$logs\hub-output.log" 2>> "$logs\hub-error.log"
  Add-Content "$logs\hub-supervisor.log" "$(Get-Date -Format o) Exited: $LASTEXITCODE; restart in 5 seconds"
  Start-Sleep 5
 }
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
