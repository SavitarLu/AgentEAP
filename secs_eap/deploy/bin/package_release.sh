#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${DEPLOY_DIR}/.." && pwd)"
RELEASE_DIR="${PROJECT_ROOT}/release"
STAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="secs_eap_deploy_${STAMP}.tar.gz"
ARCHIVE_PATH="${RELEASE_DIR}/${ARCHIVE_NAME}"

INCLUDE_LOGS=0
if [[ "${1:-}" == "--with-logs" ]]; then
  INCLUDE_LOGS=1
fi

echo "Step 1/4: clean deploy/lib ..."
"${SCRIPT_DIR}/clean_lib.sh"

echo "Step 2/4: rebuild deploy/lib ..."
"${SCRIPT_DIR}/build_lib.sh"

mkdir -p "${RELEASE_DIR}"
echo "Step 3/4: clear release directory ..."
find "${RELEASE_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "${STAGE_DIR}"' EXIT

echo "Step 4/4: package release ..."
mkdir -p "${STAGE_DIR}/deploy"
rsync -a "${DEPLOY_DIR}/bin/" "${STAGE_DIR}/deploy/bin/" --exclude ".DS_Store"
rsync -a "${DEPLOY_DIR}/config/" "${STAGE_DIR}/deploy/config/" --exclude ".DS_Store"
rsync -a "${DEPLOY_DIR}/lib/" "${STAGE_DIR}/deploy/lib/" --exclude ".DS_Store"

if [[ ${INCLUDE_LOGS} -eq 1 ]]; then
  mkdir -p "${STAGE_DIR}/deploy/log"
  if [[ -d "${DEPLOY_DIR}/log" ]]; then
    rsync -a "${DEPLOY_DIR}/log/" "${STAGE_DIR}/deploy/log/" --exclude ".DS_Store" || true
  fi
else
  mkdir -p "${STAGE_DIR}/deploy/log"
fi

tar -czf "${ARCHIVE_PATH}" -C "${STAGE_DIR}" deploy

echo "Package created: ${ARCHIVE_PATH}"
echo "Deploy steps:"
echo "  1) tar -xzf ${ARCHIVE_NAME}"
echo "  2) cd deploy"
echo "  3) ./bin/start.sh E_CLN_01"
