#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${DEPLOY_DIR}/log"
PROJECT_DIR="$(cd "${DEPLOY_DIR}/.." && pwd)"
VENV_PY="${PROJECT_DIR}/.venv/bin/python3"
PY_BIN="python3"
if [[ -x "${VENV_PY}" ]]; then
  PY_BIN="${VENV_PY}"
fi
EQPID="${1:-}"

if [[ -z "${EQPID}" ]]; then
  echo "Usage: $0 EQPID"
  exit 1
fi

CONFIG_FILE="${DEPLOY_DIR}/config/${EQPID}.yaml"
if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Config not found: ${CONFIG_FILE}"
  exit 1
fi

CONSOLE_LOG="${LOG_DIR}/console-${EQPID}-$(date +%F).log"

mkdir -p "${LOG_DIR}"

if pgrep -f "run_eap.py ${EQPID}" >/dev/null 2>&1; then
  echo "EAP ${EQPID} already running."
  exit 0
fi

nohup "${PY_BIN}" "${SCRIPT_DIR}/run_eap.py" "${EQPID}" >> "${CONSOLE_LOG}" 2>&1 &
echo "EAP ${EQPID} started."
