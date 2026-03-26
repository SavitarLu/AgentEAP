"""
Per-TX route definitions.

Keep queue routing close to each TX definition (not in device config),
similar to generated C++ TX classes.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TxRoute:
    tx_name: str
    request_queue: str


# Add more TX routes here as new modules are introduced.
TX_ROUTES: Dict[str, TxRoute] = {
    "APVRYOPE": TxRoute(tx_name="APVRYOPE", request_queue="F01.APVRYOPEI"),
}


def get_tx_route(tx_name: str) -> TxRoute:
    route = TX_ROUTES.get(tx_name)
    if not route:
        raise KeyError(f"TX route not found: {tx_name}")
    return route

