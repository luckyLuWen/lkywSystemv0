# ===========================
# 协同响应系统 - 一键启动脚本 (PowerShell)
# ===========================
# 用法: .\start_all.ps1

param(
    [switch]$DetachFrontend = $false,
    [switch]$DetachBackend = $false
)

$REPO_DIR = Split-Path -Parent $MyInvocation.MyCommandPath
$MAIN_APP_DIR = Join-Path $REPO_DIR "vue-project_all"
$BACKEND_DIR = Join-Path $REPO_DIR "Collaborative_Response\backend\command_center"

Write-Host "===== 协同响应系统 - 一键启动 =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "主应用目录: $MAIN_APP_DIR" -ForegroundColor Gray
Write-Host "后端目录:   $BACKEND_DIR" -ForegroundColor Gray
Write-Host ""

# ===== 检查依赖 =====
Write-Host "[CHECK] 检测 Node.js..." -ForegroundColor Yellow
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "[ERROR] Node.js 未安装" -ForegroundColor Red
    exit 1
}
$nodeVersion = & node --version
Write-Host "[OK] $nodeVersion" -ForegroundColor Green

Write-Host "[CHECK] 检测 Python..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python 未安装" -ForegroundColor Red
    exit 1
}
$pythonVersion = & python --version 2>&1
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# ===== 检查并安装依赖 =====
Write-Host ""
Write-Host "[SETUP] 检查主应用依赖..." -ForegroundColor Yellow
Push-Location $MAIN_APP_DIR
if (-not (Test-Path "node_modules")) {
    Write-Host "[INSTALL] 安装 npm 依赖 (仅首次)..." -ForegroundColor Cyan
    & npm install
} else {
    Write-Host "[OK] 主应用依赖已就位" -ForegroundColor Green
}
Pop-Location

Write-Host "[SETUP] 检查后端依赖..." -ForegroundColor Yellow
Push-Location $BACKEND_DIR
if (Test-Path "requirements.txt") {
    $streamlit = & pip list 2>&1 | Select-String "streamlit"
    if (-not $streamlit) {
        Write-Host "[INSTALL] 安装 Python 依赖..." -ForegroundColor Cyan
        & python -m pip install -q -r requirements.txt
    } else {
        Write-Host "[OK] 后端依赖已就位" -ForegroundColor Green
    }
}
Pop-Location

# ===== 智能检测端口 =====
Write-Host ""
Write-Host "[DETECT] 检测服务状态..." -ForegroundColor Yellow

$backendRunning = $false
$frontendRunning = $false

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5001/api/health" -TimeoutSec 2 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] 后端已在运行 (端口 5001)" -ForegroundColor Green
        $backendRunning = $true
    }
} catch {
    Write-Host "[--] 后端未运行" -ForegroundColor Gray
}

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] 前端已在运行 (端口 5173)" -ForegroundColor Green
        $frontendRunning = $true
    }
} catch {
    Write-Host "[--] 前端未运行" -ForegroundColor Gray
}

# ===== 启动后端 =====
if ($backendRunning) {
    Write-Host ""
    Write-Host "[1/3] 后端已运行, 跳过启动" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "[1/3] 启动后端服务 (端口 5001)..." -ForegroundColor Yellow
    Push-Location $BACKEND_DIR
    if ($DetachBackend) {
        Start-Process -FilePath "python" -ArgumentList "server.py" -NoNewWindow -PassThru | Out-Null
        Write-Host "[OK] 后端已启动 (后台运行)" -ForegroundColor Green
    } else {
        $backendProcess = Start-Process -FilePath "python" -ArgumentList "server.py" -PassThru -WindowStyle Normal
        Write-Host "[OK] 后端进程 ID: $($backendProcess.Id)" -ForegroundColor Green
    }
    Pop-Location
    Write-Host "[OK] 等待后端初始化 (3s)..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
}

# ===== 启动前端 =====
if ($frontendRunning) {
    Write-Host ""
    Write-Host "[2/3] 前端已运行, 跳过启动" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "[2/3] 启动主应用前端 (端口 5173)..." -ForegroundColor Yellow
    Push-Location $MAIN_APP_DIR
    if ($DetachFrontend) {
        Start-Process -FilePath "npx" -ArgumentList "vite","--port","5173","--host" -NoNewWindow -PassThru | Out-Null
        Write-Host "[OK] 前端已启动 (后台运行)" -ForegroundColor Green
    } else {
        $frontendProcess = Start-Process -FilePath "npx" -ArgumentList "vite","--port","5173","--host" -PassThru -WindowStyle Normal
        Write-Host "[OK] 前端进程 ID: $($frontendProcess.Id)" -ForegroundColor Green
    }
    Pop-Location
    Write-Host "[OK] 等待前端编译 (6s)..." -ForegroundColor Gray
    Start-Sleep -Seconds 6
}

# ===== 打开浏览器 =====
$coordUrl = "http://localhost:5173/coordination"
Write-Host ""
Write-Host "[3/3] 正在打开浏览器..." -ForegroundColor Cyan
Start-Process $coordUrl

# ===== 显示地址 =====
Write-Host ""
Write-Host "===== 系统已启动 =====" -ForegroundColor Green
Write-Host ""
Write-Host "协同响应面板: $coordUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "指挥后端 API:   http://127.0.0.1:5001" -ForegroundColor Cyan
Write-Host "健康检查:       http://127.0.0.1:5001/api/health" -ForegroundColor Cyan
Write-Host "协同调度 (Streamlit): http://127.0.0.1:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "提示:" -ForegroundColor Gray
Write-Host "  - Streamlit 可通过前端面板一键启动/停止" -ForegroundColor Gray
Write-Host "  - 同时关闭后端和前端窗口以停止服务" -ForegroundColor Gray
Write-Host "  - 后台运行: .\start_all.ps1 -DetachFrontend -DetachBackend" -ForegroundColor Gray
Write-Host ""

Read-Host "按 Enter 键退出"
