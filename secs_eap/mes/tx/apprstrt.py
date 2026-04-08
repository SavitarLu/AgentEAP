"""
APPRSTRT transaction codec (JSON payload).

Generated from:
- CAPPRSTRT.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPRSTRT"
REQUEST_QUEUE = "F01.APPRSTRTI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPRSTRTRequest(TxRequestMixin):
    trx_id: str = "APPRSTRT"
    type_id: str = "I"
    tool_id: str = ""
    chamber_id: str = ""
    start_run_time: str = ""
    batch_id: str = ""
    lot_id: str = ""
    wafer_id: str = ""
    recipe_id: str = ""
    trace_id: str = ""


@dataclass
class APPRSTRTResponse(TxResponseMixin):
    trx_id: str = "APPRSTRT"
    type_id: str = "O"
    rtn_code: str = ""
    start_run_time: str = ""
    raw_payload: str = ""


REQUEST_TYPE = APPRSTRTRequest
RESPONSE_TYPE = APPRSTRTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPRSTRTRequest",
    "APPRSTRTResponse",
]
