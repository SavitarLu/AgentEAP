"""
SECS EAP - Equipment Automation Program

设备自动化程序，基于 SECS Driver 构建，
实现消息层和业务逻辑层的分离。
"""

from .eap import EAP, run_eap
from .config import EAPConfig, EquipmentConfig, MessageHandlerConfig, PortConfig
from .driver_adapter import DriverAdapter, ConnectionState
from .services import (
    EquipmentService,
    AlarmService,
    DataCollectionService,
    ProcessService,
    PortContextStore,
    PortLifecycleState,
    PortRuntimeContext,
    PortSheetContext,
    PortType,
)
from .mes import (
    APVRYOPERequest,
    APVRYOPEResponse,
    MesMqConfig,
    MesMqService,
    TxRoute,
    TX_ROUTES,
    get_tx_route,
    get_tx_request_type,
    get_tx_response_type,
    list_tx_routes,
    load_tx_module,
    reload_tx_routes,
)

__version__ = "1.0.0"
__all__ = [
    "EAP",
    "run_eap",
    "EAPConfig",
    "EquipmentConfig",
    "MessageHandlerConfig",
    "PortConfig",
    "DriverAdapter",
    "ConnectionState",
    "EquipmentService",
    "AlarmService",
    "DataCollectionService",
    "ProcessService",
    "PortContextStore",
    "PortLifecycleState",
    "PortRuntimeContext",
    "PortSheetContext",
    "PortType",
    "APVRYOPERequest",
    "APVRYOPEResponse",
    "MesMqConfig",
    "MesMqService",
    "TxRoute",
    "TX_ROUTES",
    "get_tx_route",
    "get_tx_request_type",
    "get_tx_response_type",
    "list_tx_routes",
    "load_tx_module",
    "reload_tx_routes",
]
