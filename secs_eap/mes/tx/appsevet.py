"""
APPSEVET transaction codec (JSON payload).

Generated from:
- CAPPSEVET.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPSEVET"
REQUEST_QUEUE = "F01.APPSEVETI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPSEVETOA:
    ceid: str = ""
    cename: str = ""
    celevel: str = ""


@dataclass
class APPSEVETRequest(TxRequestMixin):
    trx_id: str = "APPSEVET"
    type_id: str = "I"
    reqmode: str = ""
    message_id: str = ""
    message_key: str = ""
    eqp_id: str = ""
    report_timestamp: str = ""


@dataclass
class APPSEVETResponse(TxResponseMixin):
    trx_id: str = "APPSEVET"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_msg: str = ""
    message_id: str = ""
    message_key: str = ""
    eqp_id: str = ""
    report_timestamp: str = ""
    arycnt1: str = ""
    ary1: List[APPSEVETOA] = field(default_factory=list)
    raw_payload: str = ""


REQUEST_TYPE = APPSEVETRequest
RESPONSE_TYPE = APPSEVETResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPSEVETOA",
    "APPSEVETRequest",
    "APPSEVETResponse",
]
