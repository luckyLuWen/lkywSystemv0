param(
  [string[]]$TargetName = @()
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$publicRoot = Join-Path $root 'vue-project_all\public'

function Reset-Directory {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  if (Test-Path -LiteralPath $Path) {
    Remove-Item -LiteralPath $Path -Recurse -Force
  }

  New-Item -ItemType Directory -Path $Path | Out-Null
}

function Copy-DirectoryContents {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [Parameter(Mandatory = $true)]
    [string]$Target
  )

  if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source directory not found: $Source"
  }

  Reset-Directory -Path $Target
  Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Target -Recurse -Force
  }
}

function Convert-ViteIndexToRelative {
  param(
    [Parameter(Mandatory = $true)]
    [string]$IndexPath
  )

  if (-not (Test-Path -LiteralPath $IndexPath)) {
    throw "Entry file not found: $IndexPath"
  }

  $utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false, $true
  $content = [System.IO.File]::ReadAllText($IndexPath, $utf8)
  $content = $content.Replace('href="/assets/', 'href="./assets/')
  $content = $content.Replace('src="/assets/', 'src="./assets/')
  $content = $content.Replace('href="/vite.svg"', 'href="./vite.svg"')
  [System.IO.File]::WriteAllText($IndexPath, $content, $utf8)
}

$targets = @(
  @{
    Name = 'collaborative-response'
    Source = Join-Path $root 'Collaborative_Response\dist'
    Type = 'vite'
  },
  @{
    Name = 'constructive-simulation'
    Source = Join-Path $root 'Constructive simulation'
    Type = 'static'
  },
  @{
    Name = 'realtime-detection'
    Source = Join-Path $root 'Real-time_Detection\web_app\frontend\vue-frontend\dist'
    Type = 'vite'
  },
  @{
    Name = 'sensor-management'
    Source = Join-Path $root 'Sensor_Management\IOT\frontend\dist'
    Type = 'vite'
  }
)

if ($TargetName.Count -gt 0) {
  $knownTargetNames = $targets | ForEach-Object { $_.Name }
  foreach ($name in $TargetName) {
    if ($knownTargetNames -notcontains $name) {
      throw "Unknown target '$name'. Known targets: $($knownTargetNames -join ', ')"
    }
  }

  $targets = $targets | Where-Object { $TargetName -contains $_.Name }
}

foreach ($target in $targets) {
  $destination = Join-Path $publicRoot $target.Name
  Copy-DirectoryContents -Source $target.Source -Target $destination

  if ($target.Type -eq 'vite') {
    Convert-ViteIndexToRelative -IndexPath (Join-Path $destination 'index.html')
  }

  Write-Host "Synced $($target.Name)."
}

Write-Host 'Subsystem static assets synced.'
