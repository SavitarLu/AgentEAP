"""
SECS EAP - Equipment Automation Program

设备自动化程序，基于 SECS Driver 构建，
实现消息层和业务逻辑层的分离。
"""

from .eap import EAP, run_eap
from .config import EAPConfig, EquipmentConfig, MessageHandlerConfig
from .driver_adapter import DriverAdapter, ConnectionState
from .services import (
    EquipmentService,
    AlarmService,
    DataCollectionService,
    ProcessService,
)
from .mes import APVRYOPERequest, APVRYOPEResponse, MesMqConfig, MesMqService

__version__ = "1.0.0"
__all__ = [
    "EAP",
    "run_eap",
    "EAPConfig",
    "EquipmentConfig",
    "MessageHandlerConfig",
    "DriverAdapter",
    "ConnectionState",
    "EquipmentService",
    "AlarmService",
    "DataCollectionService",
    "ProcessService",
    "APVRYOPERequest",
    "APVRYOPEResponse",
    "MesMqConfig",
    "MesMqService",
]
