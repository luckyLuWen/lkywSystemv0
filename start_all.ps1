# ===========================
# 协同响应系统 - 一键启动脚本 (PowerShell)
# ===========================
# 用法: .\start_all.ps1
# 优点: 支持同时监控两个进程, 自动端口检测, 优雅关闭

param(
    [switch]$DetachFrontend = $false,
    [switch]$DetachBackend = $false
)

$REPO_DIR = Split-Path -Parent $MyInvocation.MyCommandPath
$FRONTEND_DIR = Join-Path $REPO_DIR "Collaborative_Response"
$BACKEND_DIR = Join-Path $REPO_DIR "Collaborative_Response\backend\command_center"

Write-Host "===== 协同响应系统 - 一键启动 =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "前端目录: $FRONTEND_DIR" -ForegroundColor Gray
Write-Host "后端目录: $BACKEND_DIR" -ForegroundColor Gray
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
Write-Host "[SETUP] 检查前端依赖..." -ForegroundColor Yellow
Push-Location $FRONTEND_DIR
if (-not (Test-Path "node_modules")) {
    Write-Host "[INSTALL] 安装 npm 依赖..." -ForegroundColor Cyan
    & npm install
} else {
    Write-Host "[OK] 前端依赖已就位" -ForegroundColor Green
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

# ===== 启动进程 =====
Write-Host ""
Write-Host "[START] 启动后端服务..." -ForegroundColor Yellow
Push-Location $BACKEND_DIR

$backendCmd = "python -m streamlit run app_2d.py --server.port 8501 --server.headless false --logger.level=info"
if ($DetachBackend) {
    Start-Process -FilePath "python" -ArgumentList "-m streamlit run app_2d.py --server.port 8501 --server.headless false" -NoNewWindow -PassThru | Out-Null
    Write-Host "[OK] 后端已启动 (后台运行)" -ForegroundColor Green
} else {
    $backendProcess = Start-Process -FilePath "python" -ArgumentList "-m streamlit run app_2d.py --server.port 8501 --server.headless false" -PassThru -WindowStyle Normal
    Write-Host "[OK] 后端进程 ID: $($backendProcess.Id)" -ForegroundColor Green
}
Pop-Location

Write-Host ""
Write-Host "[START] 启动前端服务..." -ForegroundColor Yellow
Push-Location $FRONTEND_DIR
if ($DetachFrontend) {
    Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow -PassThru | Out-Null
    Write-Host "[OK] 前端已启动 (后台运行)" -ForegroundColor Green
} else {
    $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -PassThru -WindowStyle Normal
    Write-Host "[OK] 前端进程 ID: $($frontendProcess.Id)" -ForegroundColor Green
}
Pop-Location

# ===== 显示访问地址 =====
Write-Host ""
Write-Host "===== 系统已启动 =====" -ForegroundColor Green
Write-Host ""
Write-Host "📱 前端 (Vue DevServer):"
Write-Host "   http://127.0.0.1:5174" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 后端 (Streamlit):"
Write-Host "   http://127.0.0.1:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 提示:"
Write-Host "   - 同时关闭两个窗口以停止服务" -ForegroundColor Gray
Write-Host "   - 后台启动: .\start_all.ps1 -DetachFrontend -DetachBackend" -ForegroundColor Gray
Write-Host ""

# 保持窗口打开
Read-Host "按 Enter 键退出"
