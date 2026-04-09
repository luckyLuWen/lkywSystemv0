@echo off
chcp 65001 >nul
color 0A
echo ========================================
echo    GitHub 快速上传脚本
echo ========================================
echo.

REM 检查是否已安装Git
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Git，请先安装Git
    echo.
    echo 下载地址: https://git-scm.com/download/win
    echo.
    pause
    exit /b
)

echo ✓ Git已安装
echo.

REM 检查是否已初始化Git仓库
if not exist .git (
    echo [步骤 1/5] 初始化Git仓库...
    git init
    echo ✓ 完成
    echo.
) else (
    echo ✓ Git仓库已存在
    echo.
)

echo [步骤 2/5] 配置Git用户信息...
echo.
set /p username="请输入你的GitHub用户名: "
set /p email="请输入你的邮箱: "

git config user.name "%username%"
git config user.email "%email%"
echo ✓ 完成
echo.

echo [步骤 3/5] 添加文件到Git...
git add .
echo ✓ 完成
echo.

echo [步骤 4/5] 提交更改...
git commit -m "Initial commit: 两客一危火灾检测系统"
echo ✓ 完成
echo.

echo [步骤 5/5] 关联远程仓库...
echo.
echo 请先在GitHub上创建一个新仓库，然后输入仓库地址
echo 格式: https://github.com/你的用户名/仓库名.git
echo.
set /p repo_url="请输入GitHub仓库地址: "

git remote add origin %repo_url%
git branch -M main

echo.
echo ========================================
echo 准备推送到GitHub...
echo ========================================
echo.
echo 如果提示输入密码，请使用Personal Access Token
echo 获取Token: GitHub → Settings → Developer settings → Personal access tokens
echo.
pause

git push -u origin main

if errorlevel 1 (
    echo.
    echo ❌ 推送失败
    echo.
    echo 可能的原因：
    echo   1. 仓库地址错误
    echo   2. 没有权限
    echo   3. 文件太大
    echo.
    echo 请查看错误信息，或参考 GitHub上传指南.md
    echo.
) else (
    echo.
    echo ========================================
    echo ✅ 上传成功！
    echo ========================================
    echo.
    echo 你的项目已成功上传到GitHub
    echo 仓库地址: %repo_url%
    echo.
    echo 下次更新代码时，使用以下命令：
    echo   git add .
    echo   git commit -m "更新说明"
    echo   git push
    echo.
)

pause
