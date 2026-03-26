#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_DIR="${DEPLOY_DIR}/lib"
BUILD_DIR="${DEPLOY_DIR}/.build"
LOG_DIR="${DEPLOY_DIR}/log"

REMOVE_LOGS=0
if [[ "${1:-}" == "--logs" ]]; then
  REMOVE_LOGS=1
fi

if [[ -d "${LIB_DIR}" ]]; then
  rm -rf "${LIB_DIR}"
  echo "Removed: ${LIB_DIR}"
else
  echo "Skip (not found): ${LIB_DIR}"
fi

if [[ -d "${BUILD_DIR}" ]]; then
  rm -rf "${BUILD_DIR}"
  echo "Removed: ${BUILD_DIR}"
else
  echo "Skip (not found): ${BUILD_DIR}"
fi

if [[ ${REMOVE_LOGS} -eq 1 ]]; then
  if [[ -d "${LOG_DIR}" ]]; then
    rm -rf "${LOG_DIR:?}/"*
    echo "Removed logs under: ${LOG_DIR}"
  else
    echo "Skip (not found): ${LOG_DIR}"
  fi
fi

echo "Clean completed."
