#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PUBLIC_ROOT="${ROOT_DIR}/vue-project_all/public"

TARGET_NAMES=("$@")

assert_target_inside_public_root() {
  local target_path="$1"
  local public_root_real
  local target_parent
  local target_real

  public_root_real="$(cd "$PUBLIC_ROOT" && pwd -P)"
  target_parent="$(dirname "$target_path")"
  mkdir -p "$target_parent"
  target_real="$(cd "$target_parent" && pwd -P)/$(basename "$target_path")"

  case "$target_real" in
    "$public_root_real"/*) ;;
    *)
      echo "[ERROR] Refusing to reset directory outside public root: $target_path" >&2
      exit 1
      ;;
  esac
}

reset_directory() {
  local target_path="$1"

  assert_target_inside_public_root "$target_path"

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
  cp -a "$source_dir"/. "$target_dir"/
}

convert_vite_index_to_relative() {
  local index_path="$1"

  if [ ! -f "$index_path" ]; then
    echo "[ERROR] Entry file not found: $index_path" >&2
    exit 1
  fi

  sed -i 's|href="/assets/|href="./assets/|g' "$index_path"
  sed -i 's|src="/assets/|src="./assets/|g' "$index_path"
  sed -i 's|href="/vite.svg"|href="./vite.svg"|g' "$index_path"
}

TARGETS=(
  "collaborative-response|${ROOT_DIR}/Collaborative_Response/dist|vite"
  "constructive-simulation|${ROOT_DIR}/Constructive simulation|static"
  "realtime-detection|${ROOT_DIR}/Real-time_Detection/web_app/frontend/vue-frontend/dist|vite"
  "sensor-management|${ROOT_DIR}/Sensor_Management/IOT/frontend/dist|vite"
)

is_known_target() {
  local expected_name="$1"
  local target
  local name
  local source
  local type

  for target in "${TARGETS[@]}"; do
    IFS='|' read -r name source type <<< "$target"
    if [ "$name" = "$expected_name" ]; then
      return 0
    fi
  done

  return 1
}

should_sync_target() {
  local name="$1"
  local selected

  if [ "${#TARGET_NAMES[@]}" -eq 0 ]; then
    return 0
  fi

  for selected in "${TARGET_NAMES[@]}"; do
    if [ "$selected" = "$name" ]; then
      return 0
    fi
  done

  return 1
}

if [ "${#TARGET_NAMES[@]}" -gt 0 ]; then
  for target_name in "${TARGET_NAMES[@]}"; do
    if ! is_known_target "$target_name"; then
      echo "[ERROR] Unknown target '${target_name}'." >&2
      echo "[ERROR] Known targets: collaborative-response, constructive-simulation, realtime-detection, sensor-management" >&2
      exit 1
    fi
  done
fi

for target in "${TARGETS[@]}"; do
  IFS='|' read -r name source type <<< "$target"

  if ! should_sync_target "$name"; then
    continue
  fi

  destination="${PUBLIC_ROOT}/${name}"

  copy_directory_contents "$source" "$destination"

  if [ "$type" = "vite" ]; then
    convert_vite_index_to_relative "${destination}/index.html"
  fi

  echo "Synced ${name}."
done

echo "Subsystem static assets synced."
