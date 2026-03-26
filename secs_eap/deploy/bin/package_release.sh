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

if [[ ! -d "${DEPLOY_DIR}/lib" ]]; then
  echo "deploy/lib not found. Run: ./deploy/bin/build_lib.sh"
  exit 1
fi

mkdir -p "${RELEASE_DIR}"

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "${STAGE_DIR}"' EXIT

mkdir -p "${STAGE_DIR}/deploy"
cp -R "${DEPLOY_DIR}/bin" "${STAGE_DIR}/deploy/"
cp -R "${DEPLOY_DIR}/config" "${STAGE_DIR}/deploy/"
cp -R "${DEPLOY_DIR}/lib" "${STAGE_DIR}/deploy/"

if [[ ${INCLUDE_LOGS} -eq 1 ]]; then
  mkdir -p "${STAGE_DIR}/deploy/log"
  if [[ -d "${DEPLOY_DIR}/log" ]]; then
    cp -R "${DEPLOY_DIR}/log/." "${STAGE_DIR}/deploy/log/" || true
  fi
else
  mkdir -p "${STAGE_DIR}/deploy/log"
fi

tar -czf "${ARCHIVE_PATH}" -C "${STAGE_DIR}" deploy

echo "Package created: ${ARCHIVE_PATH}"
echo "Deploy steps:"
echo "  1) tar -xzf ${ARCHIVE_NAME}"
echo "  2) cd deploy"
echo "  3) ./bin/start.sh EQP001"
