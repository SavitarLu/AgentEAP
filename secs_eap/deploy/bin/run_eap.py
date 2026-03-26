#!/usr/bin/env python3
"""
Deployment runner for secs_eap.

Folder layout:
deploy/
  bin/
  config/
  log/
"""

import asyncio
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

    from secs_eap.eap import run_eap
    from secs_eap.config import EAPConfig

    eqpid = args.eqpid.strip()
    config_file = deploy_root / "config" / f"{eqpid}.yaml"
    if not config_file.exists():
        print(f"Config file not found: {config_file}")
        return 1

    config_dir = config_file.parent
    log_dir = deploy_root / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    config = EAPConfig.from_file(str(config_file))
    # Keep only console log redirected by start.sh.
    # Disable internal file logger to avoid duplicated log files.
    config.equipment.log_file = None

    if config.business_logic.workflow_file:
        config.business_logic.workflow_file = str(
            (config_dir / config.business_logic.workflow_file).resolve()
        )

    asyncio.run(run_eap(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
