#!/usr/bin/env python3
"""
Runtime entrypoint for bundled executable.
"""

import argparse
import sys
from pathlib import Path

from runtime_support import run_from_deploy_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one EAP equipment instance")
    parser.add_argument("eqpid", help="Equipment ID, mapped to config/<EQPID>.yaml")
    args = parser.parse_args()

    # PyInstaller onefile mode extracts to temp dir for __file__,
    # so use executable path when frozen.
    if getattr(sys, "frozen", False):
        deploy_root = Path(sys.executable).resolve().parents[1]
    else:
        deploy_root = Path(__file__).resolve().parents[1]
    eqpid = args.eqpid.strip()

    return run_from_deploy_root(deploy_root, eqpid)


if __name__ == "__main__":
    raise SystemExit(main())
