#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
EAP_ROOT="$(cd "${DEPLOY_DIR}/.." && pwd)"
DRIVER_ROOT="$(cd "${EAP_ROOT}/../secs_driver" && pwd)"
LIB_DIR="${DEPLOY_DIR}/lib"

if [[ ! -d "${DRIVER_ROOT}" ]]; then
  echo "secs_driver not found: ${DRIVER_ROOT}"
  exit 1
fi

echo "Preparing ${LIB_DIR} ..."
rm -rf "${LIB_DIR}"
mkdir -p "${LIB_DIR}"

echo "Copying secs_eap ..."
rsync -a "${EAP_ROOT}/" "${LIB_DIR}/secs_eap/" \
  --exclude "deploy" \
  --exclude "tests" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc"

echo "Copying secs_driver ..."
rsync -a "${DRIVER_ROOT}/" "${LIB_DIR}/secs_driver/" \
  --exclude "tests" \
  --exclude "java_gui" \
  --exclude "__pycache__" \
  --exclude "*.pyc"

echo "Compiling .py -> .pyc ..."
python3 -m compileall -b "${LIB_DIR}/secs_eap" "${LIB_DIR}/secs_driver"

echo "Removing source .py files ..."
find "${LIB_DIR}" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "${LIB_DIR}" -name "*.py" -type f -delete

echo "Build complete."
echo "Runtime lib directory: ${LIB_DIR}"
