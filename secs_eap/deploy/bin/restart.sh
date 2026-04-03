#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EQPID="${1:-}"

if [[ -z "${EQPID}" ]]; then
  echo "Usage: $0 EQPID"
  exit 1
fi

"${SCRIPT_DIR}/stop.sh" "${EQPID}" || true
sleep 5
"${SCRIPT_DIR}/start.sh" "${EQPID}"
