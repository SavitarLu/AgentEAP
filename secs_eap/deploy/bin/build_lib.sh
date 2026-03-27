#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
EAP_ROOT="$(cd "${DEPLOY_DIR}/.." && pwd)"
DRIVER_ROOT="$(cd "${EAP_ROOT}/../secs_driver" && pwd)"
LIB_DIR="${DEPLOY_DIR}/lib"

EAP_RUNTIME_ITEMS=(
  "__init__.py"
  "config"
  "driver_adapter.py"
  "eap.py"
  "mes"
  "message_handlers"
  "services"
  "usecases"
)

DRIVER_RUNTIME_ITEMS=(
  "src"
  "secsdriver_common"
)

if [[ ! -d "${DRIVER_ROOT}" ]]; then
  echo "secs_driver not found: ${DRIVER_ROOT}"
  exit 1
fi

copy_runtime_items() {
  local src_root="$1"
  local dst_root="$2"
  shift 2

  mkdir -p "${dst_root}"

  local item
  for item in "$@"; do
    if [[ ! -e "${src_root}/${item}" ]]; then
      echo "Skip missing runtime item: ${src_root}/${item}"
      continue
    fi

    rsync -a "${src_root}/${item}" "${dst_root}/" \
      --exclude ".DS_Store" \
      --exclude "__pycache__" \
      --exclude "*.pyc"
  done
}

echo "Preparing ${LIB_DIR} ..."
rm -rf "${LIB_DIR}"
mkdir -p "${LIB_DIR}"

echo "Copying secs_eap ..."
copy_runtime_items "${EAP_ROOT}" "${LIB_DIR}/secs_eap" "${EAP_RUNTIME_ITEMS[@]}"

echo "Copying secs_driver ..."
copy_runtime_items "${DRIVER_ROOT}" "${LIB_DIR}/secs_driver" "${DRIVER_RUNTIME_ITEMS[@]}"

find "${LIB_DIR}" -name ".DS_Store" -type f -delete

echo "Compiling .py -> .pyc ..."
python3 -m compileall -b "${LIB_DIR}/secs_eap" "${LIB_DIR}/secs_driver"

echo "Removing source .py files ..."
find "${LIB_DIR}" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "${LIB_DIR}" -name "*.py" -type f -delete

echo "Build complete."
echo "Runtime lib directory: ${LIB_DIR}"
