#!/bin/bash
# 切换到后端目录
cd "$(dirname "$0")/web_app/backend"

PYTHON_EXE="${LKYW_PYTHON_EXE:-/home/zhangboyu/anaconda3/envs/lkywSystem/bin/python}"
export LKYW_ULTRALYTICS_SOURCE="${LKYW_ULTRALYTICS_SOURCE:-/home/zhangboyu/SFGAYOLO26}"

if [ ! -x "$PYTHON_EXE" ]; then
    echo "错误: lkywSystem Python 不存在: $PYTHON_EXE"
    exit 1
fi

echo "正在启动 Python 后端服务..."
echo "API 地址: http://127.0.0.1:5000"
echo "Python: $PYTHON_EXE"
echo "Ultralytics: $LKYW_ULTRALYTICS_SOURCE"

# 检查依赖 (可选，如果已经安装可以注释掉)
# pip install -r requirements.txt -q

"$PYTHON_EXE" app.py
