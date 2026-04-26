param()

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

  $content = Get-Content -LiteralPath $IndexPath -Raw
  $content = $content.Replace('href="/assets/', 'href="./assets/')
  $content = $content.Replace('src="/assets/', 'src="./assets/')
  $content = $content.Replace('href="/vite.svg"', 'href="./vite.svg"')
  Set-Content -LiteralPath $IndexPath -Value $content -Encoding UTF8
}

$targets = @(
   @{
    Name = 'constructive-simulation'
    Source = Join-Path $root 'Constructive simulation'
    Type = 'static'
  },
  @{
    Name = 'realtime-detection'
    Source = Join-Path $root 'Real-time_Detection\web_app\frontend'
    Type = 'static'
  },
  @{
    Name = 'sensor-management'
    Source = Join-Path $root 'Sensor_Management\IOT\frontend\dist'
    Type = 'vite'
  }
)

foreach ($target in $targets) {
  $destination = Join-Path $publicRoot $target.Name
  Copy-DirectoryContents -Source $target.Source -Target $destination

  if ($target.Type -eq 'vite') {
    Convert-ViteIndexToRelative -IndexPath (Join-Path $destination 'index.html')
  }
}

Write-Host 'Subsystem static assets synced.'
