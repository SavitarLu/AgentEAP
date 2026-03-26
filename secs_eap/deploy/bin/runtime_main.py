#!/usr/bin/env python3
"""
Runtime entrypoint for bundled executable.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from secs_eap.config import EAPConfig
from secs_eap.eap import run_eap


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
