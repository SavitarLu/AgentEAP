"""
APPRCOMP transaction codec (JSON payload).

Generated from:
- CAPPRCOMP.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPRCOMP"
REQUEST_QUEUE = "F01.APPRCOMPI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPRCOMPRequest(TxRequestMixin):
    trx_id: str = "APPRCOMP"
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
class APPRCOMPResponse(TxResponseMixin):
    trx_id: str = "APPRCOMP"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_msg: str = ""
    raw_payload: str = ""


REQUEST_TYPE = APPRCOMPRequest
RESPONSE_TYPE = APPRCOMPResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPRCOMPRequest",
    "APPRCOMPResponse",
]
