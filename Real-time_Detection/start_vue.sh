#!/bin/bash
# 切换到 Vue 前端目录
cd "$(dirname "$0")/web_app/frontend/vue-frontend"

echo "正在检查依赖..."
if [ ! -d "node_modules" ]; then
    echo "未发现 node_modules，正在安装依赖..."
    npm install
fi

echo "🚀 正在启动 Vue 前端开发服务器..."
echo "后端地址设定为: http://127.0.0.1:5000"
npm run dev
