#!/usr/bin/env python3
"""
Shared helpers for deploy-time EAP runners.
"""

import asyncio
from pathlib import Path

from secs_eap.config import EAPConfig
from secs_eap.eap import run_eap


def run_from_deploy_root(deploy_root: Path, eqpid: str) -> int:
    """Load one equipment config from deploy root and run EAP."""
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
