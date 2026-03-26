#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -d "${DEPLOY_DIR}/config" ]]; then
  printf "%-16s %-10s %-20s\n" "EQPID" "STATUS" "PIDS"
  missing=1
  for cfg in "${DEPLOY_DIR}"/config/*.yaml; do
    [[ -e "${cfg}" ]] || continue
    base="$(basename "${cfg}" .yaml)"
    [[ "${base}" == "eap" ]] && continue
    pids="$(pgrep -f "run_eap.py ${base}" || true)"
    if [[ -n "${pids}" ]]; then
      one_line_pids="$(echo "${pids}" | tr '\n' ',' | sed 's/,$//')"
      printf "%-16s %-10s %-20s\n" "${base}" "RUNNING" "${one_line_pids}"
      missing=0
    else
      printf "%-16s %-10s %-20s\n" "${base}" "STOPPED" "-"
    fi
  done
  if [[ ${missing} -eq 1 ]]; then
    echo "No running instances."
  fi
else
  echo "Config directory not found: ${DEPLOY_DIR}/config"
fi
