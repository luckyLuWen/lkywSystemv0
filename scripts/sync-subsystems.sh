#!/bin/bash

# 遇到错误立即停止 (等同于 $ErrorActionPreference = 'Stop')
set -e

# 1. 设置路径
# 获取脚本所在目录，以及上一级目录 (等同于 Split-Path -Parent $PSScriptRoot)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PUBLIC_ROOT="${ROOT_DIR}/vue-project_all/public"

# 2. 辅助函数
reset_directory() {
  local target_path="$1"
  if [ -d "$target_path" ]; then
    rm -rf "$target_path"
  fi
  mkdir -p "$target_path"
}

copy_directory_contents() {
  local source_dir="$1"
  local target_dir="$2"

  if [ ! -d "$source_dir" ]; then
    echo "[ERROR] Source directory not found: $source_dir" >&2
    exit 1
  fi

  reset_directory "$target_dir"
  # 使用 cp -a 复制目录内所有内容（包含隐藏文件），并保持文件属性
  cp -a "$source_dir"/. "$target_dir"/
}

convert_vite_index_to_relative() {
  local index_path="$1"

  if [ ! -f "$index_path" ]; then
    echo "[ERROR] Entry file not found: $index_path" >&2
    exit 1
  fi

  # 使用 sed 进行原地字符串替换 (-i)
  sed -i 's|href="/assets/|href="./assets/|g' "$index_path"
  sed -i 's|src="/assets/|src="./assets/|g' "$index_path"
  sed -i 's|href="/vite.svg"|href="./vite.svg"|g' "$index_path"
}

# 3. 定义同步目标 (格式: "名称|源路径|类型")
TARGETS=(
  "collaborative-response|${ROOT_DIR}/Collaborative_Response/dist|vite"
  "constructive-simulation|${ROOT_DIR}/Constructive simulation|static"
  "realtime-detection|${ROOT_DIR}/Real-time_Detection/web_app/frontend/vue-frontend/dist|vite"
  "sensor-management|${ROOT_DIR}/Sensor_Management/IOT/frontend/dist|vite"
)

# 4. 执行同步
for target in "${TARGETS[@]}"; do
  # 解析字符串
  IFS='|' read -r name source type <<< "$target"
  
  destination="${PUBLIC_ROOT}/${name}"
  
  copy_directory_contents "$source" "$destination"

  if [ "$type" = "vite" ]; then
    convert_vite_index_to_relative "${destination}/index.html"
  fi
done

echo "Subsystem static assets synced."