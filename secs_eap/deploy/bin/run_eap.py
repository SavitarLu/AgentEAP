#!/usr/bin/env python3
"""
Deployment runner for secs_eap.

Folder layout:
deploy/
  bin/
  config/
  log/
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one EAP equipment instance")
    parser.add_argument("eqpid", help="Equipment ID, mapped to config/<EQPID>.yaml")
    args = parser.parse_args()

    deploy_root = Path(__file__).resolve().parents[1]
    lib_root = deploy_root / "lib"
    if not lib_root.exists():
        print(f"Lib directory not found: {lib_root}")
        print("Please build libraries first: deploy/bin/build_lib.sh")
        return 1

    # Load runtime libs from deploy/lib only.
    sys.path.insert(0, str(lib_root))

    from runtime_support import run_from_deploy_root

    eqpid = args.eqpid.strip()
    return run_from_deploy_root(deploy_root, eqpid)


if __name__ == "__main__":
    raise SystemExit(main())
