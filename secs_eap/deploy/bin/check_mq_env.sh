#!/usr/bin/env bash
# check_mq_env.sh — verify IBM MQ Python environment is ready
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok=0
warn=0
fail=0

pass()  { ((ok++));   echo -e "  ${GREEN}[OK]${NC}   $1"; }
skip()  { ((warn++)); echo -e "  ${YELLOW}[WARN]${NC} $1"; }
error() { ((fail++)); echo -e "  ${RED}[FAIL]${NC} $1"; }

echo "===== IBM MQ Environment Check ====="
echo ""

# 0. Architecture
echo "0) Architecture"
os_arch="$(uname -m 2>/dev/null || true)"
py_arch="$(python3 -c "import platform; print(platform.machine())" 2>/dev/null || true)"
if [ -n "$os_arch" ]; then
    pass "OS arch=$os_arch"
else
    skip "Unable to read OS architecture"
fi
if [ -n "$py_arch" ]; then
    pass "Python arch=$py_arch"
else
    skip "Unable to read Python architecture"
fi
if [ -n "$os_arch" ] && [ -n "$py_arch" ] && [ "$os_arch" != "$py_arch" ]; then
    skip "OS/Python arch mismatch (Rosetta scenario). MQ client and Python must use same arch."
fi

# 1. Python3
echo "1) Python3"
if command -v python3 &>/dev/null; then
    ver=$(python3 --version 2>&1)
    pass "$ver"
else
    error "python3 not found in PATH"
fi

# 2. ibmmq
echo "2) ibmmq (official Python MQ client library)"
if python3 -c "import ibmmq; print(f'ibmmq {getattr(ibmmq, \"__version__\", \"unknown\")}')" 2>/dev/null; then
    pass "ibmmq imported OK"
else
    error "ibmmq not installed — run: pip install ibmmq"
fi

# 3. IBM MQ Client (libmqic / MQ_HOME)
echo "3) IBM MQ Client runtime"
MQ_HOME="${MQ_HOME:-}"
if [ -n "$MQ_HOME" ] && [ -d "$MQ_HOME" ]; then
    pass "MQ_HOME=$MQ_HOME"
elif [ -d "/opt/mqm" ]; then
    pass "Found /opt/mqm (default MQ install path)"
    MQ_HOME="/opt/mqm"
elif [ -d "/usr/local/opt/ibm-mq-client" ]; then
    pass "Found /usr/local/opt/ibm-mq-client (Homebrew)"
    MQ_HOME="/usr/local/opt/ibm-mq-client"
else
    skip "MQ_HOME not set and default paths not found (/opt/mqm, /usr/local/opt/ibm-mq-client)"
fi

# 4. libmqic shared library
echo "4) libmqic shared library"
found_lib=false
for dir in "${MQ_HOME}/lib64" "${MQ_HOME}/lib" "/opt/mqm/lib64" "/opt/mqm/lib"; do
    if [ -d "$dir" ]; then
        for ext in so dylib; do
            if ls "$dir"/libmqic*."$ext" 2>/dev/null | head -1 >/dev/null; then
                pass "Found in $dir"
                found_lib=true
                break 2
            fi
        done
    fi
done
if ! $found_lib; then
    skip "libmqic not found — ibmmq may still work if LD_LIBRARY_PATH / DYLD_LIBRARY_PATH is set"
fi

# 5. MQ header files (may be required when building ibmmq from source)
echo "5) MQ header files (cmqc.h)"
found_header=false
for dir in "${MQ_HOME}/inc" "/opt/mqm/inc"; do
    if [ -f "$dir/cmqc.h" ]; then
        pass "Found $dir/cmqc.h"
        found_header=true
        break
    fi
done
if ! $found_header; then
    error "cmqc.h not found — install IBM MQ Client SDK / Development headers"
fi

# 6. LD_LIBRARY_PATH / DYLD_LIBRARY_PATH
echo "6) Library path env"
case "$(uname -s)" in
    Darwin*)
        val="${DYLD_LIBRARY_PATH:-}"
        var="DYLD_LIBRARY_PATH"
        ;;
    *)
        val="${LD_LIBRARY_PATH:-}"
        var="LD_LIBRARY_PATH"
        ;;
esac
if [ -n "$val" ]; then
    pass "$var=$val"
else
    skip "$var is not set (may be needed if MQ libs are in a non-standard path)"
fi

# 7. Quick connectivity smoke test (optional)
echo "7) ibmmq CMQC constants"
if python3 -c "from ibmmq import CMQC; print(f'MQGMO_WAIT={CMQC.MQGMO_WAIT}')" 2>/dev/null; then
    pass "CMQC constants accessible"
else
    skip "Could not load ibmmq.CMQC (ibmmq not installed or MQ client missing)"
fi

echo ""
echo "===== Summary ====="
echo -e "  ${GREEN}OK${NC}: $ok   ${YELLOW}WARN${NC}: $warn   ${RED}FAIL${NC}: $fail"
if [ "$fail" -gt 0 ]; then
    echo ""
    echo "Fix the FAIL items above before starting EAP with MES MQ enabled."
    exit 1
fi
if [ "$warn" -gt 0 ]; then
    echo ""
    echo "Warnings may not block startup but could cause issues at runtime."
fi
exit 0
