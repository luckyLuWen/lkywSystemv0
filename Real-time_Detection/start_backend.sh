#!/bin/bash
# 切换到后端目录
cd "$(dirname "$0")/web_app/backend"

echo "正在启动 Python 后端服务..."
echo "API 地址: http://127.0.0.1:5000"

# 检查依赖 (可选，如果已经安装可以注释掉)
# pip install -r requirements.txt -q

python app.py
