#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EQPID="${1:-}"

if [[ -z "${EQPID}" ]]; then
  echo "Usage: $0 EQPID"
  exit 1
fi

PIDS="$(pgrep -f "run_eap.py ${EQPID}" || true)"
if [[ -z "${PIDS}" ]]; then
  echo "EAP ${EQPID} is not running."
  exit 0
fi

for pid in ${PIDS}; do
  kill "${pid}" || true
done

echo "EAP ${EQPID} stopped."
