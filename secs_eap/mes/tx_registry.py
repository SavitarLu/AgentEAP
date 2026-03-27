"""
Auto-discovered MES TX registry based on Python TX modules.

Developers add new transaction codecs under ``secs_eap/mes/tx/*.py``.
Each module should expose at least:

- ``TX_NAME``
- ``REQUEST_QUEUE``
- ``REQUEST_TYPE``
- ``RESPONSE_TYPE``

Optional fields such as ``REPLY_QUEUE`` are also supported.
"""

from dataclasses import dataclass
import importlib
import logging
from pathlib import Path
import pkgutil
from types import ModuleType
from typing import Any, Dict, List, Optional, Type


logger = logging.getLogger(__name__)

TX_MODULE_DIR = Path(__file__).resolve().parent / "tx"
TX_PACKAGE_NAME = f"{__package__}.tx"
_SKIP_MODULES = {"__init__", "base"}


@dataclass(frozen=True)
class TxRoute:
    tx_name: str
    request_queue: str
    reply_queue: str = ""
    module_name: str = ""
    module_path: str = ""
    request_type_name: str = ""
    response_type_name: str = ""


def _normalize_tx_name(tx_name: str) -> str:
    return str(tx_name or "").strip().upper()


def _safe_type_name(value: Any) -> str:
    return getattr(value, "__name__", "")


def _iter_tx_module_names() -> List[str]:
    if not TX_MODULE_DIR.exists():
        return []
    names = []
    for module_info in pkgutil.iter_modules([str(TX_MODULE_DIR)]):
        if module_info.ispkg or module_info.name in _SKIP_MODULES:
            continue
        names.append(module_info.name)
    return sorted(set(names))


def _import_tx_module(module_name: str) -> ModuleType:
    return importlib.import_module(f"{TX_PACKAGE_NAME}.{module_name}")


def _build_tx_route(module_name: str) -> Optional[TxRoute]:
    try:
        module = _import_tx_module(module_name)
    except Exception as exc:
        logger.warning("Skip TX module %s: import failed: %s", module_name, exc)
        return None

    tx_name = _normalize_tx_name(getattr(module, "TX_NAME", module_name))
    request_queue = str(getattr(module, "REQUEST_QUEUE", "") or "").strip()
    if not request_queue:
        logger.warning("Skip TX module %s: REQUEST_QUEUE is missing", module_name)
        return None

    request_type = getattr(module, "REQUEST_TYPE", None)
    response_type = getattr(module, "RESPONSE_TYPE", None)

    return TxRoute(
        tx_name=tx_name,
        request_queue=request_queue,
        reply_queue=str(getattr(module, "REPLY_QUEUE", "") or "").strip(),
        module_name=module_name,
        module_path=module.__name__,
        request_type_name=_safe_type_name(request_type),
        response_type_name=_safe_type_name(response_type),
    )


def discover_tx_routes() -> Dict[str, TxRoute]:
    routes: Dict[str, TxRoute] = {}
    for module_name in _iter_tx_module_names():
        route = _build_tx_route(module_name)
        if route is None:
            continue
        routes[route.tx_name] = route
    return routes


def _fallback_routes() -> Dict[str, TxRoute]:
    return {
        "APVRYOPE": TxRoute(
            tx_name="APVRYOPE",
            request_queue="F01.APVRYOPEI",
            reply_queue="SHARE.REPLY",
            module_name="apvryope",
            module_path=f"{TX_PACKAGE_NAME}.apvryope",
            request_type_name="APVRYOPERequest",
            response_type_name="APVRYOPEResponse",
        )
    }


def _load_routes() -> Dict[str, TxRoute]:
    routes = discover_tx_routes()
    if routes:
        return routes
    return _fallback_routes()


TX_ROUTES: Dict[str, TxRoute] = _load_routes()


def reload_tx_routes() -> Dict[str, TxRoute]:
    global TX_ROUTES
    importlib.invalidate_caches()
    TX_ROUTES = _load_routes()
    return TX_ROUTES


def list_tx_routes() -> List[TxRoute]:
    return [TX_ROUTES[name] for name in sorted(TX_ROUTES)]


def get_tx_route(tx_name: str) -> TxRoute:
    normalized = _normalize_tx_name(tx_name)
    route = TX_ROUTES.get(normalized)
    if not route:
        raise KeyError(f"TX route not found: {tx_name}")
    return route


def load_tx_module(tx_name: str) -> ModuleType:
    route = get_tx_route(tx_name)
    return importlib.import_module(route.module_path)


def get_tx_request_type(tx_name: str) -> Optional[Type[Any]]:
    module = load_tx_module(tx_name)
    return getattr(module, "REQUEST_TYPE", None)


def get_tx_response_type(tx_name: str) -> Optional[Type[Any]]:
    module = load_tx_module(tx_name)
    return getattr(module, "RESPONSE_TYPE", None)
